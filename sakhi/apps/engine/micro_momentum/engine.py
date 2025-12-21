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


async def generate_micro_momentum(person_id: str) -> Dict[str, Any]:
    """Deterministic micro-momentum nudge (no LLM)."""
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
    momentum_row = await _safe_fetch(
        """
        SELECT momentum_hint, suggested_start, reason
        FROM morning_momentum_cache
        WHERE person_id = $1 AND momentum_date = $2
        """,
        resolved,
        today,
        one=True,
    )
    ask_row = await _safe_fetch(
        """
        SELECT question, reason
        FROM morning_ask_cache
        WHERE person_id = $1 AND ask_date = $2
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

    reminders = (momentum_row.get("suggested_start") or "") or (preview_row.get("reminders") or [])
    pending = closure_row.get("pending") or []
    key_tasks = preview_row.get("key_tasks") or []
    focus_areas = preview_row.get("focus_areas") or []
    todo_tasks = tasks_row.get("labels") or []

    nudge = "Start with a simple grounding step to get moving."
    reason = "default"

    if pending:
        nudge = "Clear one small leftover item—it will give you quick momentum."
        reason = "pending"
    elif isinstance(reminders, list) and reminders:
        nudge = "Clear one small leftover item—it will give you quick momentum."
        reason = "pending"
    elif todo_tasks and len(todo_tasks) > 3:
        nudge = "Pick the smallest task and begin with a 2-minute version of it."
        reason = "many_tasks"
    elif key_tasks:
        nudge = "Try taking the first tiny step on your main task."
        reason = "key_task"
    elif focus_areas:
        nudge = "Do one tiny action that activates your focus area."
        reason = "focus"

    return {
        "date": today.isoformat(),
        "nudge": nudge,
        "reason": reason,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


async def persist_micro_momentum(person_id: str, nudge: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    nudge_date = datetime.date.fromisoformat(nudge.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO micro_momentum_cache (person_id, nudge_date, nudge, reason)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (person_id, nudge_date)
            DO UPDATE SET nudge = EXCLUDED.nudge,
                          reason = EXCLUDED.reason,
                          generated_at = now()
            """,
            resolved,
            nudge_date,
            nudge.get("nudge") or "",
            nudge.get("reason") or "",
        )
    except Exception:
        return

    try:
        await dbexec(
            "UPDATE personal_model SET micro_momentum_state = $2 WHERE person_id = $1",
            resolved,
            nudge,
        )
    except Exception:
        return


__all__ = ["generate_micro_momentum", "persist_micro_momentum"]
