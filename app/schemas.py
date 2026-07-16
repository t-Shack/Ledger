"""Pydantic request/response models for the API layer."""

from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class MoneyModel(BaseModel):
    """Base for any response model carrying Decimal money fields.

    Pydantic's default JSON encoding can convert Decimal to float, which
    silently loses precision -- never acceptable for currency. This
    forces every Decimal field to serialize as a string instead.
    """

    @field_serializer("*", when_used="json")
    def _decimal_as_str(self, value: object) -> object:
        return str(value) if isinstance(value, Decimal) else value


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    purpose: str
    is_tracked: bool

    @field_validator("purpose", mode="before")
    @classmethod
    def _coerce_enum(cls, v: object) -> object:
        return v.value if isinstance(v, enum.Enum) else v


class AccountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    purpose: Literal["income", "spending", "savings", "other"]
    is_tracked: bool = True


class AccountUpdateRequest(BaseModel):
    is_tracked: bool


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_enum(cls, v: object) -> object:
        return v.value if isinstance(v, enum.Enum) else v


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: Literal["income", "fixed_expense", "variable_expense"]


class SkippedRowOut(BaseModel):
    row_number: int
    reason: str


class StatementUploadResponse(BaseModel):
    statement_id: uuid.UUID
    status: str
    transactions_imported: int
    transactions_skipped: int
    skipped_rows: list[SkippedRowOut] = Field(default_factory=list)


class TransactionOut(MoneyModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    txn_date: date
    raw_description: str
    amount: Decimal
    direction: str
    account_name: str
    category_id: uuid.UUID | None
    category_name: str | None
    confidence: Decimal | None
    needs_review: bool
    is_internal_transfer: bool

    @field_validator("direction", mode="before")
    @classmethod
    def _coerce_enum(cls, v: object) -> object:
        # Defensive: works whether the ORM gives us the enum member or a raw string.
        return v.value if isinstance(v, enum.Enum) else v


class CategoryCorrectionRequest(BaseModel):
    category_id: uuid.UUID


class CategoryTotalOut(MoneyModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: uuid.UUID
    name: str
    type: str
    total: Decimal

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_enum(cls, v: object) -> object:
        return v.value if isinstance(v, enum.Enum) else v


class MonthlySummaryOut(MoneyModel):
    month: date
    total_income: Decimal
    total_fixed_expenses: Decimal
    total_variable_expenses: Decimal
    discretionary_income: Decimal
    pending_review_count: int
    by_category: list[CategoryTotalOut]
