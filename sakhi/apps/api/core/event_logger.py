from __future__ import annotations

import asyncio
import json
from typing import Any, Mapping

from sakhi.apps.api.core.db import get_db
from sakhi.apps.logic.brain import brain_engine

_BRAIN_TRIGGER_LAYERS = {
    "journal",
    "turn",
    "planner",
    "focus",
    "relationship",
    "rhythm",
    "environment",
    "summary",
}


async def log_event(
    person_id: str | None,
    layer: str,
    event: str,
    payload: Mapping[str, Any] | None = None,
) -> None:
    """Persist a structured system event for dev-console streaming and trigger brain refresh."""

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

    if layer in _BRAIN_TRIGGER_LAYERS:
        asyncio.create_task(brain_engine.refresh_brain(person_id, refresh_journey=True))


__all__ = ["log_event"]
