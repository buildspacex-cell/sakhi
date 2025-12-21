from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import exec as db_exec, q


async def recent_suggestions(person_id: str, *, window_hours: float) -> List[Dict[str, Any]]:
    """Fetch suggestions issued within the supplied rolling window."""
    seconds = max(0, int(window_hours * 3600))
    return await q(
        """
        SELECT id, suggestion, style, confidence, created_at, payload
        FROM conversation_suggestions
        WHERE person_id = $1
          AND created_at >= NOW() - ($2 * INTERVAL '1 second')
        ORDER BY created_at DESC
        """,
        person_id,
        seconds,
    )


async def has_recent_duplicate(person_id: str, suggestion: str, *, window_hours: float) -> bool:
    """Check if the same suggestion text was shown recently."""
    rows = await q(
        """
        SELECT 1
        FROM conversation_suggestions
        WHERE person_id = $1
          AND suggestion = $2
          AND created_at >= NOW() - ($3 * INTERVAL '1 second')
        LIMIT 1
        """,
        person_id,
        suggestion,
        int(window_hours * 3600),
    )
    return bool(rows)


async def record_suggestion(
    person_id: str,
    *,
    suggestion: str,
    style: Optional[str],
    confidence: Optional[float],
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist a delivered suggestion so policies can enforce cadence."""
    await db_exec(
        """
        INSERT INTO conversation_suggestions (person_id, suggestion, style, confidence, payload)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        person_id,
        suggestion,
        style,
        confidence,
        json.dumps(payload or {}),
    )
