from __future__ import annotations

import json
from typing import Any, Mapping

from sakhi.apps.api.core.db import get_db


async def log_event(
    person_id: str | None,
    layer: str,
    event: str,
    payload: Mapping[str, Any] | None = None,
) -> None:
    """Persist a structured system event for dev-console streaming."""

    if not person_id:
        return

    db = await get_db()
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    try:
        await db.execute(
            """
            INSERT INTO system_events (person_id, layer, event, payload)
            VALUES ($1, $2, $3, $4)
            """,
            person_id,
            layer,
            event,
            payload_json,
        )
    finally:
        await db.close()

    # Note: Brain refresh is now handled by background workers (episodic_consolidation, esr, etc.)
    # No inline state refresh needed here.


__all__ = ["log_event"]
