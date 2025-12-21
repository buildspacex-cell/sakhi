from __future__ import annotations

import datetime
from typing import Any, Dict, Mapping

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id


async def _safe_fetch(sql: str, *args: Any, one: bool = False) -> Mapping[str, Any]:
    try:
        row = await q(sql, *args, one=one)
        return row or {}
    except Exception:
        return {}


async def generate_morning_ask(person_id: str) -> Dict[str, Any]:
    """Deterministic morning ask (no LLM)."""
    resolved = await resolve_person_id(person_id) or person_id
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    preview_row = await _safe_fetch(
        """
        SELECT focus_areas, key_tasks, reminders
        FROM morning_preview_cache
        WHERE person_id = $1 AND preview_date = $2
        """,
        resolved,
        today,
        one=True,
    )
    closure_row = await _safe_fetch(
        """
        SELECT pending
        FROM daily_closure_cache
        WHERE person_id = $1 AND closure_date = $2
        """,
        resolved,
        yesterday,
        one=True,
    )
    tasks_row = await _safe_fetch(
        "SELECT array_agg(label) AS labels FROM tasks WHERE person_id = $1 AND status = 'todo'",
        resolved,
        one=True,
    )
    focus_areas = preview_row.get("focus_areas") or []
    key_tasks = preview_row.get("key_tasks") or []
    reminders = preview_row.get("reminders") or []
    pending = closure_row.get("pending") or []
    todo_tasks = tasks_row.get("labels") or []

    question = "How would you like to begin your morning?"
    reason = "default"
    if reminders:
        question = "Would you like to clear one small item from yesterday first?"
        reason = "pending_items"
    elif len(focus_areas) > 1:
        question = "Which focus area would you like to start with today?"
        reason = "multi_focus"
    elif key_tasks:
        question = "Which of your key tasks feels right to begin with?"
        reason = "key_tasks"
    elif todo_tasks:
        question = "Which open task should we start with?"
        reason = "open_tasks"

    return {
        "date": today.isoformat(),
        "question": question,
        "reason": reason,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


async def persist_morning_ask(person_id: str, ask: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    ask_date = datetime.date.fromisoformat(ask.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO morning_ask_cache (person_id, ask_date, question, reason)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (person_id, ask_date)
            DO UPDATE SET question = EXCLUDED.question,
                          reason = EXCLUDED.reason,
                          generated_at = now()
            """,
            resolved,
            ask_date,
            ask.get("question") or "",
            ask.get("reason") or "",
        )
    except Exception:
        return

    try:
        await dbexec(
            "UPDATE personal_model SET morning_ask_state = $2 WHERE person_id = $1",
            resolved,
            ask,
        )
    except Exception:
        return


__all__ = ["generate_morning_ask", "persist_morning_ask"]
