from __future__ import annotations

import datetime
from typing import Any, Dict, List, Mapping

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id


async def _safe_fetch(sql: str, *args: Any, one: bool = False) -> Mapping[str, Any]:
    try:
        row = await q(sql, *args, one=one)
        return row or {}
    except Exception:
        return {}


async def generate_morning_preview(person_id: str) -> Dict[str, Any]:
    """Deterministic morning preview (no LLM)."""
    resolved = await resolve_person_id(person_id) or person_id
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    closure_row = await _safe_fetch(
        """
        SELECT completed, pending, signals, summary
        FROM daily_closure_cache
        WHERE person_id = $1 AND closure_date = $2
        """,
        resolved,
        yesterday,
        one=True,
    )
    pending = closure_row.get("pending") or []
    reminders = pending[:5] if isinstance(pending, list) else []

    goals_row = await _safe_fetch(
        "SELECT goals_state, rhythm_state FROM personal_model WHERE person_id = $1",
        resolved,
        one=True,
    )
    goals_state = goals_row.get("goals_state") or {}
    rhythm_state = goals_row.get("rhythm_state") or {}
    rhythm_hint = (rhythm_state.get("day_cycle") if isinstance(rhythm_state, dict) else None) or "steady"

    tasks_rows = await _safe_fetch(
        "SELECT array_agg(label) AS labels FROM tasks WHERE person_id = $1 AND status = 'todo'",
        resolved,
        one=True,
    )
    key_tasks = tasks_rows.get("labels") or []

    # focus areas: surface categories from goals/tasks
    focus_areas: List[str] = []
    if isinstance(goals_state, dict):
        active_goals = goals_state.get("active_goals") or []
        if isinstance(active_goals, list):
            focus_areas = [g.get("title") for g in active_goals if isinstance(g, dict) and g.get("title")]
    if not focus_areas and key_tasks:
        focus_areas = ["tasks"]

    summary = f"Focus:{len(focus_areas)} KeyTasks:{len(key_tasks)} Reminders:{len(reminders)} Rhythm:{rhythm_hint}"

    return {
        "date": today.isoformat(),
        "focus_areas": focus_areas,
        "key_tasks": key_tasks,
        "reminders": reminders,
        "rhythm_hint": rhythm_hint,
        "summary": summary,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


async def persist_morning_preview(person_id: str, preview: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    preview_date = datetime.date.fromisoformat(preview.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO morning_preview_cache (person_id, preview_date, focus_areas, key_tasks, reminders, rhythm_hint, summary)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (person_id, preview_date)
            DO UPDATE SET focus_areas = EXCLUDED.focus_areas,
                          key_tasks = EXCLUDED.key_tasks,
                          reminders = EXCLUDED.reminders,
                          rhythm_hint = EXCLUDED.rhythm_hint,
                          summary = EXCLUDED.summary,
                          generated_at = now()
            """,
            resolved,
            preview_date,
            preview.get("focus_areas") or [],
            preview.get("key_tasks") or [],
            preview.get("reminders") or [],
            preview.get("rhythm_hint") or "",
            preview.get("summary") or "",
        )
    except Exception:
        return

    try:
        await dbexec(
            "UPDATE personal_model SET morning_preview_state = $2 WHERE person_id = $1",
            resolved,
            preview,
        )
    except Exception:
        return


__all__ = ["generate_morning_preview", "persist_morning_preview"]
