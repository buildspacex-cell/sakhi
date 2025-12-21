from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.worker.utils.db import db_find
from sakhi.apps.worker.utils.response_composer import compose_response

LOGGER = logging.getLogger(__name__)


async def reflect_morning_presence(person_id: str) -> None:
    """
    Morning awareness reflection: summarize yesterday + today’s start.
    """
    db = await get_db()
    try:
        open_tasks: List[Dict[str, Any]] = db_find("tasks", {"user_id": person_id, "status": "todo"})
        summary_text = f"{len(open_tasks)} open tasks" if open_tasks else "A clear day ahead"
        mood_today = "balanced"
        open_actions = [task.get("title", "Task") for task in open_tasks]

        payload_json = json.dumps(open_actions or {}, ensure_ascii=False)
        status = await db.execute(
            """
            UPDATE presence_state
            SET date = CURRENT_DATE,
                summary = $2,
                mood_today = $3,
                open_actions = $4::jsonb,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            summary_text,
            mood_today,
            payload_json,
        )

        if not status or status.strip().endswith("0"):
            await db.execute(
                """
                INSERT INTO presence_state (person_id, date, summary, mood_today, open_actions, created_at, updated_at)
                VALUES ($1, CURRENT_DATE, $2, $3, $4::jsonb, NOW(), NOW())
                """,
                person_id,
                summary_text,
                mood_today,
                payload_json,
            )
    finally:
        await db.close()

    reply = await compose_response(
        person_id,
        intent="morning_checkin",
        context={"open_tasks": len(open_tasks), "summary": summary_text},
    )
    send_message(person_id, reply)


def send_message(person_id: str, text: str) -> None:
    LOGGER.info("morning_presence message person_id=%s text=%s", person_id, text)


__all__ = ["reflect_morning_presence"]
