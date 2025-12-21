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


async def generate_morning_momentum(person_id: str) -> Dict[str, Any]:
    """Deterministic morning momentum (no LLM)."""
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

    pending = closure_row.get("pending") or []
    focus_areas = preview_row.get("focus_areas") or []
    key_tasks = preview_row.get("key_tasks") or []
    reminders = preview_row.get("reminders") or pending
    todo_tasks = tasks_row.get("labels") or []

    momentum_hint = "Start with a simple grounding action."
    reason = "low_load"
    suggested_start = ""

    if reminders:
        momentum_hint = "Clear one leftover item to gain early momentum."
        reason = "pending"
        suggested_start = reminders[0] if reminders else ""
    elif len(key_tasks) > 1:
        momentum_hint = "Choose one key task to start your morning strongly."
        reason = "multi_task"
        suggested_start = key_tasks[0]
    elif len(focus_areas) > 1:
        momentum_hint = "Pick one small step to activate your main focus."
        reason = "multi_focus"
        suggested_start = focus_areas[0]
    elif todo_tasks:
        momentum_hint = "Which open task should we start with?"
        reason = "open_tasks"
        suggested_start = todo_tasks[0]

    return {
        "date": today.isoformat(),
        "momentum_hint": momentum_hint,
        "suggested_start": suggested_start,
        "reason": reason,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


async def persist_morning_momentum(person_id: str, momentum: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    momentum_date = datetime.date.fromisoformat(momentum.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO morning_momentum_cache (person_id, momentum_date, momentum_hint, suggested_start, reason)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (person_id, momentum_date)
            DO UPDATE SET momentum_hint = EXCLUDED.momentum_hint,
                          suggested_start = EXCLUDED.suggested_start,
                          reason = EXCLUDED.reason,
                          generated_at = now()
            """,
            resolved,
            momentum_date,
            momentum.get("momentum_hint") or "",
            momentum.get("suggested_start") or "",
            momentum.get("reason") or "",
        )
    except Exception:
        return

    try:
        await dbexec(
            "UPDATE personal_model SET morning_momentum_state = $2 WHERE person_id = $1",
            resolved,
            momentum,
        )
    except Exception:
        return


__all__ = ["generate_morning_momentum", "persist_morning_momentum"]
