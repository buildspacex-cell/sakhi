from __future__ import annotations

import datetime
import re
import uuid
from typing import Any, Dict

from sakhi.apps.worker.utils.db import db_fetch, db_insert, db_update, db_upsert


async def create_draft_task(person_id: str, intent: Dict[str, Any]) -> str:
    """Create a draft task record and return its identifier."""
    record = {
        "id": intent.get("task_id") or str(uuid.uuid4()),
        "user_id": person_id,
        "title": intent.get("action_title") or "Untitled task",
        "status": "draft",
        "timeline": intent.get("timeline_hint", "none"),
        "clarity_score": 0.4,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    db_insert("tasks", record)
    return str(record["id"])


async def update_task_fields(person_id: str, task_id: str, message: str) -> bool:
    """Update a draft task's metadata using natural language hints."""
    if not task_id:
        return False

    task = db_fetch("tasks", {"id": task_id, "user_id": person_id})
    if not task:
        return False

    updates: Dict[str, Any] = {}
    lowered = (message or "").lower()
    if re.search(r"today|tomorrow|next week", lowered, re.I):
        updates["due_at"] = datetime.datetime.utcnow().isoformat()
    if re.search(r"high|urgent|important", lowered, re.I):
        updates["priority"] = 3
    if "cancel" in lowered:
        updates["status"] = "skipped"

    if not updates:
        return False

    for field, value in updates.items():
        db_insert(
            "task_enrichment_log",
            {
                "task_id": task_id,
                "field_name": field,
                "new_value": str(value),
                "logged_at": datetime.datetime.utcnow().isoformat(),
            },
        )
    db_update("tasks", {"id": task_id}, updates)
    return True


def _extract_date_hint(text: str) -> str | None:
    if "tomorrow" in text:
        return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    if "today" in text or "tonight" in text:
        return datetime.date.today().isoformat()
    match = re.search(r"next (monday|tuesday|wednesday|thursday|friday|saturday|sunday)", text)
    if match:
        target = match.group(1)
        return f"next {target}"
    return None


def _extract_priority(text: str) -> str | None:
    if any(word in text for word in ("urgent", "asap", "important")):
        return "high"
    if "maybe" in text or "if time" in text:
        return "low"
    if "later" in text:
        return "medium"
    return None


__all__ = ["create_draft_task", "update_task_fields"]
