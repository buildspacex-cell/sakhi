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


async def generate_evening_closure(person_id: str) -> Dict[str, Any]:
    """Deterministic evening closure summary (no LLM)."""
    resolved = await resolve_person_id(person_id) or person_id
    today = datetime.date.today()

    continuity_row = await _safe_fetch(
        "SELECT continuity_state FROM session_continuity WHERE person_id = $1",
        resolved,
        one=True,
    )
    continuity_state = continuity_row.get("continuity_state") or {}
    last_tasks: List[Mapping[str, Any]] = continuity_state.get("last_tasks") or []
    completed = [t for t in last_tasks if (t.get("status") or "").lower() in {"done", "completed"}]
    pending = [t for t in last_tasks if (t.get("status") or "").lower() not in {"done", "completed"}]

    emotions = continuity_state.get("last_emotion_snapshots") or []
    energy = "steady"
    if len(emotions) > 5:
        energy = "active"
    elif len(emotions) == 0:
        energy = "light"

    signals = {
        "energy": energy,
        "emotion": emotions[-1].get("mode") if emotions and isinstance(emotions[-1], dict) else "neutral",
    }
    summary = f"Completed:{len(completed)} Pending:{len(pending)} Energy:{energy}"

    return {
        "date": today.isoformat(),
        "completed": completed,
        "pending": pending,
        "signals": signals,
        "summary": summary,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


async def persist_evening_closure(person_id: str, closure: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    closure_date = datetime.date.fromisoformat(closure.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO daily_closure_cache (person_id, closure_date, completed, pending, signals, summary)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (person_id, closure_date)
            DO UPDATE SET completed = EXCLUDED.completed,
                          pending = EXCLUDED.pending,
                          signals = EXCLUDED.signals,
                          summary = EXCLUDED.summary,
                          generated_at = now()
            """,
            resolved,
            closure_date,
            closure.get("completed") or [],
            closure.get("pending") or [],
            closure.get("signals") or {},
            closure.get("summary") or "",
        )
    except Exception:
        return

    try:
        await dbexec(
            """
            UPDATE personal_model
            SET closure_state = $2
            WHERE person_id = $1
            """,
            resolved,
            closure,
        )
    except Exception:
        return


__all__ = ["generate_evening_closure", "persist_evening_closure"]
