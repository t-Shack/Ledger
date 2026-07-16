"""
Domain-level exceptions.

These are raised by service/business logic (aggregation, categorization,
parsing) and are deliberately decoupled from HTTP status codes -- api.py
registers handlers that translate each type into the right response.
Keeping this separation means aggregation.py, categorization_engine.py,
etc. can be unit tested without a FastAPI app in the loop.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all domain errors. Never raised directly."""


class NotFoundError(AppError):
    """Requested resource does not exist, or exists but isn't owned by the caller."""


class ValidationError(AppError):
    """Input failed a domain-level rule (distinct from Pydantic's type-level validation)."""


class StatementProcessingError(AppError):
    """A statement failed to parse or could not be persisted/categorized."""
