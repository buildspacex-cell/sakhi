from __future__ import annotations

import datetime
from typing import Any, Dict, Mapping

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.mini_flow.adjuster import determine_rhythm_slot, adjust_mini_flow


async def _safe_fetch(sql: str, *args: Any, one: bool = False) -> Mapping[str, Any]:
    try:
        row = await q(sql, *args, one=one)
        return row or {}
    except Exception:
        return {}


def _default_flow(source: str) -> Dict[str, Any]:
    return {
        "warmup_step": "Set up your workspace for one minute.",
        "focus_block_step": "Continue on a small step for 6–10 minutes.",
        "closure_step": "Wrap with a quick note of progress.",
        "optional_reward": "Take a 1-minute breather.",
        "source": source,
    }


async def generate_mini_flow(person_id: str, focus_path: Dict[str, Any] | None = None) -> Dict[str, Any]:
    resolved = await resolve_person_id(person_id) or person_id
    today = datetime.date.today()

    if focus_path is None:
        focus_path_row = await _safe_fetch(
            """
            SELECT anchor_step, progress_step, closure_step, intent_source
            FROM focus_path_cache
            WHERE person_id = $1 AND path_date = $2
            """,
            resolved,
            today,
            one=True,
        )
        focus_path = focus_path_row if isinstance(focus_path_row, dict) else {}

    tasks_row = await _safe_fetch(
        "SELECT array_agg(label) AS labels FROM tasks WHERE person_id=$1 AND status IN ('todo','in_progress')",
        resolved,
        one=True,
    )
    tasks = tasks_row.get("labels") or []

    flow = _default_flow("default")
    if focus_path:
        flow = {
            "warmup_step": "Review your anchor step briefly.",
            "focus_block_step": focus_path.get("progress_step") or "Continue for 6–10 focused minutes.",
            "closure_step": focus_path.get("closure_step") or "Wrap with a quick note of progress.",
            "optional_reward": "Stretch for 30 seconds.",
            "source": focus_path.get("intent_source") or "focus_path",
        }
    elif tasks:
        flow = {
            "warmup_step": "Set up your workspace for one minute.",
            "focus_block_step": "Pick one task and make 6–10 minutes of progress.",
            "closure_step": "Mark the task state or jot one line.",
            "optional_reward": "Take a 1-minute breather.",
            "source": "task",
        }

    rhythm_slot = determine_rhythm_slot(datetime.datetime.utcnow())
    flow = adjust_mini_flow(
        {
            "date": today.isoformat(),
            **flow,
            "generated_at": datetime.datetime.utcnow().isoformat(),
        },
        rhythm_slot,
    )
    flow["rhythm_slot"] = rhythm_slot
    return flow


async def persist_mini_flow(person_id: str, flow: Dict[str, Any]) -> None:
    resolved = await resolve_person_id(person_id) or person_id
    flow_date = datetime.date.fromisoformat(flow.get("date") or datetime.date.today().isoformat())
    try:
        await dbexec(
            """
            INSERT INTO mini_flow_cache (person_id, flow_date, warmup_step, focus_block_step, closure_step, optional_reward, source, rhythm_slot)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (person_id, flow_date)
            DO UPDATE SET warmup_step = EXCLUDED.warmup_step,
                          focus_block_step = EXCLUDED.focus_block_step,
                          closure_step = EXCLUDED.closure_step,
                          optional_reward = EXCLUDED.optional_reward,
                          source = EXCLUDED.source,
                          rhythm_slot = EXCLUDED.rhythm_slot,
                          generated_at = now()
            """,
            resolved,
            flow_date,
            flow.get("warmup_step") or "",
            flow.get("focus_block_step") or "",
            flow.get("closure_step") or "",
            flow.get("optional_reward") or "",
            flow.get("source") or "",
            flow.get("rhythm_slot"),
        )
    except Exception:
        return

    try:
        await dbexec(
            "UPDATE personal_model SET mini_flow_state = $2, mini_flow_rhythm_slot = $3 WHERE person_id = $1",
            resolved,
            flow,
            flow.get("rhythm_slot"),
        )
    except Exception:
        return


__all__ = ["generate_mini_flow", "persist_mini_flow"]
