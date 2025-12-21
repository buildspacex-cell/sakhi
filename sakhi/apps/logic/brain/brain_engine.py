from __future__ import annotations

import asyncio
import datetime
import json
from typing import Any, Dict, List, Optional
from decimal import Decimal

from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.logic.journey import renderer as journey_renderer


def _ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []
    return []


def _clamp(val: Optional[float], lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        f = float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, f))


def _sanitize(value: Any) -> Any:
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    return value


async def _fetch_planner_state(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT payload
        FROM planner_context_cache
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    payload = _ensure_dict((row or {}).get("payload"))
    return {
        "active_goals": payload.get("active_goals") or payload.get("goals") or [],
        "effort": payload.get("effort") or {},
        "confidence": float(payload.get("confidence") or 0.6),
        "blockers": payload.get("blockers") or [],
    }


async def _fetch_rhythm_state(person_id: str) -> Dict[str, Any]:
    try:
        row = await q(
            """
            SELECT body_energy, mind_focus, emotion_tone, fatigue_level, stress_level, next_peak, next_lull, payload
            FROM rhythm_state
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        row = None
    payload = _ensure_dict((row or {}).get("payload"))
    stress_level = _clamp((row or {}).get("stress_level"))
    fatigue_level = _clamp((row or {}).get("fatigue_level"))
    stress_trend = (
        payload.get("stress_trend")
        or ("rising" if stress_level > 0.65 else "dropping" if stress_level < 0.35 else "stable")
    )
    recovery_needs = "high" if (fatigue_level > 0.7 or stress_level > 0.7) else "med" if stress_level > 0.45 else "low"
    return {
        "energy_cycle": payload.get("energy_cycle") or [],
        "emotion_cycle": payload.get("emotion_cycle") or [],
        "stress_trend": stress_trend,
        "flow_peaks": payload.get("flow_peaks") or [],
        "recovery_needs": recovery_needs,
        "body_energy": _clamp((row or {}).get("body_energy")),
        "mind_focus": _clamp((row or {}).get("mind_focus")),
        "emotion_tone": (row or {}).get("emotion_tone"),
        "next_peak": (row or {}).get("next_peak"),
        "next_lull": (row or {}).get("next_lull"),
    }


async def _fetch_emotional_state(person_id: str) -> Dict[str, Any]:
    pm = await q(
        """
        SELECT emotion, short_term, emotion_state, data
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    pm = pm or {}
    # Schema guard: fall back to data blob if present
    if pm and isinstance(pm.get("data"), dict):
        blob = pm["data"]
        pm.setdefault("emotion_state", blob.get("emotion_state"))
        pm.setdefault("short_term", blob.get("short_term"))
        pm.setdefault("emotion", blob.get("emotion"))
    short_term = _ensure_dict(pm.get("short_term"))
    emotion_state = _ensure_dict(pm.get("emotion_state"))
    return {
        "dominant": pm.get("emotion") or emotion_state.get("dominant"),
        "volatility": short_term.get("emotion_volatility") or emotion_state.get("volatility"),
        "mood_curve": short_term.get("mood_curve") or emotion_state.get("mood_curve") or [],
        "sentiment_trend": short_term.get("sentiment_trend") or emotion_state.get("sentiment_trend"),
        "self_reported": short_term.get("self_reported_feeling") or emotion_state.get("self_reported"),
        "fragility": short_term.get("emotional_fragility") or emotion_state.get("fragility"),
    }


async def _fetch_identity_state(person_id: str) -> Dict[str, Any]:
    values = await q(
        """
        SELECT value_name, confidence
        FROM soul_values
        WHERE person_id = $1
        ORDER BY confidence DESC NULLS LAST
        LIMIT 5
        """,
        person_id,
    )
    purpose = await q(
        """
        SELECT theme, description, momentum
        FROM purpose_themes
        WHERE person_id = $1
        ORDER BY momentum DESC NULLS LAST, created_at DESC
        LIMIT 3
        """,
        person_id,
    )
    arc = await q(
        """
        SELECT label, summary
        FROM identity_evolution_events
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    persona = await q(
        """
        SELECT current_mode, drift_score
        FROM persona_evolution
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    # Schema guard: persona_modes fallback
    if not persona:
        persona_mode = await q(
            """
            SELECT mode_name
            FROM persona_modes
            WHERE person_id = $1
            ORDER BY last_activated DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )
        if persona_mode:
            persona = {"current_mode": persona_mode.get("mode_name"), "drift_score": 0.0}
    alignment = 1.0 - _clamp((persona or {}).get("drift_score"))
    return {
        "values": values or [],
        "purpose": purpose or [],
        "identity_arcs": arc or {},
        "intention_alignment": alignment,
        "mode": (persona or {}).get("current_mode"),
    }


async def _fetch_relationship_state(person_id: str) -> Dict[str, Any]:
    try:
        row = await q(
            """
            SELECT trust_score, attunement_score, emotional_safety, closeness_stage, updated_at
            FROM relationship_state
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
    except Exception:
        row = None
    return row or {}


async def _fetch_environment_state(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT weather, calendar_blocks, day_cycle, weekend_flag, holiday_flag, travel_flag, environment_tags, updated_at
        FROM environment_context
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    env = row or {}
    env["weather"] = _ensure_dict(env.get("weather")) if env.get("weather") else env.get("weather")
    env["calendar_blocks"] = _ensure_list(env.get("calendar_blocks"))
    env["environment_tags"] = _ensure_list(env.get("environment_tags"))
    return env


async def _fetch_habits_state(person_id: str) -> Dict[str, Any]:
    habits = await q(
        """
        SELECT label, streak_count, micro_progress, confidence, active, last_logged
        FROM growth_habits
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 5
        """,
        person_id,
    )
    motivation = max((_clamp(h.get("confidence")) for h in habits), default=0.5) if habits else 0.5
    return {
        "top_habits": habits or [],
        "consistency": [h.get("streak_count") for h in habits] if habits else [],
        "motivation": motivation,
    }


async def _fetch_focus_state(person_id: str) -> Dict[str, Any]:
    try:
        row = await q(
            """
            SELECT id, mode, completion_score, actual_duration, session_quality, status, end_time, start_time
            FROM focus_sessions
            WHERE person_id = $1
            ORDER BY COALESCE(end_time, start_time) DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )
    except Exception:
        row = None
    if not row:
        return {}
    quality = _ensure_dict(row.get("session_quality"))
    return {
        "last_session_id": str(row.get("id")) if row.get("id") else None,
        "status": row.get("status"),
        "mode": row.get("mode"),
        "outcome": row.get("completion_score"),
        "flow_depth": quality.get("flow_depth"),
        "distraction_pattern": quality.get("distractions"),
        "actual_duration": row.get("actual_duration"),
        "ended_at": row.get("end_time") or row.get("start_time"),
    }


async def _fetch_life_chapter(person_id: str) -> Dict[str, Any]:
    season = await q(
        """
        SELECT season, hints, updated_at
        FROM narrative_seasons
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if season:
        hints = _ensure_dict(season.get("hints"))
        return {
            "chapter": season.get("season"),
            "tone": hints.get("tone"),
            "theme": hints.get("theme"),
            "updated_at": season.get("updated_at"),
        }
    arc = await q(
        """
        SELECT arc_name, sentiment, tags, created_at
        FROM life_arcs
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    if arc:
        return {
            "chapter": arc.get("arc_name"),
            "tone": arc.get("sentiment"),
            "theme": arc.get("tags"),
            "updated_at": arc.get("created_at"),
        }
    return {}


async def _fetch_working_memory(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT short_term
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    return _ensure_dict((row or {}).get("short_term"))


async def _fetch_friction_points(person_id: str) -> List[Dict[str, Any]]:
    events = await q(
        """
        SELECT task_label, delta, payload, created_at
        FROM growth_task_confidence_events
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 5
        """,
        person_id,
    )
    return [
        {
            "task": e.get("task_label"),
            "delta": e.get("delta"),
            "hint": (e.get("payload") or {}).get("reason"),
            "ts": e.get("created_at"),
        }
        for e in events
    ]


async def _derive_top_priorities(person_id: str, fallback_goals: List[Any]) -> List[Dict[str, Any]]:
    try:
        planned = await q(
            """
            SELECT COALESCE(label, title, 'task') AS title,
                   priority,
                   status,
                   horizon,
                   due_ts
            FROM planned_items
            WHERE person_id = $1
              AND (status IS NULL OR status IN ('pending', 'in_progress'))
            ORDER BY priority ASC NULLS LAST, created_at DESC
            LIMIT 3
            """,
            person_id,
        )
        if planned:
            return planned
    except Exception:
        # Fallback if planned_items shape differs or is absent.
        pass
    return fallback_goals[:3] if fallback_goals else []


async def compute_brain_state(person_id: str) -> Dict[str, Any]:
    (
        goals_state,
        rhythm_state,
        emotional_state,
        identity_state,
        relationship_state,
        environment_state,
        habits_state,
        focus_state,
        life_chapter,
        working_memory,
        friction_points,
    ) = await asyncio.gather(
        _fetch_planner_state(person_id),
        _fetch_rhythm_state(person_id),
        _fetch_emotional_state(person_id),
        _fetch_identity_state(person_id),
        _fetch_relationship_state(person_id),
        _fetch_environment_state(person_id),
        _fetch_habits_state(person_id),
        _fetch_focus_state(person_id),
        _fetch_life_chapter(person_id),
        _fetch_working_memory(person_id),
        _fetch_friction_points(person_id),
    )
    top_priorities = await _derive_top_priorities(person_id, goals_state.get("active_goals", []))

    return {
        "person_id": person_id,
        "goals_state": goals_state,
        "rhythm_state": rhythm_state,
        "emotional_state": emotional_state,
        "identity_state": identity_state,
        "relationship_state": relationship_state,
        "environment_state": environment_state,
        "habits_state": habits_state,
        "focus_state": focus_state,
        "friction_points": friction_points,
        "top_priorities": top_priorities,
        "life_chapter": life_chapter,
        "working_memory": working_memory,
        "last_updated": datetime.datetime.utcnow().isoformat(),
    }


async def _persist_brain(person_id: str, brain: Dict[str, Any]) -> None:
    sanitized = _sanitize(brain)
    goals_json = json.dumps(sanitized.get("goals_state", {}), ensure_ascii=False)
    rhythm_json = json.dumps(sanitized.get("rhythm_state", {}), ensure_ascii=False)
    emotional_json = json.dumps(sanitized.get("emotional_state", {}), ensure_ascii=False)
    identity_json = json.dumps(sanitized.get("identity_state", {}), ensure_ascii=False)
    relationship_json = json.dumps(sanitized.get("relationship_state", {}), ensure_ascii=False)
    environment_json = json.dumps(sanitized.get("environment_state", {}), ensure_ascii=False)
    habits_json = json.dumps(sanitized.get("habits_state", {}), ensure_ascii=False)
    focus_json = json.dumps(sanitized.get("focus_state", {}), ensure_ascii=False)
    friction_json = json.dumps(sanitized.get("friction_points", []), ensure_ascii=False)
    priorities_json = json.dumps(sanitized.get("top_priorities", []), ensure_ascii=False)
    life_json = json.dumps(sanitized.get("life_chapter", {}), ensure_ascii=False)
    working_json = json.dumps(sanitized.get("working_memory", {}), ensure_ascii=False)
    await dbexec(
        """
        INSERT INTO personal_os_brain (
            person_id, goals_state, rhythm_state, emotional_state, identity_state,
            relationship_state, environment_state, habits_state, focus_state,
            friction_points, top_priorities, life_chapter, working_memory, last_updated
        )
        VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb, $8::jsonb, $9::jsonb, $10::jsonb, $11::jsonb, $12::jsonb, $13::jsonb, NOW())
        ON CONFLICT (person_id) DO UPDATE SET
            goals_state = EXCLUDED.goals_state,
            rhythm_state = EXCLUDED.rhythm_state,
            emotional_state = EXCLUDED.emotional_state,
            identity_state = EXCLUDED.identity_state,
            relationship_state = EXCLUDED.relationship_state,
            environment_state = EXCLUDED.environment_state,
            habits_state = EXCLUDED.habits_state,
            focus_state = EXCLUDED.focus_state,
            friction_points = EXCLUDED.friction_points,
            top_priorities = EXCLUDED.top_priorities,
            life_chapter = EXCLUDED.life_chapter,
            working_memory = EXCLUDED.working_memory,
            last_updated = NOW()
        """,
        person_id,
        goals_json,
        rhythm_json,
        emotional_json,
        identity_json,
        relationship_json,
        environment_json,
        habits_json,
        focus_json,
        friction_json,
        priorities_json,
        life_json,
        working_json,
    )


async def refresh_brain(person_id: str, *, refresh_journey: bool = True) -> Dict[str, Any]:
    brain = await compute_brain_state(person_id)
    await _persist_brain(person_id, brain)

    if refresh_journey:
        await asyncio.gather(
            journey_renderer.get_today(person_id, force_refresh=True),
            journey_renderer.get_week(person_id, force_refresh=True),
            journey_renderer.get_month(person_id, force_refresh=True),
            journey_renderer.get_life_chapters(person_id, force_refresh=True),
        )
    return _sanitize(brain)


async def get_brain_state(person_id: str, *, force_refresh: bool = False) -> Dict[str, Any]:
    if force_refresh:
        return await refresh_brain(person_id, refresh_journey=False)

    row = await q(
        """
        SELECT goals_state, rhythm_state, emotional_state, identity_state,
               relationship_state, environment_state, habits_state, focus_state,
               friction_points, top_priorities, life_chapter, working_memory, last_updated
        FROM personal_os_brain
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if row:
        return _sanitize(row)
    return await refresh_brain(person_id, refresh_journey=False)


async def get_brain_summary(person_id: str, *, force_refresh: bool = False) -> Dict[str, Any]:
    brain = await get_brain_state(person_id, force_refresh=force_refresh)
    rhythm = _ensure_dict(brain.get("rhythm_state"))
    emotion = _ensure_dict(brain.get("emotional_state"))
    relationship = _ensure_dict(brain.get("relationship_state"))
    environment = _ensure_dict(brain.get("environment_state"))
    return {
        "person_id": person_id,
        "priorities": (brain.get("top_priorities") or [])[:3],
        "emotion": {
            "dominant": emotion.get("dominant"),
            "trend": emotion.get("sentiment_trend"),
        },
        "energy": rhythm.get("energy_cycle") or rhythm.get("body_energy"),
        "stress": rhythm.get("stress_trend"),
        "relationship": {
            "trust": relationship.get("trust_score"),
            "attunement": relationship.get("attunement_score"),
            "safety": relationship.get("emotional_safety"),
            "stage": relationship.get("closeness_stage"),
        },
        "environment": {
            "day_cycle": environment.get("day_cycle"),
            "travel": environment.get("travel_flag"),
            "weather": environment.get("weather"),
        },
        "life_chapter": brain.get("life_chapter"),
        "updated_at": brain.get("last_updated"),
    }


async def get_brain_priorities(person_id: str, *, force_refresh: bool = False) -> List[Dict[str, Any]]:
    brain = await get_brain_state(person_id, force_refresh=force_refresh)
    priorities = brain.get("top_priorities") or []
    return priorities[:3] if isinstance(priorities, list) else []


__all__ = [
    "compute_brain_state",
    "refresh_brain",
    "get_brain_state",
    "get_brain_summary",
    "get_brain_priorities",
]
