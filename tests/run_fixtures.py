"""
Runs the parser against the synthetic fixtures in tests/fixtures/ and
prints parsed transactions vs skipped rows for manual inspection.

These fixtures were built to reproduce specific real-world conventions
(Palmpay's Transaction Type wording, ISO dates, DR/CR abbreviations, etc.)
and the bugs each one caught during development -- run this after any
change to statement_parser.py as a quick regression check.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.statement_parser import StatementParseError, parse_statement  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURES = [
    "palmpay_style.csv",
    "gtbank_style.csv",
    "international_style.csv",
    "palmpay_style.xlsx",
    "opay_style.pdf",
]


def main() -> None:
    for filename in FIXTURES:
        path = FIXTURES_DIR / filename
        print(f"\n{'=' * 70}\n{filename}\n{'=' * 70}")
        try:
            content = path.read_bytes()
        except OSError as e:
            print(f"  COULD NOT READ FILE: {e}")
            continue

        try:
            result = parse_statement(filename, content)
        except StatementParseError as e:
            print(f"  PARSE ERROR: {e}")
            continue

        print(f"  parsed: {len(result.transactions)}  skipped: {len(result.skipped)}")
        for t in result.transactions:
            print(f"    {t.txn_date}  {t.direction:6s}  {str(t.amount):>12}  {t.raw_description[:45]}")
        for s in result.skipped:
            print(f"    SKIPPED row {s.row_number}: {s.reason}")


if __name__ == "__main__":
    main()
