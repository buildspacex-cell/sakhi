from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.intelligence.decision_graph_engine import compute_deep_decision_graph


async def run_decision_graph_deep(person_id: str) -> Dict[str, Any]:
    episodic = await q(
        """
        SELECT soul, emotional_state, rhythm_state, ts
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY ts DESC
        LIMIT 50
        """,
        person_id,
    )
    pm_row = await q(
        "SELECT soul_state, goals_state, rhythm_state, emotion_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    soul_state = (pm_row or {}).get("soul_state") or {}
    goals_state = (pm_row or {}).get("goals_state") or {}
    # tasks placeholder: planner_tasks not modeled here; use empty list
    task_state: list[Dict[str, Any]] = []

    deep = await compute_deep_decision_graph(person_id, episodic or [], soul_state, goals_state, task_state)
    await dbexec("UPDATE personal_model SET internal_decision_graph = $2 WHERE person_id = $1", person_id, deep)
    return deep

