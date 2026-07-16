"""
Runs the parser against a real statement file and reports parsed vs
skipped rows, plus computed totals -- cross-check these against the
bank's own reported "Total Debit"/"Total Credit" figures on the
statement itself. An exact match is the strongest evidence the parser
got a file right.

Usage:
    python tests/run_real_file.py path/to/statement.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.statement_parser import StatementParseError, parse_statement  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python run_real_file.py <path-to-statement>")
        raise SystemExit(1)

    path = Path(sys.argv[1])
    try:
        content = path.read_bytes()
    except OSError as e:
        print(f"COULD NOT READ FILE: {e}")
        raise SystemExit(1) from e

    try:
        result = parse_statement(path.name, content)
    except StatementParseError as e:
        print(f"PARSE ERROR: {e}")
        raise SystemExit(1) from e

    total_debit = sum(t.amount for t in result.transactions if t.direction == "debit")
    total_credit = sum(t.amount for t in result.transactions if t.direction == "credit")

    print(f"parsed: {len(result.transactions)}   skipped: {len(result.skipped)}")
    print(f"computed total debit:  {total_debit}")
    print(f"computed total credit: {total_credit}")

    print("\nfirst 10 transactions:")
    for t in result.transactions[:10]:
        print(f"  {t.txn_date}  {t.direction:6s}  {str(t.amount):>14}  {t.raw_description[:60]!r}")

    if result.skipped:
        print("\nfirst 10 skipped rows:")
        for s in result.skipped[:10]:
            print(f"  row {s.row_number}: {s.reason}")


if __name__ == "__main__":
    main()
