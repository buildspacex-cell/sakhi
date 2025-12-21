from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone, date
import json
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q, exec as dbexec

# Config
PLANNER_ROLLUP_WINDOW_DAYS = int(os.getenv("PLANNER_ROLLUP_WINDOW_DAYS", "7") or "7")

OPEN_STATUSES = {"pending", "open", "in_progress", "overdue"}
OVERDUE_THRESHOLD = 3
CARRYOVER_THRESHOLD = 0.4
FRAGMENTATION_THRESHOLD = 0.6


def _safe_status(value: Any) -> str:
    return str(value or "").lower()


def _bucket_horizon(horizon: Any) -> str:
    slug = str(horizon or "").lower()
    if slug in {"today", "day"}:
        return "today"
    if slug in {"week", "weekly"}:
        return "week"
    if slug in {"month", "monthly"}:
        return "month"
    return "later"


def _fragmentation_score(open_count: int, horizons: List[str], priorities: List[int]) -> float:
    open_component = min(1.0, open_count / 20.0)
    horizon_spread = len(set(horizons)) / 4.0 if horizons else 0.0
    if priorities:
        p_min, p_max = min(priorities), max(priorities)
        priority_spread = (p_max - p_min) / max(1.0, float(p_max))
    else:
        priority_spread = 0.0
    score = (open_component * 0.5) + (horizon_spread * 0.25) + (priority_spread * 0.25)
    return round(max(0.0, min(1.0, score)), 3)


def _compute_pressure(
    items: List[Dict[str, Any]], now: datetime, window_start: date, window_end: date
) -> Tuple[Dict[str, Any], float]:
    open_items = [i for i in items if _safe_status(i.get("status")) in OPEN_STATUSES]

    def _to_date(value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
        except Exception:
            return None

    due_dates = [_to_date(i.get("due_ts")) for i in open_items if _to_date(i.get("due_ts"))]
    overdue = [d for d in due_dates if d and d < window_end]
    due_this_week = [d for d in due_dates if d and window_start <= d <= window_end]

    priorities = [int(i.get("priority")) for i in open_items if i.get("priority") is not None]
    urgent = [p for p in priorities if p >= 3]

    open_count = len(open_items)
    overdue_count = len(overdue)
    due_this_week_count = len(due_this_week)
    created_this_week_count = 0  # created_at not available on planned_items
    completed_this_week_count = 0  # updated_at not available on planned_items

    carryover = [d for d in due_dates if d and d < window_end]
    carryover_rate = round(len(carryover) / max(1, open_count), 3) if open_count else 0.0
    urgency_ratio = round(len(urgent) / max(1, open_count), 3) if open_count else 0.0
    deadline_density = round(due_this_week_count / max(1, PLANNER_ROLLUP_WINDOW_DAYS), 3)

    horizons = [_bucket_horizon(i.get("horizon")) for i in open_items]
    horizon_mix = {bucket: horizons.count(bucket) for bucket in ("today", "week", "month", "later")}

    frag_score = _fragmentation_score(open_count, horizons, priorities)
    overload_conditions = sum(
        [
            overdue_count > OVERDUE_THRESHOLD,
            carryover_rate > CARRYOVER_THRESHOLD,
            frag_score > FRAGMENTATION_THRESHOLD,
        ]
    )
    overload_flag = overload_conditions >= 2

    pressure = {
        "open_count": open_count,
        "overdue_count": overdue_count,
        "due_this_week": due_this_week_count,
        "created_this_week": created_this_week_count,
        "completed_this_week": completed_this_week_count,
        "carryover_rate": carryover_rate,
        "urgency_ratio": urgency_ratio,
        "deadline_density": deadline_density,
        "fragmentation_score": frag_score,
        "horizon_mix": horizon_mix,
        "overload_flag": overload_flag,
    }

    confidence = round(min(1.0, len(items) / 20.0), 3)
    return pressure, confidence


async def run_weekly_planner_pressure(person_id: str | None = None) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=PLANNER_ROLLUP_WINDOW_DAYS)).date()
    window_end = now.date()

    if person_id:
        persons = [{"person_id": person_id}]
    else:
        persons = await q("SELECT DISTINCT person_id FROM planned_items")

    results = {"processed": 0, "updated": 0}

    for row in persons:
        pid = row.get("person_id") or row.get("id")
        if not pid:
            continue

        planned = await q(
            """
            SELECT status, due_ts, priority, horizon, energy, ease
            FROM planned_items
            WHERE person_id = $1
              AND (
                    (due_ts::date BETWEEN $2 AND $3)
                 OR status IN ('open','in_progress','overdue','pending')
              )
            """,
            pid,
            window_start,
            window_end,
        )

        pressure, confidence = _compute_pressure(planned or [], now, window_start, window_end)
        pressure_json = json.dumps(pressure)

        await dbexec(
            """
            INSERT INTO planner_weekly_pressure (person_id, week_start, week_end, pressure, confidence, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, NOW())
            ON CONFLICT (person_id, week_start) DO UPDATE
            SET pressure = EXCLUDED.pressure,
                confidence = EXCLUDED.confidence,
                week_end = EXCLUDED.week_end,
                created_at = NOW()
            """,
            pid,
            window_start,
            window_end,
            pressure_json,
            confidence,
        )
        results["processed"] += 1
        results["updated"] += 1

    return results


__all__ = ["run_weekly_planner_pressure", "_compute_pressure"]
