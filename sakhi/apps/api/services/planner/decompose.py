from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from uuid import uuid4

HORIZON_KIND_MAP = {
    "today": "today",
    "tomorrow": "today",
    "this_week": "week",
    "this_month": "month",
    "this_quarter": "quarter",
    "unspecified": "month",
}

DEFAULT_DUE_OFFSETS = {
    "today": timedelta(hours=8),
    "week": timedelta(days=3),
    "month": timedelta(days=14),
    "quarter": timedelta(days=45),
}


def build_plan_graph(person_id: str, intents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert ranked planner intents into a goal→milestone→task graph.
    Every intent yields at least one goal, milestone, and task so downstream
    flows can render multi-horizon plans.
    """

    goals: List[Dict[str, Any]] = []
    milestones: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []

    now = datetime.now(timezone.utc)

    for idx, intent in enumerate(intents):
        horizon, due_ts = _select_horizon_and_due(intent, now)
        title = intent.get("title") or intent.get("details") or "Untitled task"
        details = intent.get("details") or ""

        goal_id = intent.get("goal_id") or str(uuid4())
        milestone_id = intent.get("milestone_id") or str(uuid4())
        task_id = intent.get("task_id") or str(uuid4())
        origin_id = _derive_origin_id(person_id, intent, idx)

        goal_payload = {
            "id": goal_id,
            "person_id": person_id,
            "title": title,
            "details": details,
            "horizon": horizon if horizon != "today" else "week",
            "priority": int(intent.get("priority") or 1),
            "status": intent.get("status") or "active",
        }
        goals.append(goal_payload)

        milestone_payload = {
            "id": milestone_id,
            "goal_id": goal_id,
            "person_id": person_id,
            "title": f"{title} milestone",
            "details": details,
            "due_ts": due_ts.isoformat() if due_ts else None,
            "horizon": horizon,
            "status": "active",
            "sequence": idx,
        }
        milestones.append(milestone_payload)

        tasks.append(
            {
                "id": task_id,
                "goal_id": goal_id,
                "milestone_id": milestone_id,
                "label": title,
                "details": details,
                "due_ts": due_ts.isoformat() if due_ts else None,
                "priority": int(intent.get("priority") or 1),
                "energy": intent.get("energy_hint"),
                "ease": _difficulty_to_ease(intent.get("difficulty_hint")),
                "recurrence": intent.get("recurrence"),
                "horizon": horizon,
                "status": "pending",
                "origin_id": origin_id,
                "meta": {
                    "intent_index": idx,
                    "intent_time_window": intent.get("time_window"),
                },
            }
        )

    return {"goals": goals, "milestones": milestones, "tasks": tasks}


def _select_horizon_and_due(intent: Dict[str, Any], now: datetime) -> Tuple[str, datetime]:
    time_window = intent.get("time_window") or {}
    kind = str(time_window.get("kind") or "unspecified").lower()
    horizon = HORIZON_KIND_MAP.get(kind, "month")
    due_ts = now + DEFAULT_DUE_OFFSETS.get(horizon, timedelta(days=14))
    if horizon == "today":
        due_ts = now + timedelta(hours=4)
    return horizon, due_ts


def _derive_origin_id(person_id: str, intent: Dict[str, Any], idx: int) -> str:
    seed = f"{person_id}:{intent.get('title') or ''}:{intent.get('details') or ''}:{idx}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return f"intent:{digest}"


def _difficulty_to_ease(candidate: Any) -> int | None:
    mapping = {
        "very_easy": 1,
        "easy": 2,
        "medium": 3,
        "hard": 4,
        "very_hard": 5,
    }
    if candidate is None:
        return None
    if isinstance(candidate, (int, float)):
        value = int(candidate)
        return max(1, min(5, value))
    key = str(candidate).strip().lower()
    return mapping.get(key)


__all__ = ["build_plan_graph"]
