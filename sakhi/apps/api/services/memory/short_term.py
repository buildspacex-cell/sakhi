from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.libs.json_utils import json_safe


async def enrich_short_term_memory(
    person_id: str,
    entry_id: str,
    text: str,
    topics: List[str],
    emotion: Dict[str, Any],
    embedding: List[float],
) -> None:
    """
    Append short-term memory slice into personal_model.short_term.
    Keeps last ~20 items.
    """

    db = await get_db()
    try:
        row = await db.fetchrow(
            "SELECT short_term FROM personal_model WHERE person_id = $1",
            person_id,
        )
        current = row.get("short_term") if row else None
        if isinstance(current, list):
            items = current
        elif isinstance(current, dict) and isinstance(current.get("entries"), list):
            items = current["entries"]
        else:
            items = []

        items.append(
            {
                "entry_id": entry_id,
                "text": text,
                "topics": topics or [],
                "emotion": emotion or {},
                "embedding": embedding or [],
            }
        )
        items = items[-20:]

        await db.execute(
            """
            UPDATE personal_model
            SET short_term = $2::jsonb,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            json.dumps(json_safe(items), ensure_ascii=False),
        )
    finally:
        await db.close()


__all__ = ["enrich_short_term_memory"]
