from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec, q

HORIZON_WINDOWS = {
    "today": ("CURRENT_DATE", "CURRENT_DATE"),
    "week": ("CURRENT_DATE", "CURRENT_DATE + INTERVAL '7 days'"),
    "month": ("CURRENT_DATE", "CURRENT_DATE + INTERVAL '30 days'"),
    "quarter": ("CURRENT_DATE", "CURRENT_DATE + INTERVAL '90 days'"),
}


async def refresh_planner_cache(person_id: str) -> Dict[str, Any]:
    payload = await build_planner_summary(person_id)
    await dbexec(
        """
        INSERT INTO planner_context_cache (person_id, payload, updated_at)
        VALUES ($1, $2::jsonb, NOW())
        ON CONFLICT (person_id) DO UPDATE
        SET payload = EXCLUDED.payload,
            updated_at = NOW()
        """,
        person_id,
        json.dumps(payload, ensure_ascii=False),
    )
    return payload


async def build_planner_summary(person_id: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    for label, (start_expr, end_expr) in HORIZON_WINDOWS.items():
        rows = await q(
            f"""
            SELECT id, label, due_ts, priority, status, horizon, energy, ease, recurrence, meta
            FROM planned_items
            WHERE person_id = $1
              AND due_ts::date BETWEEN {start_expr} AND {end_expr}
            ORDER BY COALESCE(due_ts, NOW()), priority DESC
            """,
            person_id,
        )
        summary[label] = [_to_serializable(row) for row in rows]

    goals = await q(
        """
        SELECT id, title, details, horizon, priority, status
        FROM planner_goals
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 25
        """,
        person_id,
    )
    milestones = await q(
        """
        SELECT id, goal_id, title, due_ts, horizon, status, sequence
        FROM planner_milestones
        WHERE person_id = $1
        ORDER BY COALESCE(due_ts, NOW()), sequence
        LIMIT 50
        """,
        person_id,
    )

    summary["goals"] = [_to_serializable(row) for row in goals]
    summary["milestones"] = [_to_serializable(row) for row in milestones]
    summary["updated_at"] = datetime.now(timezone.utc).isoformat()
    return summary


def _to_serializable(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        row = dict(row)
    result: Dict[str, Any] = {}
    for key, value in row.items():
        if hasattr(value, "hex"):  # UUID
            result[key] = str(value)
        elif hasattr(value, "isoformat"):  # datetime
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


__all__ = ["build_planner_summary", "refresh_planner_cache"]
