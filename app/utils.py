"""Small helpers shared across service modules."""

from __future__ import annotations

import calendar
from datetime import date


def month_bounds(any_date: date) -> tuple[date, date]:
    """Returns (first day, last day) of the month containing any_date.
    Accepts any day within the month -- callers don't need to normalize
    to the 1st first.
    """
    if not isinstance(any_date, date):
        raise TypeError(f"month_bounds expects a date, got {type(any_date).__name__}")
    try:
        first = date(any_date.year, any_date.month, 1)
        last_day = calendar.monthrange(any_date.year, any_date.month)[1]
        last = date(any_date.year, any_date.month, last_day)
    except (ValueError, OverflowError) as e:
        raise ValueError(f"invalid date for month_bounds: {any_date!r}") from e
    return first, last
