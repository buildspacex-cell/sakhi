from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q, exec as dbexec


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify_time_horizon(task: str, triage: Dict[str, Any] | None = None, sentiment: Dict[str, Any] | None = None) -> str:
    t = _normalize(task)
    if any(k in t for k in ["today", "tonight", "now"]):
        return "today"
    if "tomorrow" in t or "this week" in t:
        return "week"
    if "next month" in t or "this month" in t:
        return "month"
    if "quarter" in t or "q" in t:
        return "quarter"
    if "year" in t or "long term" in t or "long-term" in t:
        return "year"
    # fallback to sentiment/intent urgency
    intent = ""
    if triage and isinstance(triage, dict):
        intent = (triage.get("intent") or triage.get("intent_type") or "").lower()
    if intent in {"task_intent", "plan_intent"}:
        return "week"
    return "week"


def compute_energy_cost(task_text: str, emotion_state: Dict[str, Any] | None = None) -> float:
    base = 0.5
    t = _normalize(task_text)
    if any(k in t for k in ["deep", "write", "research", "analysis"]):
        base += 0.2
    if emotion_state and isinstance(emotion_state, dict):
        tone = (emotion_state.get("summary") or "").lower()
        if "tired" in tone or "low" in tone:
            base += 0.1
    return min(1.0, max(0.1, base))


def compute_auto_priority(horizon: str, energy_cost: float, emotion_state: Dict[str, Any] | None = None) -> float:
    score = 0.5
    if horizon == "today":
        score += 0.2
    if energy_cost <= 0.5:
        score += 0.1
    if emotion_state and isinstance(emotion_state, dict):
        tone = (emotion_state.get("summary") or "").lower()
        if "stressed" in tone or "anxious" in tone:
            score -= 0.05
    return round(max(0.1, min(1.0, score)), 2)


async def _find_anchor_goal(person_id: str, normalized: str) -> str | None:
    try:
        row = await q(
            """
            SELECT id FROM planner_goals
            WHERE person_id = $1 AND lower(title) LIKE '%' || $2 || '%'
            ORDER BY priority DESC
            LIMIT 1
            """,
            person_id,
            normalized.split(" ")[0],
            one=True,
        )
        if row:
            return row["id"]
    except Exception:
        return None
    return None


async def generate_structure(person_id: str, task_text: str, triage: Dict[str, Any] | None, emotion_state: Dict[str, Any] | None) -> Tuple[List[Dict[str, Any]], str]:
    normalized = _normalize(task_text)
    content_hash = _hash(normalized)
    horizon = classify_time_horizon(task_text, triage=triage)
    energy_cost = compute_energy_cost(task_text, emotion_state)
    priority = compute_auto_priority(horizon, energy_cost, emotion_state)

    anchor_goal_id = await _find_anchor_goal(person_id, normalized)

    # base task definitions
    base_id = str(uuid.uuid4())
    weekly_id = str(uuid.uuid4())
    monthly_id = str(uuid.uuid4())
    anchor_id = str(uuid.uuid4())

    tasks = []

    tasks.append(
        {
            "id": base_id,
            "title": task_text,
            "horizon": "today",
            "parent": weekly_id,
            "anchor_goal_id": anchor_goal_id,
            "priority": priority,
            "energy_cost": energy_cost,
            "canonical_intent": (triage or {}).get("intent"),
            "emotional_fit": (emotion_state or {}).get("summary"),
            "content_hash": content_hash,
        }
    )
    tasks.append(
        {
            "id": weekly_id,
            "title": f"Weekly: {task_text}",
            "horizon": "week",
            "parent": monthly_id,
            "anchor_goal_id": anchor_goal_id,
            "priority": priority - 0.05,
            "energy_cost": energy_cost + 0.05,
            "canonical_intent": (triage or {}).get("intent"),
            "emotional_fit": (emotion_state or {}).get("summary"),
            "content_hash": content_hash,
        }
    )
    tasks.append(
        {
            "id": monthly_id,
            "title": f"Milestone: {task_text}",
            "horizon": "month",
            "parent": anchor_id,
            "anchor_goal_id": anchor_goal_id,
            "priority": priority - 0.1,
            "energy_cost": energy_cost + 0.1,
            "canonical_intent": (triage or {}).get("intent"),
            "emotional_fit": (emotion_state or {}).get("summary"),
            "content_hash": content_hash,
        }
    )
    tasks.append(
        {
            "id": anchor_id,
            "title": f"Anchor: {task_text}",
            "horizon": "year",
            "parent": None,
            "anchor_goal_id": anchor_goal_id,
            "priority": priority - 0.15,
            "energy_cost": energy_cost + 0.15,
            "canonical_intent": (triage or {}).get("intent"),
            "emotional_fit": (emotion_state or {}).get("summary"),
            "content_hash": content_hash,
        }
    )

    return tasks, content_hash


async def _upsert_task(person_id: str, task: Dict[str, Any]) -> None:
    title = task["title"]
    existing = await q(
        "SELECT id FROM tasks WHERE user_id = $1 AND lower(title) = lower($2) LIMIT 1",
        person_id,
        title,
        one=True,
    )
    priority = task.get("priority")
    energy_cost = task.get("energy_cost")
    auto_priority = priority if priority is not None else None
    parent_id = task.get("parent")
    anchor_goal_id = task.get("anchor_goal_id")
    horizon = task.get("horizon")
    canonical_intent = task.get("canonical_intent")
    emotional_fit = task.get("emotional_fit")

    if existing:
        try:
            await dbexec(
                """
                UPDATE tasks
                SET inferred_time_horizon = COALESCE($3, inferred_time_horizon),
                    energy_cost = $4,
                    emotional_fit = $5,
                    auto_priority = $6,
                    parent_task_id = COALESCE($7, parent_task_id),
                    anchor_goal_id = COALESCE($8, anchor_goal_id),
                    canonical_intent = COALESCE($9, canonical_intent)
                WHERE id = $1
                """,
                existing["id"],
                person_id,
                horizon,
                energy_cost,
                emotional_fit,
                auto_priority,
                parent_id,
                anchor_goal_id,
                canonical_intent,
            )
        except Exception:
            pass
    else:
        try:
            await dbexec(
                """
                INSERT INTO tasks (
                    id,
                    user_id,
                    title,
                    status,
                    priority,
                    parent_task_id,
                    inferred_time_horizon,
                    energy_cost,
                    emotional_fit,
                    auto_priority,
                    anchor_goal_id,
                    canonical_intent
                )
                VALUES ($1, $2, $3, 'todo', 0, $4, $5, $6, $7, $8, $9, $10)
                """,
                task["id"],
                person_id,
                title,
                parent_id,
                horizon,
                energy_cost,
                emotional_fit,
                auto_priority,
                anchor_goal_id,
                canonical_intent,
            )
        except Exception:
            pass


async def assign(person_id: str, task_text: str, triage: Dict[str, Any] | None = None, emotion_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    tasks, content_hash = await generate_structure(person_id, task_text, triage, emotion_state)
    for task in tasks:
        await _upsert_task(person_id, task)
    return {"ok": True, "content_hash": content_hash, "created": len(tasks)}


__all__ = [
    "classify_time_horizon",
    "compute_energy_cost",
    "compute_auto_priority",
    "generate_structure",
    "assign",
]
