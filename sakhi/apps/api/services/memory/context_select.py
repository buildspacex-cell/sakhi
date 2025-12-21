from __future__ import annotations

import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.libs.embeddings import embed_text

_LOGGER = logging.getLogger(__name__)


async def fetch_relevant_long_term(
    person_id: str, latest_text: str, limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Use pgvector similarity to fetch the most relevant past memories for a person.
    """
    if not person_id or not latest_text or not latest_text.strip():
        return []

    latest_vec = await embed_text(latest_text)
    if not latest_vec:
        return []

    try:
        rows = await dbfetch(
            """
            SELECT id,
                   type,
                   content,
                   metadata,
                   1 - (embedding <=> $2::vector) AS similarity
            FROM memory_items
            WHERE person_id = $1
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $2::vector
            LIMIT $3
            """,
            person_id,
            latest_vec,
            limit,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        _LOGGER.debug("Vector recall failed; returning empty result: %s", exc)
        return []

    results: List[Dict[str, Any]] = []
    for row in rows:
        similarity = _coerce_float(row.get("similarity"))
        item: Dict[str, Any] = {
            "id": str(row.get("id")),
            "type": row.get("type"),
            "content": row.get("content"),
            "metadata": row.get("metadata"),
            "similarity": round(similarity, 3) if similarity is not None else None,
        }
        results.append(item)

    return results


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
