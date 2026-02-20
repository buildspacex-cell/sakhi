"""Fast deterministic decision graph frame — <5ms, no LLM, no I/O."""

from __future__ import annotations

from typing import Any, Sequence


def compute_fast_decision_frame(
    short_term: Sequence[dict[str, Any]] | None = None,
    intents: Sequence[dict[str, Any]] | None = None,
    goals: Sequence[dict[str, Any]] | None = None,
    tasks: Sequence[dict[str, Any]] | None = None,
    soul_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic, turn-time graph summary (<5ms).

    Builds active nodes, discovers micro-links (support/conflict),
    identifies friction points, and computes an energy path ranking.
    """
    st = short_term or []  # noqa: F841
    intents_list = intents or []
    goals_list = goals or []
    tasks_list = tasks or []
    soul = soul_state or {}

    values = soul.get("core_values") or []
    shadow = soul.get("shadow") or []  # noqa: F841
    friction = soul.get("friction") or soul.get("conflicts") or []

    active_nodes = {
        "values": list(values),
        "intents": [
            i.get("title") or i.get("intent") or str(i) for i in intents_list
        ][:5],
        "goals": [g.get("title") or str(g) for g in goals_list][:5],
        "tasks": [
            t.get("label") or t.get("title") or str(t) for t in tasks_list
        ][:5],
    }

    # Micro links: simple rule-based support/conflict
    micro_links = []
    for g in active_nodes["goals"]:
        if any(v.lower() in g.lower() for v in values):
            micro_links.append({"type": "supports", "from": g, "to": "values"})
        if any(f.lower() in g.lower() for f in friction):
            micro_links.append(
                {"type": "conflicts", "from": g, "to": "friction"}
            )

    friction_points = list(friction)

    # Energy path: prefer goals that match values and have fewer friction hits
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
