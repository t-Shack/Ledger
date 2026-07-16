# Budget Tracker

Uploads bank statements (Opay, Palmpay, and others), auto-categorizes
transactions, and tracks spending against a monthly budget worksheet.

## Project structure

```
.
├── app/                    # backend package -- relative imports need this
│   ├── __init__.py
│   ├── api.py               # FastAPI app + all endpoints (entry point)
│   ├── database.py          # engine, session, DATABASE_URL handling
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response models
│   ├── exceptions.py        # domain exceptions
│   ├── utils.py
│   ├── aggregation.py       # monthly summary computation
│   ├── categorization_engine.py
│   └── statement_parser.py  # CSV/XLSX/PDF -> transactions
├── tests/
│   ├── fixtures/             # synthetic statement files
│   ├── run_fixtures.py
│   └── run_real_file.py
├── frontend/                # Next.js app (separate from the backend package)
├── schema.sql
├── requirements.txt
├── .env.example
└── README.md
```

`app/` is a real Python package (has `__init__.py`), which is what makes
the `from .database import ...`-style relative imports inside it work.
Run everything from the project root, never from inside `app/`.

## Backend setup

1. Python 3.11+:
   ```
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in:
   ```
   DATABASE_URL=postgresql://user:password@host/dbname
   ANTHROPIC_API_KEY=sk-...
   ```
   `.env` is loaded automatically (via `python-dotenv`) -- no need to
   export variables manually or pass `--env-file`. A standard connection
   string from your provider (Neon, Supabase, RDS, Railway, etc.) works
   as-is; `+asyncpg` and SSL params are normalized automatically.

   Missing `ANTHROPIC_API_KEY` no longer crashes the server -- uploads
   still work, transactions just come in uncategorized and flagged for
   review until the key is set.
3. Apply the schema:
   ```
   psql $DATABASE_URL -f schema.sql
   ```
   No `psql` installed? Paste the contents of `schema.sql` into your
   provider's SQL editor instead (e.g. Neon's built-in one) — same result.
4. Run the API from the project root:
   ```
   uvicorn app.api:app --reload
   ```

Auth is currently a stub — every request needs an `X-User-Id: <uuid>`
header. Insert a row into `users` manually to get a UUID to use.

## Frontend setup

```
cd frontend
npm install
cp .env.example .env.local   # fill in BACKEND_URL and STUB_USER_ID
npm run build
npm run dev
```

## Testing the statement parser

`tests/fixtures/` has synthetic bank-statement fixtures (Palmpay/GTBank/
international-style CSV, an XLSX, and a synthetic Opay-style PDF) covering
the bugs found during development. Run:
```
python tests/run_fixtures.py
```

To test against a real statement file and see computed totals (useful for
cross-checking against the bank's own reported totals):
```
python tests/run_real_file.py path/to/statement.pdf
```

## Known gaps

- **Auth** is a stub (`X-User-Id` header) — not production auth.
- **PDF extraction**: solid for Access Bank-style statements (verified
  exact match against the bank's own reported totals). Partial for Opay —
  a transaction description that wraps across multiple lines can cause
  that row's cells to garble during table detection. Partial for
  PalmPay — a page where every transaction is the same direction (all
  debits or all credits) can lose that column's structure entirely,
  breaking alignment for that page. Both are pdfplumber table-detection
  limitations, not bugs in the row-parsing logic itself; fixing them
  fully means a different extraction strategy (regex fallback for
  garbled cells; word-coordinate-based column reconstruction for the
  vanishing-column case).
- **No delete/rename** for accounts or categories yet.
- **No pagination** on the transaction list yet.
