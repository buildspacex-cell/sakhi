from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sakhi.apps.api.services.planner.engine import (
    planner_commit,
    planner_summary,
    planner_suggest,
)
from sakhi.apps.api.core.db import q
import datetime

router = APIRouter(prefix="/planner", tags=["planner"])


class PlannerSuggestIn(BaseModel):
    person_id: str
    text: str


@router.post("/suggest")
async def suggest(body: PlannerSuggestIn) -> Dict[str, Any]:
    return await planner_suggest(body.person_id, body.text)


class PlannerCommitIn(BaseModel):
    person_id: str
    goals: List[Dict[str, Any]] = Field(default_factory=list)
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/commit")
async def commit(body: PlannerCommitIn) -> Dict[str, Any]:
    payload = body.dict()
    payload.pop("person_id", None)
    return await planner_commit(body.person_id, payload)


@router.get("/{person_id}/summary")
async def summary(person_id: str) -> Dict[str, Any]:
    return await planner_summary(person_id)


class DailyStackIn(BaseModel):
    person_id: str


@router.post("/daily_stack")
async def daily_stack(body: DailyStackIn) -> Dict[str, Any]:
    """
    Returns a prioritized stack of daily atoms (max 7).
    """
    try:
        rows = await q(
            """
            SELECT id, title, auto_priority, energy_cost, emotional_fit
            FROM tasks
            WHERE user_id = $1 AND (inferred_time_horizon = 'today' OR inferred_time_horizon IS NULL)
            ORDER BY auto_priority DESC NULLS LAST, created_at ASC
            LIMIT 7
            """,
            body.person_id,
        )
    except Exception:
        rows = []
    stack = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "auto_priority": r.get("auto_priority"),
            "energy_cost": r.get("energy_cost"),
            "emotional_fit": r.get("emotional_fit"),
        }
        for r in rows or []
    ]
    return {
        "ts": datetime.datetime.utcnow().isoformat(),
        "items": stack,
        "count": len(stack),
    }


__all__ = ["router"]
