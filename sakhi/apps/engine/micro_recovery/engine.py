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


async def generate_micro_recovery(person_id: str) -> Dict[str, Any]:
    """Deterministic micro-recovery nudge (no LLM, no inference)."""
    resolved = await resolve_person_id(person_id) or person_id
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Inputs
    momentum_row = await _safe_fetch(
        "SELECT momentum_hint, suggested_start FROM morning_momentum_cache WHERE person_id=$1 AND momentum_date=$2",
        resolved,
        today,
        one=True,
    )
    micro_row = await _safe_fetch(
        "SELECT nudge FROM micro_momentum_cache WHERE person_id=$1 AND nudge_date=$2",
        resolved,
        today,
        one=True,
    )
    closure_row = await _safe_fetch(
        "SELECT pending FROM daily_closure_cache WHERE person_id=$1 AND closure_date=$2",
        resolved,
        yesterday,
        one=True,
    )
    tasks_row = await _safe_fetch(
        "SELECT COUNT(*) AS open_count, COUNT(*) FILTER (WHERE status='in_progress') AS active_count FROM tasks WHERE person_id=$1 AND status IN ('todo','in_progress')",
        resolved,
        one=True,
    )
    last_turn_row = await _safe_fetch(
        "SELECT created_at FROM conversation_turns WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1",
        resolved,
        one=True,
    )

    open_tasks = int(tasks_row.get("open_count") or 0)
    active_tasks = int(tasks_row.get("active_count") or 0)
    pending = closure_row.get("pending") or []
    has_leftover = isinstance(pending, list) and len(pending) > 0

    now = datetime.datetime.utcnow()
    last_ts = last_turn_row.get("created_at")
    gap_hours = None
    if last_ts:
        try:
            delta = now - last_ts
            gap_hours = delta.total_seconds() / 3600.0
        except Exception:
            gap_hours = None

    reason = "default"
    nudge = "Start with a simple grounding step to reset."

    if gap_hours is not None and gap_hours > 3:
        reason = "return_gap"
        nudge = "Pick one tiny step to warm up again."
    elif active_tasks > 0:
        reason = "context_switch"
        nudge = "Resume with one small continuation step."
    elif open_tasks > 3:
        reason = "many_tasks"
        nudge = "Try clearing a tiny item to reset your flow."
    elif has_leftover:
        reason = "leftover"
        nudge = "A small leftover from yesterday can be a gentle restart."
    elif momentum_row.get("suggested_start") or micro_row.get("nudge"):
        reason = "context_switch"
        nudge = "Resume with one small continuation step."

    return {
        "date": today.isoformat(),
        "nudge": nudge,
        "reason": reason,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


async def persist_micro_recovery(person_id: str, rec: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    rec_date = datetime.date.fromisoformat(rec.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO micro_recovery_cache (person_id, recovery_date, nudge, reason)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (person_id, recovery_date)
            DO UPDATE SET nudge = EXCLUDED.nudge,
                          reason = EXCLUDED.reason,
                          generated_at = now()
            """,
            resolved,
            rec_date,
            rec.get("nudge") or "",
            rec.get("reason") or "",
        )
    except Exception:
        return

    try:
        await dbexec(
            "UPDATE personal_model SET micro_recovery_state = $2 WHERE person_id = $1",
            resolved,
            rec,
        )
    except Exception:
        return


__all__ = ["generate_micro_recovery", "persist_micro_recovery"]
