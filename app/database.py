"""Async SQLAlchemy engine and session dependency for FastAPI."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()  # populates os.environ from a local .env file, if present


def _normalize_database_url(raw_url: str) -> tuple[str, dict]:
    """Makes a standard postgresql:// URL -- what every managed Postgres
    provider (Neon, Supabase, RDS, Railway) actually hands you -- usable
    with SQLAlchemy's async engine:
      - adds the +asyncpg driver if it's missing
      - moves libpq-style SSL params (sslmode, channel_binding) out of the
        URL and into connect_args. asyncpg's connect() doesn't accept
        these as query parameters and raises on ones it doesn't recognize,
        so passing a Neon URL straight through fails before ever reaching
        the network.
    """
    parts = urlsplit(raw_url)

    scheme = parts.scheme
    if scheme in ("postgresql", "postgres"):
        scheme = "postgresql+asyncpg"

    query_pairs = parse_qs(parts.query, keep_blank_values=True)
    sslmode = query_pairs.pop("sslmode", ["require"])[0]
    query_pairs.pop("channel_binding", None)  # asyncpg has no equivalent; safe to drop

    remaining_query = urlencode(query_pairs, doseq=True)
    normalized_url = urlunsplit((scheme, parts.netloc, parts.path, remaining_query, parts.fragment))

    connect_args = {"ssl": sslmode} if sslmode != "disable" else {}
    return normalized_url, connect_args


DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Fail fast at import time rather than on the first request.
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "A standard postgresql:// connection string from your provider "
        "works directly -- the +asyncpg driver and SSL settings are "
        "normalized automatically."
    )

_normalized_url, _connect_args = _normalize_database_url(DATABASE_URL)

engine = create_async_engine(_normalized_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session.
    Rolls back and re-raises on any error so a failed request never leaves
    a half-committed transaction open.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

