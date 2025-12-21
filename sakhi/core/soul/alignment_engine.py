from __future__ import annotations

import json
from typing import Any, Dict


def compute_alignment(short_term: Any, soul_state: Dict[str, Any] | None, goals_state: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Deterministic alignment computation (no LLM).
    Inputs:
      short_term: recent context (unused beyond placeholder)
      soul_state: Build 57/58/59 soul fields
      goals_state: planner goals if available
    Outputs:
      - alignment_score 0-1
      - conflict_zones []
      - action_suggestions []
    """
    soul = soul_state or {}
    if isinstance(soul, str):
        try:
            soul = json.loads(soul)
        except Exception:
            soul = {}
    if not isinstance(soul, dict):
        soul = {}

    goals = goals_state or {}
    if isinstance(goals, str):
        try:
            goals = json.loads(goals)
        except Exception:
            goals = {}
    if not isinstance(goals, dict):
        goals = {}
    values = soul.get("core_values") or []
    aversions = set(soul.get("aversions") or [])
    friction = soul.get("friction") or []
    conflicts = soul.get("conflicts") or []
    goals_list = goals.get("active_goals") or []

    # value vs goals overlap
    overlap = 0
    for g in goals_list:
        title = str(g.get("title") or "").lower()
        if any(v.lower() in title for v in values):
            overlap += 1
    goal_count = len(goals_list) or 1
    value_goal_alignment = overlap / goal_count

    friction_penalty = min(0.5, len(friction) * 0.05)
    conflict_penalty = min(0.5, len(conflicts) * 0.05)
    alignment_score = max(0.0, min(1.0, value_goal_alignment - friction_penalty - conflict_penalty))

    conflict_zones = []
    for f in friction:
        if isinstance(f, str):
            conflict_zones.append(f)
    for c in conflicts:
        if isinstance(c, str) and c not in conflict_zones:
            conflict_zones.append(c)
    for a in aversions:
        if a not in conflict_zones:
            conflict_zones.append(a)

    action_suggestions = []
    if alignment_score < 0.5 and values:
        action_suggestions.append(f"Pick one goal that supports {values[0]} this week.")
    if friction:
        action_suggestions.append("Reduce one friction source with a small boundary.")
    if not action_suggestions:
        action_suggestions.append("Maintain current alignment; reflect weekly.")

    return {
        "alignment_score": alignment_score,
        "conflict_zones": conflict_zones,
        "action_suggestions": action_suggestions,
    }
