import asyncio
import datetime
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.core.db import q, exec as dbexec


def _sanitize(value: Any) -> Any:
    """Make payload JSON serializable (Decimal/datetime/date -> float/iso)."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    return value


async def _load_cache(person_id: str, scope: str) -> Optional[Dict[str, Any]]:
    row = await q(
        """
        SELECT payload FROM journey_cache
        WHERE person_id = $1 AND scope = $2
        """,
        person_id,
        scope,
        one=True,
    )
    if not row:
        return None
    return row["payload"]


async def _save_cache(person_id: str, scope: str, payload: Dict[str, Any]) -> None:
    sanitized = _sanitize(payload)
    await dbexec(
        """
        INSERT INTO journey_cache (person_id, scope, payload, updated_at)
        VALUES ($1, $2, $3::jsonb, NOW())
        ON CONFLICT (person_id, scope)
        DO UPDATE SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at
        """,
        person_id,
        scope,
        json.dumps(sanitized),
    )


async def _fetch_environment(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT weather, calendar_blocks, day_cycle, weekend_flag, holiday_flag,
               travel_flag, environment_tags, updated_at
        FROM environment_context
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    return _sanitize(row) if row else {}


async def _fetch_relationship(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT trust_score, attunement_score, emotional_safety, closeness_stage, updated_at
        FROM relationship_state
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    return _sanitize(row) if row else {}


async def _fetch_focus_sessions(person_id: str, since: datetime.datetime) -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT id, mode, start_time, end_time, completion_score, actual_duration
        FROM focus_sessions
        WHERE person_id = $1 AND start_time >= $2
        ORDER BY start_time DESC
        """,
        person_id,
        since,
    )
    return _sanitize(rows or [])


async def _fetch_rhythm_today(person_id: str, today: datetime.date) -> Dict[str, Any]:
    row = await q(
        """
        SELECT slots
        FROM rhythm_daily_curve
        WHERE person_id = $1 AND day_scope = $2::date
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        today,
        one=True,
    )
    if not row:
        return {}
    try:
        slots = json.loads(row["slots"]) if isinstance(row["slots"], str) else row["slots"]
    except Exception:
        slots = []
    # crude averages
    def avg_between(start_hour: int, end_hour: int) -> Optional[float]:
        vals = [
            s.get("energy")
            for s in slots
            if isinstance(s, dict)
            and "time" in s
            and start_hour <= int(str(s["time"]).split(":")[0]) < end_hour
        ]
        return float(sum(vals) / len(vals)) if vals else None

    return {
        "energy_morning": avg_between(5, 12),
        "energy_afternoon": avg_between(12, 17),
        "energy_evening": avg_between(17, 22),
    }


async def _fetch_weekly_summary(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT week_start, week_end, summary, highlights, top_themes, drift_score, created_at
        FROM memory_weekly_summaries
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    return _sanitize(row) if row else {}


async def _fetch_monthly_recap(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT month_scope, summary, highlights, top_themes, chapter_hint, drift_score, compression, created_at
        FROM memory_monthly_recaps
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    return _sanitize(row) if row else {}


async def _fetch_life_chapters(person_id: str) -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT arc_name, start_scope, end_scope, tags
        FROM life_arcs
        WHERE person_id = $1
        ORDER BY start_scope DESC
        """,
        person_id,
    )
    return [
        {
            "title": r["arc_name"],
            "start": _sanitize(r.get("start_scope")),
            "end": _sanitize(r.get("end_scope")),
            "identity": r.get("tags") or [],
            "themes": r.get("tags") or [],
        }
        for r in rows or []
    ]


async def get_today(person_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    if not force_refresh:
        cached = await _load_cache(person_id, "today")
        if cached:
            return cached

    now = datetime.datetime.utcnow()
    today_date = now.date()
    rhythm = await _fetch_rhythm_today(person_id, today_date)
    focus_sessions = await _fetch_focus_sessions(
        person_id, since=datetime.datetime.combine(today_date, datetime.time.min)
    )
    environment = await _fetch_environment(person_id)
    relationship = await _fetch_relationship(person_id)

    payload = {
        "date": str(today_date),
        "tasks": [],
        "rhythm": rhythm,
        "emotion": {"dominant": None, "trend": None},
        "focus_sessions": focus_sessions,
        "environment": environment,
        "suggestions": [],
        "relationship_state": relationship,
    }
    await _save_cache(person_id, "today", payload)
    return payload


async def get_week(person_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    if not force_refresh:
        cached = await _load_cache(person_id, "week")
        if cached:
            return cached

    relationship = await _fetch_relationship(person_id)
    weekly = await _fetch_weekly_summary(person_id)
    focus_sessions = await _fetch_focus_sessions(
        person_id, since=datetime.datetime.utcnow() - datetime.timedelta(days=7)
    )
    iso = datetime.date.today().isocalendar()
    payload = {
        "week_of": f"{iso.year}-W{iso.week:02d}",
        "goals": [],
        "progress": weekly.get("drift_score") if weekly else 0.0,
        "energy_pattern": [],
        "emotion_pattern": [],
        "milestones": [],
        "themes": weekly.get("top_themes") if weekly else [],
        "relationship_state": relationship,
        "focus_sessions": focus_sessions,
    }
    await _save_cache(person_id, "week", payload)
    return payload


async def get_month(person_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    if not force_refresh:
        cached = await _load_cache(person_id, "month")
        if cached:
            return cached

    monthly = await _fetch_monthly_recap(person_id)
    payload = {
        "month": datetime.date.today().strftime("%Y-%m"),
        "wins": [monthly.get("highlights")] if monthly.get("highlights") else [],
        "struggles": [],
        "habit_strength": {},
        "identity_shifts": [],
        "purpose_signals": [],
        "summary": monthly.get("summary"),
    }
    await _save_cache(person_id, "month", payload)
    return payload


async def get_life_chapters(person_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    if not force_refresh:
        cached = await _load_cache(person_id, "life")
        if cached:
            return cached

    chapters = await _fetch_life_chapters(person_id)
    payload = {"chapters": chapters}
    await _save_cache(person_id, "life", payload)
    return payload
