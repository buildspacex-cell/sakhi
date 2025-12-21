from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert, db_update


async def run_goal_evolver(person_id: str) -> None:
    goals = db_find("goals", {"person_id": person_id, "status": "active"})
    reflections = db_find("reflections", {"user_id": person_id})[:10]
    rhythm = db_find("rhythm_forecasts", {"person_id": person_id})[-1:]
    phase = db_find("life_phases", {"person_id": person_id})[-1:]

    prompt = f"""
You are Sakhi's Goal Evolution Engine.
Review active goals and compare with recent reflections, rhythm, and life phase.

GOALS: {goals}
REFLECTIONS: {reflections}
RHYTHM: {rhythm}
PHASE: {phase}

Identify:
- Goals aligned and progressing
- Goals needing reframing
- New or merged goals
- Evolution score (0–1)

Output JSON list:
[{{"goal_id": "...","revised_title": "...","revised_description": "...","reason": "...","evolution_score": 0.82}}]
""".strip()

    response = await call_llm(messages=[{"role": "user", "content": prompt}])
    payload = response.get("message") if isinstance(response, dict) else response
    try:
        revisions = json.loads(payload or "[]")
    except json.JSONDecodeError:
        revisions = []

    for revision in revisions:
        goal_id = revision.get("goal_id")
        if not goal_id:
            continue
        matching_goal = next((goal for goal in goals if goal.get("id") == goal_id), None)
        if not matching_goal:
            continue

        db_insert(
            "goal_history",
            {
                "goal_id": goal_id,
                "person_id": person_id,
                "previous_title": matching_goal.get("title"),
                "previous_description": matching_goal.get("description"),
                "revised_title": revision.get("revised_title"),
                "revised_description": revision.get("revised_description"),
                "reason": revision.get("reason"),
            },
        )

        db_update(
            "goals",
            {"id": goal_id},
            {
                "title": revision.get("revised_title"),
                "description": revision.get("revised_description"),
                "evolution_score": revision.get("evolution_score", 0.5),
                "last_revised": "now",
            },
        )


__all__ = ["run_goal_evolver"]
