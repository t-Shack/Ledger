"""
SQLAlchemy ORM models mirroring schema.sql.

schema.sql is the source of truth for DDL (enums, constraints, indexes,
seed data). These models must stay in sync with it for application-level
querying -- they don't create the enum types themselves (create_type=False),
since schema.sql already does that.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CategoryType(str, enum.Enum):
    income = "income"
    fixed_expense = "fixed_expense"
    variable_expense = "variable_expense"


class TxnDirection(str, enum.Enum):
    debit = "debit"
    credit = "credit"


class StatementFormat(str, enum.Enum):
    csv = "csv"
    xlsx = "xlsx"
    pdf = "pdf"


class StatementStatus(str, enum.Enum):
    processing = "processing"
    parsed = "parsed"
    failed = "failed"


class RuleSource(str, enum.Enum):
    seed = "seed"
    ai_suggestion = "ai_suggestion"
    user_correction = "user_correction"


class AccountPurpose(str, enum.Enum):
    income = "income"
    spending = "spending"
    savings = "savings"
    other = "other"


def _uuid_pk():
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[AccountPurpose] = mapped_column(
        SAEnum(AccountPurpose, name="account_purpose", create_type=False), nullable=False
    )
    is_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[CategoryType] = mapped_column(
        SAEnum(CategoryType, name="category_type", create_type=False), nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[StatementFormat] = mapped_column(
        SAEnum(StatementFormat, name="statement_format", create_type=False), nullable=False
    )
    status: Mapped[StatementStatus] = mapped_column(
        SAEnum(StatementStatus, name="statement_status", create_type=False),
        nullable=False,
        default=StatementStatus.processing,
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    statement_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("statements.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    txn_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[TxnDirection] = mapped_column(
        SAEnum(TxnDirection, name="txn_direction", create_type=False), nullable=False
    )
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_internal_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    linked_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CategoryRule(Base):
    __tablename__ = "category_rules"
    __table_args__ = (UniqueConstraint("user_id", "match_key"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    match_key: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    source: Mapped[RuleSource] = mapped_column(
        SAEnum(RuleSource, name="rule_source", create_type=False), nullable=False
    )
    times_matched: Mapped[int] = mapped_column(nullable=False, default=0)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CategoryCorrection(Base):
    __tablename__ = "category_corrections"

    id: Mapped[uuid.UUID] = _uuid_pk()
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    previous_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    new_category_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"
    __table_args__ = (UniqueConstraint("user_id", "month"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    total_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_fixed_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_variable_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    discretionary_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
