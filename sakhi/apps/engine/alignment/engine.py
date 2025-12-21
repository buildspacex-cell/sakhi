from __future__ import annotations

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


async def compute_alignment_map(person_id: str) -> Dict[str, Any]:
    # wellness state
    wellness_row = await q(
        "SELECT body, mind, emotion, energy FROM wellness_state_cache WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    body_score = (wellness_row.get("body") or {}).get("score", 0) if isinstance(wellness_row.get("body"), dict) else 0
    mind_score = (wellness_row.get("mind") or {}).get("score", 0) if isinstance(wellness_row.get("mind"), dict) else 0
    emotion_score = (wellness_row.get("emotion") or {}).get("score", 0) if isinstance(wellness_row.get("emotion"), dict) else 0
    energy_score = (wellness_row.get("energy") or {}).get("score", 0) if isinstance(wellness_row.get("energy"), dict) else 0

    # emotion loop
    emo_state = await q(
        "SELECT long_term->>'emotion_state' as es FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    mode = ""
    drift = 0.0
    if emo_state and emo_state.get("es"):
        es = emo_state.get("es") if isinstance(emo_state.get("es"), dict) else {}
        mode = es.get("mode") or ""
        drift = float(es.get("drift") or 0)

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
        # derive intent strength using title match
        title = (task.get("title") or "").lower()
        matched_intent_strength = 0.0
        matched_alignment = 0.0
        for intent_name, strength in intent_strength_map.items():
            if intent_name and intent_name in title:
                matched_intent_strength = max(matched_intent_strength, strength)
                matched_alignment = max(matched_alignment, intent_align_map.get(intent_name, 0))
        urgency = priority  # reuse auto_priority as urgency proxy
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
