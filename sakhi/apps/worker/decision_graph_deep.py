from __future__ import annotations

from typing import Any, Dict
import logging

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.intelligence.decision_graph_engine import compute_deep_decision_graph
logger = logging.getLogger(__name__)


def normalize_episodic_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "soul": row.get("soul") or {},
        "soul_conflict": row.get("soul_conflict") or {},
        "soul_friction": row.get("soul_friction") or {},
        "emotional_state": row.get("emotional_state")
        or {"tone": "neutral", "valence": 0.0, "activation": 0.5, "stability": 0.5},
        "rhythm_state": row.get("rhythm_state") or {},
        "ts": row.get("ts"),
    }


async def run_decision_graph_deep(person_id: str) -> Dict[str, Any]:
    episodic_rows_raw = await q(
        """
        SELECT soul, emotional_state, rhythm_state, ts
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY ts DESC
        LIMIT 50
        """,
        person_id,
    )
    episodic = [normalize_episodic_row(r) for r in (episodic_rows_raw or [])]
    pm_row = await q(
        "SELECT soul_state, goals_state, rhythm_state, emotion_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    soul_state = (pm_row or {}).get("soul_state") or {}
    goals_state = (pm_row or {}).get("goals_state") or {}
    # tasks placeholder: planner_tasks not modeled here; use empty list
    task_state: list[Dict[str, Any]] = []

    logger.info(
        "[decision_graph_deep] episodic_inputs",
        extra={
            "person_id": person_id,
            "episodic_count": len(episodic),
            "with_conflict": sum(bool(r.get("soul_conflict")) for r in episodic),
            "with_friction": sum(bool(r.get("soul_friction")) for r in episodic),
        },
    )

    deep = await compute_deep_decision_graph(person_id, episodic or [], soul_state, goals_state, task_state)
    await dbexec("UPDATE personal_model SET internal_decision_graph = $2 WHERE person_id = $1", person_id, deep)
    return deep
