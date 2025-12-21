from __future__ import annotations

import logging
import uuid

from sakhi.libs.embeddings import embed_text, to_pgvector
from sakhi.libs.schemas.db import get_async_pool

LOGGER = logging.getLogger(__name__)


def _coerce_uuid(value: uuid.UUID | str | None) -> uuid.UUID | str | None:
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except Exception:
        return value


async def upsert_session_vector(session_id: str, title: str | None, summary: str | None) -> None:
    parts = [(title or "").strip(), (summary or "").strip()]
    text_block = " ".join(part for part in parts if part)
    vector_literal: str | None = None

    if text_block:
        try:
            vec = await embed_text(text_block)
        except Exception as exc:  # pragma: no cover - defensive log
            LOGGER.warning("session_vector.embed_failed id=%s error=%s", session_id, exc)
            vec = []

        if isinstance(vec, list) and len(vec) == 1536:
            vector_literal = to_pgvector(vec)
        else:
            LOGGER.warning(
                "session_vector.invalid_vector id=%s len=%s",
                session_id,
                len(vec) if isinstance(vec, list) else "n/a",
            )

    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        if not vector_literal:
            await conn.execute(
                "UPDATE conversation_sessions SET summary_vec = NULL WHERE id = $1",
                session_uuid,
            )
        else:
            await conn.execute(
                "UPDATE conversation_sessions SET summary_vec = $2::vector WHERE id = $1",
                session_uuid,
                vector_literal,
            )
