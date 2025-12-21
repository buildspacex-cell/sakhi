from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from sakhi.apps.worker.utils.db import db_find
from sakhi.apps.worker.utils.response_composer import compose_response

LOGGER = logging.getLogger(__name__)


def complete_task_enrichment() -> None:
    """
    Check for draft tasks missing fields and nudge the user.
    """
    asyncio.run(_complete_task_enrichment_async())


async def _complete_task_enrichment_async() -> None:
    drafts: List[Dict[str, Any]] = db_find("tasks", {"status": "draft"})
    for task in drafts:
        missing = [field for field in ("due_at", "priority") if not task.get(field)]
        if not missing:
            continue
        person_id = task.get("user_id") or "unknown"
        title = task.get("title", "your task")
        reply = await compose_response(
            person_id,
            intent="reflective_nudge",
            context={"task": title, "missing_fields": missing},
        )
        send_message_to_user(person_id, reply)


def send_message_to_user(person_id: Any, text: str) -> None:
    LOGGER.info("task_enrichment.nudge person_id=%s text=%s", person_id, text)


__all__ = ["complete_task_enrichment"]
