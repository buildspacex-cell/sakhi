from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q


def _energy_profile(score: float) -> str:
    if score < -0.3:
        return "low"
    if score < 0.3:
        return "medium"
    return "high"


def _focus_profile(mind_score: float) -> str:
    if mind_score > 2:
        return "overloaded"
    if mind_score == 0:
        return "clear"
    return "scattered"


def _normalize_energy_cost(val: float | None) -> float:
    if val is None:
        return 0.5
    return max(0.0, min(1.0, float(val)))


def _parse_json(value: Any, default: Any) -> Any:
    """Normalize a DB value that may be a string-encoded JSON or already parsed."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if parsed is not None else default
        except Exception:
            return default
    return default


async def compute_alignment_map(person_id: str) -> Dict[str, Any]:
    # wellness state
    wellness_row = await q(
        "SELECT body, mind, emotion, energy FROM wellness_state_cache WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    body_score = _parse_json(wellness_row.get("body"), {}).get("score", 0)
    mind_score = _parse_json(wellness_row.get("mind"), {}).get("score", 0)
    emotion_score = _parse_json(wellness_row.get("emotion"), {}).get("score", 0)
    energy_score = _parse_json(wellness_row.get("energy"), {}).get("score", 0)

    # emotion state — read the direct column, not a JSON path inside long_term
    emotion_state_row = await q(
        "SELECT emotion_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    emotion_state = _parse_json(emotion_state_row.get("emotion_state"), {})
    mode = emotion_state.get("mode") or ""
    drift = float(emotion_state.get("drift") or 0)

    # intents
    intents = await q(
        """
        SELECT intent_name, strength, emotional_alignment, trend
        FROM intent_evolution
        WHERE person_id = $1
        """,
        person_id,
    ) or []

    # tasks
    tasks = await q(
        """
        SELECT id, title, energy_cost, auto_priority, anchor_goal_id
        FROM tasks
        WHERE user_id = $1 AND (inferred_time_horizon IS NULL OR inferred_time_horizon = 'today')
        """,
        person_id,
    ) or []

    energy_profile = _energy_profile(energy_score)
    focus_profile = _focus_profile(mind_score)

    recommended: List[Dict[str, Any]] = []
    avoid: List[Dict[str, Any]] = []
    THRESH = 0.4
    intent_strength_map = {i["intent_name"]: float(i.get("strength") or 0) for i in intents if i.get("intent_name")}
    intent_align_map = {i["intent_name"]: float(i.get("emotional_alignment") or 0) for i in intents if i.get("intent_name")}

    for task in tasks:
        priority = float(task.get("auto_priority") or 0)
        energy_cost = _normalize_energy_cost(task.get("energy_cost"))
        title = (task.get("title") or "").lower()
        matched_intent_strength = 0.0
        matched_alignment = 0.0
        for intent_name, strength in intent_strength_map.items():
            if intent_name and intent_name in title:
                matched_intent_strength = max(matched_intent_strength, strength)
                matched_alignment = max(matched_alignment, intent_align_map.get(intent_name, 0))
        urgency = priority
        score = (matched_intent_strength * 0.4) + (matched_alignment * 0.2) + ((1 - energy_cost) * 0.2) + (urgency * 0.2)
        payload = {
            "id": task.get("id"),
            "title": task.get("title"),
            "score": round(score, 3),
            "energy_cost": energy_cost,
        }
        if score > THRESH and energy_profile != "low":
            recommended.append(payload)
        else:
            avoid.append(payload)

    recommended = sorted(recommended, key=lambda x: x["score"], reverse=True)

    intent_alignment = []
    for intent in intents:
        if float(intent.get("strength") or 0) > 0.5:
            intent_alignment.append(
                {
                    "intent": intent.get("intent_name"),
                    "hint": "nudge next step",
                    "strength": float(intent.get("strength") or 0),
                }
            )

    emotional_safeguards = []
    if mode in {"falling"} or energy_profile == "low":
        emotional_safeguards.append("delay difficult tasks")
        emotional_safeguards.append("light breathing first")
    self_care = []
    if body_score > 2:
        self_care.append("rest or short walk")
    if emotion_score < -0.5:
        self_care.append("grounding breath cycle")

    return {
        "recommended_actions": recommended,
        "avoid_actions": avoid,
        "energy_profile": energy_profile,
        "focus_profile": focus_profile,
        "intent_alignment": intent_alignment,
        "emotional_safeguards": emotional_safeguards,
        "self_care_suggestions": self_care,
    }


__all__ = ["compute_alignment_map"]
