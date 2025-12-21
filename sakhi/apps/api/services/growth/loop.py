from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch


async def _fetch_habit(person_id: str, label: str) -> Dict[str, Any] | None:
    return await dbfetch(
        """
        SELECT *
        FROM growth_habits
        WHERE person_id = $1 AND label = $2
        """,
        person_id,
        label,
        one=True,
    )


async def _ensure_habit(person_id: str, label: str, *, cadence: Mapping[str, Any] | None = None, intent_source: str | None = None) -> Dict[str, Any]:
    habit = await _fetch_habit(person_id, label)
    if habit:
        return habit
    habit_id = str(uuid.uuid4())
    await dbexec(
        """
        INSERT INTO growth_habits (id, person_id, label, cadence, intent_source)
        VALUES ($1, $2, $3, $4::jsonb, $5)
        """,
        habit_id,
        person_id,
        label,
        json.dumps(cadence or {}, ensure_ascii=False),
        intent_source,
    )
    return await _fetch_habit(person_id, label) or {"id": habit_id, "label": label, "streak_count": 0, "confidence": 0.5, "micro_progress": 0.0}


async def record_habit_event(
    person_id: str,
    *,
    label: str,
    micro_score: float = 0.2,
    mood: str | None = None,
    note: str | None = None,
    cadence: Mapping[str, Any] | None = None,
    intent_source: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> None:
    habit = await _ensure_habit(person_id, label, cadence=cadence, intent_source=intent_source)
    habit_id = habit["id"]
    now = datetime.now(timezone.utc)
    last_logged = habit.get("last_logged")
    streak = int(habit.get("streak_count") or 0)
    if isinstance(last_logged, datetime):
        last_date = last_logged.date()
    elif isinstance(last_logged, str):
        try:
            last_date = datetime.fromisoformat(last_logged).date()
        except ValueError:
            last_date = None
    else:
        last_date = None
    today = now.date()
    if last_date == today:
        new_streak = streak
    elif last_date == today - timedelta(days=1):
        new_streak = streak + 1
    else:
        new_streak = 1
    micro_val = float(micro_score)
    prev_conf = float(habit.get("confidence") or 0.5)
    new_conf = max(0.0, min(1.0, prev_conf + micro_val / 2))
    prev_micro = float(habit.get("micro_progress") or 0.0)
    new_micro = max(0.0, min(1.0, prev_micro + micro_val))

    await dbexec(
        """
        INSERT INTO growth_habit_logs (habit_id, person_id, micro_score, mood, note, payload)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        """,
        habit_id,
        person_id,
        micro_score,
        mood,
        note,
        json.dumps(payload or {}, ensure_ascii=False),
    )

    await dbexec(
        """
        UPDATE growth_habits
        SET streak_count = $2,
            micro_progress = $3,
            confidence = $4,
            last_logged = NOW(),
            updated_at = NOW()
        WHERE id = $1
        """,
        habit_id,
        new_streak,
        new_micro,
        new_conf,
    )


async def record_daily_check_in(
    person_id: str,
    *,
    energy: float | None = None,
    mood: str | None = None,
    reflection: str | None = None,
    plan_adjustment: Mapping[str, Any] | None = None,
    checkin_date: datetime | None = None,
) -> Dict[str, Any]:
    check_date = (checkin_date or datetime.utcnow()).date()
    row = await dbfetch(
        """
        INSERT INTO growth_daily_checkins (person_id, checkin_date, energy, mood, reflection, plan_adjustment)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        ON CONFLICT (person_id, checkin_date)
        DO UPDATE SET energy = EXCLUDED.energy,
                      mood = EXCLUDED.mood,
                      reflection = EXCLUDED.reflection,
                      plan_adjustment = EXCLUDED.plan_adjustment,
                      created_at = NOW()
        RETURNING *
        """,
        person_id,
        check_date,
        energy,
        mood,
        reflection,
        json.dumps(plan_adjustment or {}, ensure_ascii=False),
        one=True,
    )
    return row or {}


async def record_task_confidence_event(
    person_id: str,
    *,
    task_id: str | None,
    label: str | None,
    confidence_before: float | None,
    confidence_after: float | None,
    source: str,
    payload: Mapping[str, Any] | None = None,
) -> None:
    before = confidence_before if confidence_before is not None else confidence_after
    after = confidence_after if confidence_after is not None else before
    delta = None
    if before is not None and after is not None:
        delta = after - before
    await dbexec(
        """
        INSERT INTO growth_task_confidence_events (person_id, task_id, task_label, confidence_before, confidence_after, delta, source, payload)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        """,
        person_id,
        task_id,
        label,
        before,
        after,
        delta,
        source,
        json.dumps(payload or {}, ensure_ascii=False),
    )


def _normalize_cadence(recurrence: Any, horizon: str | None) -> Dict[str, Any]:
    if recurrence is None:
        if horizon:
            return {"kind": horizon}
        return {}
    if isinstance(recurrence, dict):
        return recurrence
    return {"kind": str(recurrence)}


def _looks_like_habit(task: Mapping[str, Any]) -> bool:
    recurrence = task.get("recurrence")
    if recurrence:
        return True
    label = str(task.get("label") or task.get("title") or "").lower()
    details = str(task.get("details") or "").lower()
    blob = f"{label} {details}"
    if "habit" in blob or "routine" in blob:
        return True
    if "daily" in blob or "every day" in blob:
        return True
    horizon = str(task.get("horizon") or "").lower()
    if horizon == "today" and ("morning" in blob or "evening" in blob):
        return True
    return False


async def sync_growth_from_planner(person_id: str, planner_payload: Mapping[str, Any] | None) -> None:
    if not planner_payload:
        return
    tasks = []
    if isinstance(planner_payload, Mapping):
        tasks = planner_payload.get("tasks") or planner_payload.get("plan_graph", {}).get("tasks") or []
        if not tasks and isinstance(planner_payload.get("suggestions"), Sequence):
            tasks = planner_payload.get("suggestions")
    if not isinstance(tasks, Sequence):
        tasks = []
    for task in tasks:
        if not isinstance(task, Mapping):
            continue
        label = task.get("label") or task.get("title")
        if not label:
            continue
        is_habit = task.get("kind") in {"habit", "routine"} or task.get("cadence") or task.get("habit")
        cadence_payload = _normalize_cadence(task.get("recurrence") or task.get("cadence"), task.get("horizon"))
        is_habit = _looks_like_habit(task) or bool(cadence_payload)
        if is_habit:
            horizon = str(task.get("horizon") or "").lower()
            base_micro = 0.2
            if horizon in {"today", "week"}:
                base_micro = 0.25
            elif horizon == "month":
                base_micro = 0.15
            await record_habit_event(
                person_id,
                label=label or "Untitled habit",
                micro_score=float(task.get("micro_score") or base_micro),
                cadence=cadence_payload,
                intent_source="planner",
                note=task.get("details"),
                payload={"task": task},
            )
        confidence = task.get("confidence")
        if confidence is not None:
            await record_task_confidence_event(
                person_id,
                task_id=task.get("id"),
                label=label,
                confidence_before=task.get("confidence_before"),
                confidence_after=confidence,
                source="planner",
                payload={"task": task},
            )


async def summarize_growth(person_id: str) -> Dict[str, Any]:
    habits = await dbfetch(
        """
        SELECT id, label, streak_count, micro_progress, confidence, last_logged, cadence, intent_source
        FROM growth_habits
        WHERE person_id = $1
        ORDER BY updated_at DESC
        """,
        person_id,
    )
    checkins = await dbfetch(
        """
        SELECT checkin_date, energy, mood, reflection, plan_adjustment, created_at
        FROM growth_daily_checkins
        WHERE person_id = $1
        ORDER BY checkin_date DESC
        LIMIT 7
        """,
        person_id,
    )
    confidence_events = await dbfetch(
        """
        SELECT task_id, task_label, confidence_before, confidence_after, delta, source, created_at
        FROM growth_task_confidence_events
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        person_id,
    )
    return {
        "person_id": person_id,
        "habits": habits,
        "checkins": checkins,
        "confidence_events": confidence_events,
    }


__all__ = [
    "record_habit_event",
    "record_daily_check_in",
    "record_task_confidence_event",
    "sync_growth_from_planner",
    "summarize_growth",
]
