from __future__ import annotations

import json
import logging
from typing import Any, List

import numpy as np

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.services.memory.personal_model import synthesize_layer
from sakhi.libs.embeddings import parse_pgvector

LOGGER = logging.getLogger(__name__)


def _coerce_vector(raw: Any) -> List[float]:
    """Return a float vector (1536-d) from common storage formats."""

    if raw is None:
        return []
    if isinstance(raw, list):
        try:
            vec = [float(x) for x in raw]
        except (TypeError, ValueError):
            return []
        return vec

    if isinstance(raw, (bytes, bytearray, memoryview)):
        raw = raw.tobytes().decode("utf-8", errors="ignore")

    if isinstance(raw, str):
        parsed = parse_pgvector(raw)
        if parsed:
            return parsed
        stripped = raw.strip().lstrip("[{").rstrip("}]")
        try:
            parts = [float(part) for part in stripped.split(",") if part.strip()]
        except ValueError:
            return []
        return parts

    parsed = parse_pgvector(raw)
    if parsed:
        return parsed
    return []


async def consolidate_embeddings_for_user(person_id: str) -> None:
    """
    Consolidate various embeddings into a centroid and merge into personal_model.long_term.
    """

    db = await get_db()
    try:
        journal_rows = await db.fetch(
            """
            SELECT je.embedding_vec
            FROM journal_embeddings je
            JOIN journal_entries e ON je.entry_id = e.id
            WHERE e.user_id = $1
              AND je.embedding_vec IS NOT NULL
            LIMIT 500
            """,
            person_id,
        )

        theme_rows = await db.fetch(
            """
            SELECT embed_vec
            FROM themes
            WHERE person_id = $1
              AND embed_vec IS NOT NULL
            """,
            person_id,
        )

        personal_rows = await db.fetch(
            """
            SELECT embedding
            FROM personal_embeddings
            WHERE person_id = $1
              AND embedding IS NOT NULL
            """,
            person_id,
        )

        vectors: List[np.ndarray] = []
        for row in journal_rows + theme_rows + personal_rows:
            raw_value = row.get("embedding_vec") or row.get("embed_vec") or row.get("embedding")
            vec = _coerce_vector(raw_value)
            if len(vec) == 1536:
                vectors.append(np.array(vec, dtype=float))

        if not vectors:
            LOGGER.warning("[Embed Consolidation] No vectors available for %s", person_id)
            return

        centroid = np.mean(vectors, axis=0).tolist()

        current = await db.fetchrow(
            "SELECT long_term FROM personal_model WHERE person_id = $1",
            person_id,
        )
        long_term = current.get("long_term") if current else None

        merged = synthesize_layer(
            long_term if isinstance(long_term, dict) else {},
            {"observations": [], "layers": {}, "embedding_centroid": centroid},
        )
        merged["embedding_centroid"] = centroid

        await db.execute(
            """
            UPDATE personal_model
            SET long_term = $2::jsonb,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            json.dumps(merged, ensure_ascii=False),
        )

        LOGGER.info("[Embed Consolidation] Updated centroid for %s", person_id)
    finally:
        await db.close()


__all__ = ["consolidate_embeddings_for_user"]
