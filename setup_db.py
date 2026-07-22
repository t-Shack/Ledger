#!/usr/bin/env python3
"""
Initialize the database with the stub user for testing/development.
Run this after creating the database schema.

Usage:
    python setup_db.py
"""

import asyncio
import os
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables from .env file
load_dotenv()

# Use the same stub user ID from the frontend .env
STUB_USER_ID = "59e107ee-7258-4592-84c4-9e7f2ae0049d"
STUB_USER_EMAIL = "shack@example.com"
# In a real app, this would be hashed. For development, we'll use a placeholder.
STUB_PASSWORD_HASH = "placeholder_hash_not_for_production"


def normalize_database_url(raw_url: str) -> tuple[str, dict]:
    """Normalize PostgreSQL URL for async use with asyncpg driver.
    
    - Adds the +asyncpg driver if it's missing
    - Moves libpq-style SSL params out of the URL and into connect_args
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

async def setup_db():
    """Create the stub user if it doesn't exist."""
    raw_database_url = os.environ.get("DATABASE_URL")
    if not raw_database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Normalize the URL for asyncpg
    database_url, connect_args = normalize_database_url(raw_database_url)
    
    engine = create_async_engine(database_url, connect_args=connect_args)
    
    async with engine.begin() as conn:
        # Check if user exists
        result = await conn.execute(
            text("SELECT id FROM users WHERE id = :id"),
            {"id": STUB_USER_ID}
        )
        
        if result.scalar() is None:
            # Insert the stub user
            await conn.execute(
                text("""
                    INSERT INTO users (id, email, password_hash)
                    VALUES (:id, :email, :password_hash)
                """),
                {
                    "id": STUB_USER_ID,
                    "email": STUB_USER_EMAIL,
                    "password_hash": STUB_PASSWORD_HASH,
                }
            )
            print(f"✓ Created stub user: {STUB_USER_ID}")
        else:
            print(f"✓ Stub user already exists: {STUB_USER_ID}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(setup_db())
