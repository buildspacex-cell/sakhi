from __future__ import annotations

from typing import Any, Dict, Sequence

from sakhi.apps.api.core.llm import call_llm


def compute_fast_decision_graph_frame(
    short_term: Sequence[Dict[str, Any]] | None,
    intents: Sequence[Dict[str, Any]] | None,
    goals: Sequence[Dict[str, Any]] | None,
    tasks: Sequence[Dict[str, Any]] | None,
    soul_state: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Deterministic, turn-time graph summary (<5ms).
    """
    st = short_term or []
    intents = intents or []
    goals = goals or []
    tasks = tasks or []
    soul = soul_state or {}

    values = soul.get("core_values") or []
    shadow = soul.get("shadow") or []
    friction = soul.get("friction") or soul.get("conflicts") or []

    active_nodes = {
        "values": list(values),
        "intents": [i.get("title") or i.get("intent") or str(i) for i in intents][:5],
        "goals": [g.get("title") or str(g) for g in goals][:5],
        "tasks": [t.get("label") or t.get("title") or str(t) for t in tasks][:5],
    }

    # micro links: simple rule-based support/conflict
    micro_links = []
    for g in active_nodes["goals"]:
        if any(v.lower() in g.lower() for v in values):
            micro_links.append({"type": "supports", "from": g, "to": "values"})
        if any(f.lower() in g.lower() for f in friction):
            micro_links.append({"type": "conflicts", "from": g, "to": "friction"})

    friction_points = list(friction)

    # energy path: prefer intents/goals that match values and have fewer friction hits
    scored = []
    for g in active_nodes["goals"]:
        score = 1
        score += sum(1 for v in values if v.lower() in g.lower())
        score -= sum(1 for f in friction if f.lower() in g.lower())
        scored.append((score, g))
    scored.sort(reverse=True)
    energy_path = [g for _, g in scored[:3]]

    return {
        "active_nodes": active_nodes,
        "micro_links": micro_links,
        "friction_points": friction_points,
        "energy_path": energy_path,
    }


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
    return {"graph_metadata": str(result)}
