"""
FastAPI application: statement upload, transaction review/correction, and
monthly summary endpoints.

Auth note: get_current_user_id is a placeholder that reads an X-User-Id
header. It's intentionally isolated here so the request-handling logic
below can be reviewed and tested independently of the real auth design,
which hasn't been discussed yet -- replace before deploying.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from decimal import Decimal

import anthropic
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .aggregation import compute_monthly_summary
from .categorization_engine import CategorizationEngine, CategoryCache, RawTransaction, normalize_description
from .database import get_session
from .exceptions import AppError, NotFoundError, StatementProcessingError, ValidationError
from .models import (
    Account,
    AccountPurpose,
    Category,
    CategoryCorrection,
    CategoryType,
    Statement,
    StatementFormat,
    StatementStatus,
    Transaction,
)
from .schemas import (
    AccountCreateRequest,
    AccountOut,
    AccountUpdateRequest,
    CategoryCorrectionRequest,
    CategoryCreateRequest,
    CategoryOut,
    MonthlySummaryOut,
    SkippedRowOut,
    StatementUploadResponse,
    TransactionOut,
)
from .statement_parser import StatementParseError, parse_statement
from .utils import month_bounds

app = FastAPI(title="Budget Tracker API")

_ai_client: anthropic.AsyncAnthropic | None = None


def _get_ai_client() -> anthropic.AsyncAnthropic:
    """Creates the Anthropic client on first use rather than at import
    time. A missing ANTHROPIC_API_KEY then only breaks categorization
    (which already degrades to needs_review=True on any failure -- see
    upload_statement) instead of preventing the server from starting at
    all, including for endpoints that don't touch AI.
    """
    global _ai_client
    if _ai_client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise StatementProcessingError("ANTHROPIC_API_KEY is not set -- categorization is unavailable")
        _ai_client = anthropic.AsyncAnthropic()
    return _ai_client


def _error_response(code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=code, content={"detail": detail})


@app.exception_handler(NotFoundError)
async def handle_not_found(request, exc: NotFoundError) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, str(exc))


@app.exception_handler(ValidationError)
async def handle_validation(request, exc: ValidationError) -> JSONResponse:
    return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))


@app.exception_handler(StatementProcessingError)
async def handle_statement_error(request, exc: StatementProcessingError) -> JSONResponse:
    return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))


@app.exception_handler(AppError)
async def handle_app_error(request, exc: AppError) -> JSONResponse:
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal error")


@app.exception_handler(Exception)
async def handle_unexpected(request, exc: Exception) -> JSONResponse:
    # Last-resort safety net: never leak a raw stack trace to the client.
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal error")


async def get_current_user_id(x_user_id: str = Header(...)) -> uuid.UUID:
    try:
        return uuid.UUID(x_user_id)
    except (ValueError, AttributeError) as e:
        raise HTTPException(status_code=401, detail="missing or invalid X-User-Id header") from e


async def _get_owned_account(session: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    account = (
        await session.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    ).scalar_one_or_none()
    if account is None:
        raise NotFoundError(f"account {account_id} not found")
    return account


async def _get_accessible_category(session: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> Category:
    category = (
        await session.execute(
            select(Category).where(
                Category.id == category_id,
                (Category.user_id == user_id) | (Category.user_id.is_(None)),
            )
        )
    ).scalar_one_or_none()
    if category is None:
        raise NotFoundError(f"category {category_id} not found or not accessible")
    return category


def _transactions_with_labels_query(user_id: uuid.UUID):
    """Base query joining a transaction to its account name (always present,
    via statement -> account) and category name (absent when uncategorized).
    """
    return (
        select(Transaction, Account.name, Category.name)
        .join(Statement, Transaction.statement_id == Statement.id)
        .join(Account, Statement.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(Transaction.user_id == user_id)
    )


def _to_transaction_out(txn: Transaction, account_name: str, category_name: str | None) -> TransactionOut:
    return TransactionOut(
        id=txn.id,
        txn_date=txn.txn_date,
        raw_description=txn.raw_description,
        amount=txn.amount,
        direction=txn.direction,
        account_name=account_name,
        category_id=txn.category_id,
        category_name=category_name,
        confidence=txn.confidence,
        needs_review=txn.needs_review,
        is_internal_transfer=txn.is_internal_transfer,
    )


@app.get("/accounts", response_model=list[AccountOut])
async def list_accounts(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[AccountOut]:
    try:
        rows = (await session.execute(select(Account).where(Account.user_id == user_id))).scalars().all()
    except Exception as e:
        raise ValidationError("could not fetch accounts") from e
    return [AccountOut.model_validate(a) for a in rows]


@app.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    account = Account(
        user_id=user_id, name=body.name, purpose=AccountPurpose(body.purpose), is_tracked=body.is_tracked
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ValidationError(f"an account named '{body.name}' already exists") from e
    except Exception as e:
        await session.rollback()
        raise AppError("could not create account") from e
    return AccountOut.model_validate(account)


@app.patch("/accounts/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    account = await _get_owned_account(session, user_id, account_id)
    account.is_tracked = body.is_tracked
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise AppError("could not update account") from e
    return AccountOut.model_validate(account)


@app.post("/accounts/{account_id}/statements", response_model=StatementUploadResponse)
async def upload_statement(
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StatementUploadResponse:
    account = await _get_owned_account(session, user_id, account_id)

    if not file.filename:
        raise ValidationError("uploaded file has no filename")
    try:
        content = await file.read()
    except Exception as e:
        raise StatementProcessingError("could not read uploaded file") from e
    if not content:
        raise ValidationError("uploaded file is empty")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    try:
        statement_format = StatementFormat("xlsx" if ext == "xls" else ext)
    except ValueError as e:
        raise ValidationError(f"unsupported file extension: .{ext or 'unknown'}") from e

    statement = Statement(
        user_id=user_id,
        account_id=account.id,
        original_filename=file.filename,
        format=statement_format,
        status=StatementStatus.processing,
    )
    session.add(statement)
    try:
        await session.flush()  # assigns statement.id without committing
    except Exception as e:
        await session.rollback()
        raise StatementProcessingError("could not create statement record") from e

    try:
        parse_result = parse_statement(file.filename, content)
    except StatementParseError as e:
        statement.status = StatementStatus.failed
        await session.commit()
        raise StatementProcessingError(str(e)) from e

    if not parse_result.transactions:
        statement.status = StatementStatus.failed
        await session.commit()
        raise StatementProcessingError("no valid transactions found in statement")

    transactions = [
        Transaction(
            statement_id=statement.id,
            user_id=user_id,
            txn_date=t.txn_date,
            raw_description=t.raw_description,
            amount=t.amount,
            direction=t.direction,
            balance_after=t.balance_after,
        )
        for t in parse_result.transactions
    ]
    session.add_all(transactions)
    try:
        await session.flush()
    except Exception as e:
        await session.rollback()
        statement.status = StatementStatus.failed
        await session.commit()
        raise StatementProcessingError("could not save parsed transactions") from e

    try:
        categories = (
            await session.execute(
                select(Category).where((Category.user_id == user_id) | (Category.user_id.is_(None)))
            )
        ).scalars().all()
    except Exception as e:
        raise StatementProcessingError("could not load categories") from e

    raw_txns = [RawTransaction(id=t.id, description=t.raw_description) for t in transactions]
    try:
        engine = CategorizationEngine(session, _get_ai_client())
        categorized = await engine.categorize(user_id, raw_txns, categories)
    except Exception:
        # Categorization failing (including a missing API key) shouldn't lose
        # the imported transactions -- they're kept, marked uncategorized,
        # and flagged for manual review.
        categorized = []

    by_id = {c.id: c for c in categorized}
    for txn in transactions:
        result = by_id.get(txn.id)
        if result is None:
            txn.needs_review = True
            continue
        txn.category_id = result.category_id
        txn.confidence = Decimal(str(result.confidence))
        txn.needs_review = result.needs_review

    statement.status = StatementStatus.parsed
    statement.processed_at = datetime.utcnow()
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise StatementProcessingError("could not finalize statement processing") from e

    return StatementUploadResponse(
        statement_id=statement.id,
        status=statement.status.value,
        transactions_imported=len(transactions),
        transactions_skipped=len(parse_result.skipped),
        skipped_rows=[SkippedRowOut(row_number=r.row_number, reason=r.reason) for r in parse_result.skipped],
    )


@app.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryOut]:
    try:
        rows = (
            await session.execute(
                select(Category).where((Category.user_id == user_id) | (Category.user_id.is_(None)))
            )
        ).scalars().all()
    except Exception as e:
        raise ValidationError("could not fetch categories") from e
    return [CategoryOut.model_validate(c) for c in rows]


@app.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> CategoryOut:
    category = Category(user_id=user_id, name=body.name, type=CategoryType(body.type), is_default=False)
    session.add(category)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ValidationError(f"a category named '{body.name}' already exists") from e
    except Exception as e:
        await session.rollback()
        raise AppError("could not create category") from e
    return CategoryOut.model_validate(category)


@app.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(
    needs_review: bool | None = Query(default=None),
    month: date | None = Query(default=None),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[TransactionOut]:
    query = _transactions_with_labels_query(user_id)
    if needs_review is not None:
        query = query.where(Transaction.needs_review.is_(needs_review))
    if month is not None:
        try:
            start, end = month_bounds(month)
        except (TypeError, ValueError) as e:
            raise ValidationError(str(e)) from e
        query = query.where(Transaction.txn_date >= start, Transaction.txn_date <= end)

    try:
        rows = (await session.execute(query.order_by(Transaction.txn_date.desc()))).all()
    except Exception as e:
        raise ValidationError("could not fetch transactions") from e

    return [_to_transaction_out(txn, account_name, category_name) for txn, account_name, category_name in rows]


@app.patch("/transactions/{transaction_id}/category", response_model=TransactionOut)
async def correct_transaction_category(
    transaction_id: uuid.UUID,
    body: CategoryCorrectionRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TransactionOut:
    transaction = (
        await session.execute(
            select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
        )
    ).scalar_one_or_none()
    if transaction is None:
        raise NotFoundError(f"transaction {transaction_id} not found")

    category = await _get_accessible_category(session, user_id, body.category_id)

    previous_category_id = transaction.category_id
    transaction.category_id = category.id
    transaction.confidence = Decimal("1.000")
    transaction.needs_review = False
    transaction.reviewed_at = datetime.utcnow()

    session.add(
        CategoryCorrection(
            transaction_id=transaction.id,
            previous_category_id=previous_category_id,
            new_category_id=category.id,
        )
    )

    cache = CategoryCache(session)
    normalized = normalize_description(transaction.raw_description)
    try:
        await cache.record(user_id, normalized, category.id, source="user_correction")
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise ValidationError("could not save correction") from e

    row = (
        await session.execute(_transactions_with_labels_query(user_id).where(Transaction.id == transaction.id))
    ).first()
    if row is None:
        raise NotFoundError(f"transaction {transaction_id} not found after update")
    return _to_transaction_out(*row)


@app.get("/summary", response_model=MonthlySummaryOut)
async def get_monthly_summary(
    month: date = Query(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MonthlySummaryOut:
    result = await compute_monthly_summary(session, user_id, month)
    return MonthlySummaryOut(**result)
