from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import asyncio

from sakhi.apps.api.core.db import q, exec as dbexec

LOGGER = logging.getLogger(__name__)

NUDGE_TYPES = (
    "flow_continue",
    "flow_dip_refocus",
    "encouragement_soft",
    "micro_break_suggestion",
    "recovery_break_suggestion",
    "calming_moment",
)
NUDGE_BACKOFF_SECONDS = 300  # 5 minutes
NUDGE_MAX_PER_SESSION = 8


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    try:
        from decimal import Decimal

        if isinstance(obj, Decimal):
            return float(obj)
    except Exception:
        pass
    try:
        import datetime

        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
    except Exception:
        pass
    return obj


async def _fetch_session(session_id: str) -> Dict[str, Any] | None:
    rows = await q(
        """
        SELECT id, person_id, task_id, start_time, end_time, mode, estimated_duration, session_quality
        FROM focus_sessions
        WHERE id = $1
        """,
        session_id,
    )
    return rows[0] if rows else None


async def _fetch_rhythm(person_id: str) -> Dict[str, Any]:
    rows = await q(
        """
        SELECT body_energy, fatigue_level, stress_level, updated_at
        FROM rhythm_state
        WHERE person_id = $1
        """,
        person_id,
    )
    return rows[0] if rows else {}


async def _fetch_task(task_id: str | None) -> Dict[str, Any]:
    if not task_id:
        return {}
    rows = await q(
        """
        SELECT id, title, energy, ease, status
        FROM planned_items
        WHERE id = $1
        """,
        task_id,
    )
    return rows[0] if rows else {}


def _pick_event_type(energy: float | None) -> tuple[str, str]:
    # Map into the allowed guardrailed nudge types.
    if energy is None:
        return "encouragement_soft", "Gentle steady focus - you're on track."
    if energy >= 0.7:
        return "flow_continue", "Nice groove - keep going."
    if 0.35 <= energy < 0.7:
        return "flow_dip_refocus", "Tiny reset, one breath, then back in."
    return "micro_break_suggestion", "Tiny pause. One breath. Let's get back to it."


async def _nudge_meta(session_id: str) -> tuple[datetime | None, int]:
    rows = await q(
        """
        SELECT ts
        FROM focus_events
        WHERE session_id = $1 AND event_type = ANY($2)
        ORDER BY ts DESC
        LIMIT 1
        """,
        session_id,
        list(NUDGE_TYPES),
    )
    last_ts = rows[0]["ts"] if rows else None

    count_rows = await q(
        """
        SELECT COUNT(*) AS count
        FROM focus_events
        WHERE session_id = $1 AND event_type = ANY($2)
        """,
        session_id,
        list(NUDGE_TYPES),
    )
    total = 0
    if count_rows:
        total = int(count_rows[0].get("count", 0))
    return last_ts, total


async def _run_focus_tick(session_id: str) -> None:
    session = await _fetch_session(session_id)
    if not session:
        LOGGER.warning("[Focus] session not found %s", session_id)
        return
    if session.get("end_time"):
        LOGGER.info("[Focus] session already ended %s", session_id)
        return

    person_id = session["person_id"]
    rhythm_state = await _fetch_rhythm(person_id)
    task_state = await _fetch_task(session.get("task_id"))

    energy = None
    try:
        raw_energy = rhythm_state.get("body_energy")
        energy = float(raw_energy) if raw_energy is not None else None
    except Exception:
        energy = None

    now = datetime.now(timezone.utc)

    # Respect nudge guardrails: 1 per 5 minutes, max 8 per session.
    last_ts, total_nudges = await _nudge_meta(session_id)
    if total_nudges >= NUDGE_MAX_PER_SESSION:
        LOGGER.info("[Focus] nudge cap reached for session=%s", session_id)
    elif last_ts and (now - last_ts).total_seconds() < NUDGE_BACKOFF_SECONDS:
        LOGGER.info("[Focus] backoff active for session=%s", session_id)
    else:
        event_type, prompt = _pick_event_type(energy)
        await dbexec(
            """
            INSERT INTO focus_events (session_id, ts, event_type, content, rhythm_state, task_state, emotion_state)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, '{}'::jsonb)
            """,
            session_id,
            now,
            event_type,
            json.dumps(_sanitize({"nudge": prompt}), ensure_ascii=False),
            json.dumps(_sanitize(rhythm_state or {}), ensure_ascii=False),
            json.dumps(_sanitize(task_state or {}), ensure_ascii=False),
        )
        LOGGER.info("[Focus] tick recorded for session=%s event=%s", session_id, event_type)

    # Update actual duration snapshot
    try:
        start = session.get("start_time")
        if start:
            actual_minutes = int((now - start).total_seconds() // 60)
            await dbexec(
                "UPDATE focus_sessions SET actual_duration = $2 WHERE id = $1",
                session_id,
                actual_minutes,
            )
    except Exception as exc:
        LOGGER.warning("[Focus] failed to update duration for %s: %s", session_id, exc)


def run_focus_tick(session_id: str) -> None:
    asyncio.run(_run_focus_tick(session_id))


__all__ = ["run_focus_tick"]
