from __future__ import annotations

from fastapi import APIRouter

from sakhi.apps.api.core.db import q
from sakhi.core.intelligence.decision_graph_engine import compute_fast_decision_graph_frame

router = APIRouter(prefix="/decision_graph", tags=["decision_graph"])


@router.get("/{person_id}")
async def get_decision_graph(person_id: str):
    pm = await q(
        "SELECT soul_state, goals_state, internal_decision_graph FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    soul = (pm or {}).get("soul_state") or {}
    goals = (pm or {}).get("goals_state") or {}
    fast = compute_fast_decision_graph_frame([], [], goals.get("active_goals") or [], [], soul)
    deep = (pm or {}).get("internal_decision_graph") or {}
    return {"fast": fast, "deep": deep}
