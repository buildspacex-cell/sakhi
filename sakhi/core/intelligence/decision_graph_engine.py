from __future__ import annotations

from typing import Any, Dict, Sequence

from kala.decision.scoring import compute_fast_decision_frame  # noqa: F401
from sakhi.apps.api.core.llm import call_llm

# Re-export under original name for backwards compatibility
compute_fast_decision_graph_frame = compute_fast_decision_frame


async def compute_deep_decision_graph(
    person_id: str,
    episodic: Sequence[Dict[str, Any]],
    soul_state: Dict[str, Any],
    goals_state: Dict[str, Any],
    task_state: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Worker-time deep graph (LLM allowed).
    """
    prompt = (
        "You are Sakhi's Internal Decision Graph engine. Given soul_state, goals_state, tasks, and episodic signals, "
        "return JSON with nodes (soul_values, identity_drivers, intents, goals, tasks, actions), edges (supports, conflicts, depends_on, blocks, amplifies), "
        "and graph_metadata (friction_clusters, value_goal_alignment, action_readiness, energy_flow). JSON only."
    )
    payload = {
        "person_id": person_id,
        "soul_state": soul_state or {},
        "goals_state": goals_state or {},
        "tasks": task_state or [],
        "episodic": episodic or [],
    }
    result = await call_llm(messages=[{"role": "user", "content": f"{prompt}\n\nPAYLOAD:\n{payload}"}])
    if isinstance(result, dict):
        return result
    # Handle string response with potential markdown blocks
    from sakhi.apps.api.core.llm import extract_json_from_llm_response
    parsed = extract_json_from_llm_response(str(result))
    if isinstance(parsed, dict) and "_raw" not in parsed:
        return parsed
    return {"graph_metadata": str(result)}
