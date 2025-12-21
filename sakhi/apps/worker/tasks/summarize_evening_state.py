from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.worker.utils.db import db_find
from sakhi.apps.worker.utils.response_composer import compose_response

LOGGER = logging.getLogger(__name__)


async def summarize_evening_state(person_id: str) -> None:
    """
    End-of-day summary and reflection entry.
    """
    tasks_done: List[Dict[str, Any]] = db_find("tasks", {"user_id": person_id, "status": "done"})
    summary_text = f"Closed {len(tasks_done)} tasks today."
    open_actions: Dict[str, Any] | None = None

    db = await get_db()
    try:
        actions_json = json.dumps(open_actions or {}, ensure_ascii=False)
        await db.execute(
            """
            INSERT INTO presence_state (person_id, date, summary, mood_today, open_actions, created_at)
            VALUES ($1, CURRENT_DATE, $2, NULL, $3::jsonb, NOW())
            ON CONFLICT (person_id, date)
            DO UPDATE SET
                summary = EXCLUDED.summary,
                mood_today = EXCLUDED.mood_today,
                open_actions = EXCLUDED.open_actions,
                created_at = presence_state.created_at
            """,
            person_id,
            summary_text,
            actions_json,
        )
    finally:
        await db.close()

    reply = await compose_response(
        person_id,
        intent="evening_summary",
        context={"tasks_done": len(tasks_done)},
    )
    send_message(person_id, reply)


def send_message(person_id: str, text: str) -> None:
    LOGGER.info("evening_state message person_id=%s text=%s", person_id, text)


__all__ = ["summarize_evening_state"]
