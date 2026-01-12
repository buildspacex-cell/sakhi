from __future__ import annotations

import datetime as dt
from sakhi.apps.api.core.db import get_db
from sakhi.libs.embeddings import embed_text, to_pgvector

JOURNAL_VECTOR_DIM = 1536


def _normalize_ts(value: dt.datetime | str | None) -> dt.datetime:
    if isinstance(value, dt.datetime):
        if value.tzinfo:
            return value.astimezone(dt.timezone.utc)
        return value.replace(tzinfo=dt.timezone.utc)
    if isinstance(value, str):
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo:
                return parsed.astimezone(dt.timezone.utc)
            return parsed.replace(tzinfo=dt.timezone.utc)
        except Exception:
            pass
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)


async def generate_journal_embedding(entry_id: str, text: str, *, created_at: dt.datetime | str | None = None):
    """
    Compute deterministic 1536-d embedding for this entry and store it.
    """

    ts = _normalize_ts(created_at)
    vector = await embed_text(text)
    if isinstance(vector, list) and vector and isinstance(vector[0], list):
        vector = vector[0]
    if not isinstance(vector, list):
        vector = []

    vector_literal = to_pgvector(vector, length=JOURNAL_VECTOR_DIM)

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO journal_embeddings (entry_id, model, embedding_vec, created_at)
            VALUES ($1, 'text-embedding-3-small', $2::vector, $3)
            ON CONFLICT (entry_id)
            DO UPDATE SET embedding_vec = EXCLUDED.embedding_vec,
                          created_at = EXCLUDED.created_at
            """,
            entry_id,
            vector_literal,
            ts,
        )
        return vector
    finally:
        await db.close()


__all__ = ["generate_journal_embedding"]
