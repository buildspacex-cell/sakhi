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


def _default_path(source: str) -> Dict[str, Any]:
    return {
        "anchor_step": "Choose one grounding action to begin.",
        "progress_step": "Extend it for a few focused minutes.",
        "closure_step": "Note how far you reached.",
        "intent_source": source,
    }


async def generate_focus_path(person_id: str, intent_text: str | None = None) -> Dict[str, Any]:
    """Deterministic focus path (no LLM, no inference)."""
    resolved = await resolve_person_id(person_id) or person_id
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    preview_row = await _safe_fetch(
        """
        SELECT key_tasks, reminders
        FROM morning_preview_cache
        WHERE person_id = $1 AND preview_date = $2
        """,
        resolved,
        today,
        one=True,
    )
    momentum_row = await _safe_fetch(
        """
        SELECT momentum_hint, suggested_start
        FROM morning_momentum_cache
        WHERE person_id = $1 AND momentum_date = $2
        """,
        resolved,
        today,
        one=True,
    )
    micro_row = await _safe_fetch(
        """
        SELECT nudge
        FROM micro_momentum_cache
        WHERE person_id = $1 AND nudge_date = $2
        """,
        resolved,
        today,
        one=True,
    )
    recovery_row = await _safe_fetch(
        """
        SELECT nudge
        FROM micro_recovery_cache
        WHERE person_id = $1 AND recovery_date = $2
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
        "SELECT array_agg(label) AS labels FROM tasks WHERE person_id=$1 AND status IN ('todo','in_progress')",
        resolved,
        one=True,
    )

    key_tasks = preview_row.get("key_tasks") or []
    reminders = preview_row.get("reminders") or []
    pending = closure_row.get("pending") or []
    tasks = tasks_row.get("labels") or []

    path = _default_path("default")

    if key_tasks:
        path = {
            "anchor_step": "Open the key task and complete the smallest subpart.",
            "progress_step": "Continue for a short focused burst.",
            "closure_step": "Mark progress or jot one-line reflection.",
            "intent_source": "key_task",
        }
    elif pending:
        path = {
            "anchor_step": "Clear the smallest leftover from yesterday.",
            "progress_step": "Move one step further on the same item.",
            "closure_step": "Update your pending list.",
            "intent_source": "leftover",
        }
    elif intent_text:
        path = {
            "anchor_step": "Take one tiny action toward your stated focus.",
            "progress_step": "Continue with a brief follow-on step.",
            "closure_step": "Note the progress on this focus.",
            "intent_source": "focus_signal",
        }
    elif tasks:
        path = {
            "anchor_step": "Open any task and complete the smallest subpart.",
            "progress_step": "Continue for a short focused burst.",
            "closure_step": "Mark the task state or jot a quick note.",
            "intent_source": "task",
        }
    elif reminders or momentum_row.get("suggested_start") or micro_row.get("nudge") or recovery_row.get("nudge"):
        path = {
            "anchor_step": "Resume with one small continuation step.",
            "progress_step": "Keep the same thread for a brief burst.",
            "closure_step": "Record what changed.",
            "intent_source": "focus_signal",
        }

    return {
        "date": today.isoformat(),
        **path,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


async def persist_focus_path(person_id: str, path: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    path_date = datetime.date.fromisoformat(path.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO focus_path_cache (person_id, path_date, anchor_step, progress_step, closure_step, intent_source)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (person_id, path_date)
            DO UPDATE SET anchor_step = EXCLUDED.anchor_step,
                          progress_step = EXCLUDED.progress_step,
                          closure_step = EXCLUDED.closure_step,
                          intent_source = EXCLUDED.intent_source,
                          generated_at = now()
            """,
            resolved,
            path_date,
            path.get("anchor_step") or "",
            path.get("progress_step") or "",
            path.get("closure_step") or "",
            path.get("intent_source") or "",
        )
    except Exception:
        return

    try:
        await dbexec(
            "UPDATE personal_model SET focus_path_state = $2 WHERE person_id = $1",
            resolved,
            path,
        )
    except Exception:
        return


__all__ = ["generate_focus_path", "persist_focus_path"]
