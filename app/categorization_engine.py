"""
Categorization engine.

Two-tier lookup for every transaction:
  1. Cache  -- per-user learned rules (category_rules table). Instant, free.
  2. Claude -- batched call for anything the cache has never seen, using a
     forced tool schema so the response is always structured JSON.

Successful AI classifications are written back into the cache, so the same
merchant on next month's statement (e.g. "PALMPAY-KFC IKEJA") is matched
without another API call. Confidence below CONFIDENCE_THRESHOLD is flagged
for manual review instead of being silently guessed.

Internal transfers (e.g. Opay -> Palmpay) are not special-cased here --
per the account model, an inbound transfer to a tracked spending account is
categorized normally under "Internal Transfer" (an income-type category).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

import anthropic
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Category, CategoryRule  # SQLAlchemy models mirroring schema.sql

MODEL = "claude-sonnet-5"
CONFIDENCE_THRESHOLD = 0.75   # below this, needs_review = true
BATCH_SIZE = 40               # transactions per Claude call

_REFERENCE_NOISE = re.compile(r"\b(?:ref|txn|trx)?[:#]?\s*\d{6,}\b", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def normalize_description(raw: str) -> str:
    """Strip reference numbers and collapse whitespace so the same merchant
    with a different transaction ID still hits the cache.

    'PALMPAY-KFC IKEJA-TXN00238471' -> 'palmpay-kfc ikeja'
    """
    text = _REFERENCE_NOISE.sub("", raw.lower())
    text = _WHITESPACE.sub(" ", text).strip(" -_")
    return text


@dataclass(frozen=True)
class RawTransaction:
    id: UUID
    description: str


@dataclass(frozen=True)
class CategorizedTransaction:
    id: UUID
    category_id: UUID | None
    confidence: float
    needs_review: bool
    source: str  # "cache" | "ai"


class CategoryCache:
    """Read/write wrapper over the category_rules table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def lookup(self, user_id: UUID, normalized: str) -> tuple[UUID, float] | None:
        row = (
            await self.session.execute(
                select(CategoryRule.category_id, CategoryRule.times_matched).where(
                    CategoryRule.user_id == user_id,
                    CategoryRule.match_key == normalized,
                )
            )
        ).first()
        if row is None:
            return None
        category_id, times_matched = row
        # Confidence grows slightly with repeated confirmed use, capped below 1.0.
        confidence = min(0.99, 0.85 + 0.02 * times_matched)
        return category_id, confidence

    async def record(self, user_id: UUID, normalized: str, category_id: UUID, source: str) -> None:
        stmt = insert(CategoryRule).values(
            user_id=user_id,
            match_key=normalized,
            category_id=category_id,
            source=source,
            times_matched=0,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[CategoryRule.user_id, CategoryRule.match_key],
            set_={
                "category_id": stmt.excluded.category_id,
                "source": stmt.excluded.source,
                "times_matched": CategoryRule.times_matched + 1,
                "last_matched_at": func.now(),
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()


class AIClassifier:
    """Calls Claude with a forced tool schema so output is always structured."""

    def __init__(self, client: anthropic.AsyncAnthropic):
        self.client = client

    async def classify_batch(self, descriptions: Sequence[str], categories: Sequence[str]) -> list[dict]:
        schema = {
            "name": "categorize_transactions",
            "description": "Assign exactly one category to each transaction description.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer"},
                                "category": {"type": "string", "enum": list(categories)},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                            "required": ["index", "category", "confidence"],
                        },
                    }
                },
                "required": ["results"],
            },
        }

        numbered = "\n".join(f"{i}: {d}" for i, d in enumerate(descriptions))
        response = await self.client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=[schema],
            tool_choice={"type": "tool", "name": "categorize_transactions"},
            messages=[{
                "role": "user",
                "content": (
                    "Categorize each bank transaction description into exactly one "
                    f"of these categories: {', '.join(categories)}.\n\n{numbered}"
                ),
            }],
        )
        tool_call = next(block for block in response.content if block.type == "tool_use")
        return tool_call.input["results"]


class CategorizationEngine:
    """Orchestrates cache-first, AI-fallback categorization for a batch of transactions."""

    def __init__(self, session: AsyncSession, ai_client: anthropic.AsyncAnthropic):
        self.cache = CategoryCache(session)
        self.classifier = AIClassifier(ai_client)

    async def categorize(
        self,
        user_id: UUID,
        transactions: Sequence[RawTransaction],
        categories: Sequence[Category],
    ) -> list[CategorizedTransaction]:
        name_to_id = {c.name: c.id for c in categories}
        results: dict[UUID, CategorizedTransaction] = {}
        misses: list[RawTransaction] = []
        normalized_by_id: dict[UUID, str] = {}

        # Tier 1: cache
        for txn in transactions:
            normalized = normalize_description(txn.description)
            normalized_by_id[txn.id] = normalized
            hit = await self.cache.lookup(user_id, normalized)
            if hit is None:
                misses.append(txn)
                continue
            category_id, confidence = hit
            results[txn.id] = CategorizedTransaction(
                id=txn.id,
                category_id=category_id,
                confidence=confidence,
                needs_review=confidence < CONFIDENCE_THRESHOLD,
                source="cache",
            )

        # Tier 2: Claude, batched
        for start in range(0, len(misses), BATCH_SIZE):
            chunk = misses[start:start + BATCH_SIZE]
            ai_results = await self.classifier.classify_batch(
                [t.description for t in chunk], list(name_to_id.keys())
            )
            for r in ai_results:
                txn = chunk[r["index"]]
                category_id = name_to_id.get(r["category"])
                confidence = float(r["confidence"])
                results[txn.id] = CategorizedTransaction(
                    id=txn.id,
                    category_id=category_id,
                    confidence=confidence,
                    needs_review=confidence < CONFIDENCE_THRESHOLD,
                    source="ai",
                )
                if category_id is not None:
                    await self.cache.record(
                        user_id, normalized_by_id[txn.id], category_id, source="ai_suggestion"
                    )

        return list(results.values())
