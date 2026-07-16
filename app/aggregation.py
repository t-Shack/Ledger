"""
Aggregation: rolls categorized transactions up into the budget worksheet's
Income / Fixed Expenses / Variable Expenses / Discretionary Income totals,
plus a per-category breakdown within each section (e.g. Food & Groceries
vs Transport under Variable Expenses) -- both computed from one grouped
query so the breakdown and the totals can never drift apart.

Transactions with needs_review = true are excluded from the totals -- an
unconfirmed AI guess shouldn't silently count toward the budget -- and are
reported separately as pending_review_count so the caller can flag an
incomplete month in the UI.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import ValidationError
from .models import Account, Category, CategoryType, MonthlySummary, Statement, Transaction
from .utils import month_bounds


async def compute_monthly_summary(session: AsyncSession, user_id: uuid.UUID, any_date: date) -> dict:
    """Computes, persists, and returns the worksheet totals for the month
    containing any_date. Safe to call repeatedly -- results are upserted.

    Only transactions on accounts with is_tracked = true are included --
    an income-only account (linked just so its transfers are visible) can
    be uploaded without its balance double-counting against the tracked
    spending account it funds.
    """
    if not isinstance(user_id, uuid.UUID):
        raise TypeError(f"user_id must be a UUID, got {type(user_id).__name__}")

    try:
        start, end = month_bounds(any_date)
    except (TypeError, ValueError) as e:
        raise ValidationError(str(e)) from e

    breakdown_query = (
        select(Category.id, Category.name, Category.type, func.coalesce(func.sum(Transaction.amount), 0))
        .join(Category, Transaction.category_id == Category.id)
        .join(Statement, Transaction.statement_id == Statement.id)
        .join(Account, Statement.account_id == Account.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
            Transaction.needs_review.is_(False),
            Account.is_tracked.is_(True),
        )
        .group_by(Category.id, Category.name, Category.type)
        .order_by(Category.type, Category.name)
    )
    pending_query = (
        select(func.count())
        .select_from(Transaction)
        .join(Statement, Transaction.statement_id == Statement.id)
        .join(Account, Statement.account_id == Account.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
            Transaction.needs_review.is_(True),
            Account.is_tracked.is_(True),
        )
    )

    try:
        breakdown_rows = (await session.execute(breakdown_query)).all()
        pending_review_count = (await session.execute(pending_query)).scalar_one()
    except Exception as e:
        raise ValidationError("failed to read transactions for summary") from e

    totals: dict[CategoryType, Decimal] = {t: Decimal("0") for t in CategoryType}
    by_category: list[dict] = []
    for category_id, name, category_type, total in breakdown_rows:
        amount = Decimal(total)
        totals[category_type] += amount
        by_category.append({"category_id": category_id, "name": name, "type": category_type, "total": amount})

    total_income = totals[CategoryType.income]
    total_fixed = totals[CategoryType.fixed_expense]
    total_variable = totals[CategoryType.variable_expense]
    discretionary_income = total_income - total_fixed - total_variable

    upsert = insert(MonthlySummary).values(
        user_id=user_id,
        month=start,
        total_income=total_income,
        total_fixed_expenses=total_fixed,
        total_variable_expenses=total_variable,
        discretionary_income=discretionary_income,
    )
    upsert = upsert.on_conflict_do_update(
        index_elements=[MonthlySummary.user_id, MonthlySummary.month],
        set_={
            "total_income": upsert.excluded.total_income,
            "total_fixed_expenses": upsert.excluded.total_fixed_expenses,
            "total_variable_expenses": upsert.excluded.total_variable_expenses,
            "discretionary_income": upsert.excluded.discretionary_income,
            "generated_at": func.now(),
        },
    )
    try:
        await session.execute(upsert)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise ValidationError("failed to persist monthly summary") from e

    return {
        "month": start,
        "total_income": total_income,
        "total_fixed_expenses": total_fixed,
        "total_variable_expenses": total_variable,
        "discretionary_income": discretionary_income,
        "pending_review_count": pending_review_count,
        "by_category": by_category,
    }
