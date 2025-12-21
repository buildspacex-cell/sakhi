from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from sakhi.apps.api.core.db import exec as dbexec


async def update_existing_plans(person_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Commit planner plan graph (goals, milestones, tasks) to DB.
    """

    goals = payload.get("goals", [])
    milestones = payload.get("milestones", [])
    tasks = payload.get("tasks", []) or payload.get("items", [])

    await _upsert_goals(person_id, goals)
    await _upsert_milestones(person_id, milestones)
    await _upsert_tasks(person_id, tasks)
    return {"goals": len(goals), "milestones": len(milestones), "tasks": len(tasks)}


async def _upsert_goals(person_id: str, goals: List[Dict[str, Any]]) -> None:
    for goal in goals:
        await dbexec(
            """
            INSERT INTO planner_goals (id, person_id, title, details, horizon, priority, status, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, 'active'), NOW())
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title,
                details = EXCLUDED.details,
                horizon = EXCLUDED.horizon,
                priority = EXCLUDED.priority,
                status = EXCLUDED.status,
                updated_at = NOW()
            """,
            goal.get("id"),
            person_id,
            goal.get("title") or "Untitled goal",
            goal.get("details") or "",
            goal.get("horizon") or "month",
            int(goal.get("priority") or 1),
            goal.get("status") or "active",
        )


async def _upsert_milestones(person_id: str, milestones: List[Dict[str, Any]]) -> None:
    for milestone in milestones:
        await dbexec(
            """
            INSERT INTO planner_milestones (id, person_id, goal_id, title, details, due_ts, horizon, status, sequence, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, 'week'), COALESCE($8, 'active'), COALESCE($9, 0), NOW())
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title,
                details = EXCLUDED.details,
                due_ts = EXCLUDED.due_ts,
                horizon = EXCLUDED.horizon,
                status = EXCLUDED.status,
                sequence = EXCLUDED.sequence,
                updated_at = NOW()
            """,
            milestone.get("id"),
            person_id,
            milestone.get("goal_id"),
            milestone.get("title") or "Milestone",
            milestone.get("details") or "",
            _parse_ts(milestone.get("due_ts")),
            milestone.get("horizon"),
            milestone.get("status"),
            milestone.get("sequence"),
        )


async def _upsert_tasks(person_id: str, tasks: List[Dict[str, Any]]) -> None:
    for item in tasks:
        task_id = _stringify_uuid(item.get("id"))
        goal_id = _stringify_uuid(item.get("goal_id"))
        milestone_id = _stringify_uuid(item.get("milestone_id"))
        payload_json = json.dumps(_to_serializable(item), ensure_ascii=False)

        await dbexec(
            """
            INSERT INTO planned_items (
                id,
                person_id,
                goal_id,
                milestone_id,
                label,
                due_ts,
                priority,
                status,
                energy,
                ease,
                recurrence,
                horizon,
                origin_id,
                meta,
                payload
            )
            VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, 1), COALESCE($8, 'pending'),
                    $9, $10, $11::jsonb, $12, $13, $14::jsonb, $15::jsonb)
            ON CONFLICT (person_id, origin_id) DO UPDATE
            SET label = EXCLUDED.label,
                due_ts = EXCLUDED.due_ts,
                priority = EXCLUDED.priority,
                status = EXCLUDED.status,
                energy = EXCLUDED.energy,
                ease = EXCLUDED.ease,
                recurrence = EXCLUDED.recurrence,
                horizon = EXCLUDED.horizon,
                meta = EXCLUDED.meta,
                payload = EXCLUDED.payload
            """,
            task_id,
            person_id,
            goal_id,
            milestone_id,
            item.get("label") or "Task",
            _parse_ts(item.get("due_ts")),
            int(item.get("priority") or 1),
            item.get("status") or "pending",
            item.get("energy"),
            item.get("ease"),
            json.dumps(_to_serializable(item.get("recurrence"))) if item.get("recurrence") is not None else None,
            item.get("horizon"),
            item.get("origin_id"),
            json.dumps(_to_serializable(item.get("meta") or {}), ensure_ascii=False),
            payload_json,
        )


def _to_serializable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _to_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_serializable(v) for v in value]
    return value


def _stringify_uuid(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    return value


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed
        except ValueError:
            return None
    return None


__all__ = ["update_existing_plans"]
