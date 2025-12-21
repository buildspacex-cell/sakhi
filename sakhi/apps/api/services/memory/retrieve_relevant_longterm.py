from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

import numpy as np

from sakhi.apps.api.core.cache import cached
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.libs.embeddings import embed_text


@cached(ttl=600)
async def get_relevant_longterm_slice(
    person_id: str, latest_message: str, top_k: int = 5
) -> List[Dict[str, Any]]:
    """Return the top-k most relevant long-term memory snippets for a message."""
    if not latest_message or not latest_message.strip():
        return []

    rows = await dbfetch(
        """
        SELECT label, content, embedding
        FROM personal_embeddings
        WHERE person_id = $1
        """,
        person_id,
    )

    if not rows:
        return []

    message_vector = np.array(await embed_text(latest_message), dtype=float)
    message_norm = np.linalg.norm(message_vector)
    if message_norm == 0 or np.isnan(message_norm):
        return []

    scored: List[Dict[str, Any]] = []
    for row in rows:
        embedding = _coerce_embedding(row.get("embedding"))
        if embedding is None:
            continue

        vector = np.array(embedding, dtype=float)
        vector_norm = np.linalg.norm(vector)
        if vector_norm == 0 or np.isnan(vector_norm):
            continue

        similarity = float(np.dot(message_vector, vector) / (message_norm * vector_norm))
        scored.append(
            {
                "label": row.get("label"),
                "text": row.get("content"),
                "score": similarity,
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[: max(top_k, 0)]


def _coerce_embedding(value: Any) -> Iterable[float] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, (list, tuple)):
                return parsed
        except json.JSONDecodeError:
            return None
    return None
