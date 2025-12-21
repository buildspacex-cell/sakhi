from __future__ import annotations

from sakhi.apps.api.core.db import get_db
from sakhi.libs.embeddings import embed_text, to_pgvector

JOURNAL_VECTOR_DIM = 1536


async def generate_journal_embedding(entry_id: str, text: str):
    """
    Compute deterministic 1536-d embedding for this entry and store it.
    """

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
            INSERT INTO journal_embeddings (entry_id, model, embedding_vec)
            VALUES ($1, 'text-embedding-3-small', $2::vector)
            ON CONFLICT (entry_id)
            DO UPDATE SET embedding_vec = EXCLUDED.embedding_vec
            """,
            entry_id,
            vector_literal,
        )
        return vector
    finally:
        await db.close()


__all__ = ["generate_journal_embedding"]
