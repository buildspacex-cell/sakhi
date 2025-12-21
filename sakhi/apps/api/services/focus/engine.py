from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
import asyncpg

from fastapi import HTTPException
from redis import Redis
from rq import Queue

from sakhi.apps.api.core.db import dbfetchrow, exec as dbexec, q
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.logic.relationship_engine import update_from_focus
from sakhi.apps.api.services.memory.stm_config import compute_expires_at


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

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_FOCUS_QUEUE = os.getenv("FOCUS_QUEUE", "focus")
_FOCUS_TIMEOUT = int(os.getenv("FOCUS_QUEUE_TIMEOUT", "300"))

_redis_conn: Redis | None = None


def _get_queue() -> Queue:
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = Redis.from_url(_REDIS_URL)
    return Queue(_FOCUS_QUEUE, connection=_redis_conn)


async def _fetch_rhythm_baseline(person_id: str) -> Dict[str, Any]:
    row = await dbfetchrow(
        """
        SELECT body_energy, fatigue_level, stress_level, updated_at
        FROM rhythm_state
        WHERE person_id = $1
        """,
        person_id,
    )
    return row or {}


async def _fetch_emotion_baseline(person_id: str) -> Dict[str, Any]:
    # Allowed sources only: personal_model (emotion) and memory_short_term (record.sentiment/emotion_tags).
    baseline: Dict[str, Any] = {}

    pm: Dict[str, Any] | None = None
    try:
        pm = await dbfetchrow(
            """
            SELECT emotion, short_term_vector
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
        )
    except asyncpg.UndefinedColumnError:
        pm = None

    if pm and pm.get("emotion"):
        baseline["mood"] = pm.get("emotion")

    mst = await dbfetchrow(
        """
        SELECT record
        FROM memory_short_term
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
    )
    if mst and isinstance(mst.get("record"), dict):
        record = mst["record"]
        sentiment = record.get("sentiment") or record.get("mood")
        if sentiment and "mood" not in baseline:
            baseline["mood"] = sentiment
        tags = record.get("emotion_tags")
        if tags:
            baseline["tags"] = tags

    # Normalize to allowed keys
    normalized = {
        "mood": baseline.get("mood", "neutral"),
        "energy": None,
        "stress": None,
        "motivation": None,
        "focus_state": None,
        "tags": baseline.get("tags", []),
    }
    return normalized


async def _fetch_task_snapshot(task_id: Optional[str]) -> Dict[str, Any]:
    if not task_id:
        return {}
    row = await dbfetchrow(
        """
        SELECT id, title, energy, ease, status
        FROM planned_items
        WHERE id = $1
        """,
        task_id,
    )
    return row or {}


async def _record_summary(person_id: str, session_id: str, task_id: Optional[str], duration_minutes: Optional[int], completion_score: Optional[float]) -> None:
    summary = {
        "type": "focus_session_summary",
        "task_id": task_id,
        "duration_minutes": duration_minutes,
        "flow_quality": completion_score if completion_score is not None else 0.5,
        "energy_curve": [],
        "wins": ["kept momentum"],
        "suggestions": ["start earlier next time"],
        "confidence": completion_score if completion_score is not None else 0.5,
    }

    # STM must stay evidence-only; skip writing focus summaries into STM.

    # Best-effort habit increment on personal_model; ignore if column missing.
    try:
        await dbexec(
            """
            UPDATE personal_model
            SET habits = COALESCE(habits, '{}'::jsonb) || jsonb_build_object(
                'focus_sessions_completed',
                COALESCE((habits->>'focus_sessions_completed')::int, 0) + 1
            ),
            updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
        )
    except Exception:
        pass


async def start_focus_session(person_id: str, task_id: Optional[str], estimated_duration: Optional[int], mode: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    rhythm = await _fetch_rhythm_baseline(person_id)
    emotion = await _fetch_emotion_baseline(person_id)
    task_snapshot = await _fetch_task_snapshot(task_id)
    start_state = _sanitize({"rhythm": rhythm, "emotion": emotion, "task": task_snapshot})

    row = await dbfetchrow(
        """
        INSERT INTO focus_sessions (person_id, task_id, estimated_duration, mode, session_start_state)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id, start_time
        """,
        person_id,
        task_id,
        estimated_duration,
        mode,
        json.dumps(start_state, ensure_ascii=False),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Could not start focus session")

    session_id = row["id"]
    queue = _get_queue()
    queue.enqueue(
        "sakhi.apps.worker.tasks.focus_session.run_focus_tick",
        kwargs={"session_id": session_id},
        job_timeout=_FOCUS_TIMEOUT,
    )

    return {
        "session_id": session_id,
        "start_time": row["start_time"],
        "start_state": start_state,
        "ack": f"Okay, I'm here with you. Let's focus on {task_snapshot.get('title') or 'this session'}.",
    }


async def ping_focus_session(session_id: str, biomarkers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    session = await dbfetchrow(
        "SELECT id FROM focus_sessions WHERE id = $1 AND end_time IS NULL",
        session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Focus session not found or ended")

    await dbexec(
        """
        INSERT INTO focus_events (session_id, event_type, content)
        VALUES ($1, 'ping', $2::jsonb)
        """,
        session_id,
        json.dumps(biomarkers or {}, ensure_ascii=False),
    )
    return {"status": "ok"}


async def end_focus_session(session_id: str, completion_score: Optional[float], session_quality: Optional[Dict[str, Any]], early_end: bool) -> Dict[str, Any]:
    session = await dbfetchrow(
        """
        SELECT start_time, end_time, person_id, task_id
        FROM focus_sessions
        WHERE id = $1
        """,
        session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Focus session not found")

    if session.get("end_time"):
        return {"status": "ok", "session_id": session_id}

    now = datetime.now(timezone.utc)
    start_time = session.get("start_time")
    actual_minutes = None
    if start_time:
        actual_minutes = int((now - start_time).total_seconds() // 60)

    await dbexec(
        """
        UPDATE focus_sessions
        SET end_time = $2,
            actual_duration = COALESCE($3, actual_duration),
            completion_score = COALESCE($4, completion_score),
            session_quality = COALESCE($5::jsonb, session_quality),
            status = 'ended'
        WHERE id = $1
        """,
        session_id,
        now,
        actual_minutes,
        completion_score,
        json.dumps(session_quality or {"early_end": early_end}, ensure_ascii=False),
    )

    await dbexec(
        """
        INSERT INTO focus_events (session_id, event_type, content)
        VALUES ($1, 'session_end', $2::jsonb)
        """,
        session_id,
        json.dumps({"early_end": early_end, "completion_score": completion_score}, ensure_ascii=False),
    )

    await _record_summary(person_id=session.get("person_id"), session_id=session_id, task_id=session.get("task_id"), duration_minutes=actual_minutes, completion_score=completion_score)
    try:
        await update_from_focus(session.get("person_id"), completion_score)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"[Focus] relationship update failed for {session.get('person_id')}: {exc}")
    return {"status": "ok", "session_id": session_id}


__all__ = ["start_focus_session", "ping_focus_session", "end_focus_session"]
