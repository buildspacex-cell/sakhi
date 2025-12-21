from __future__ import annotations

import json
from typing import Any, Dict, List


def _ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _avg(values: List[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def _sum_minutes(blocks: Any) -> float:
    items = _ensure_list(blocks)
    total = 0.0
    for blk in items:
        if isinstance(blk, dict):
            total += _to_float(blk.get("total_minutes"), 0.0)
    return total


def compute_behavior_profile(brain: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic mapping from Personal OS Brain -> Behavior Profile.
    """

    goals = _ensure_dict(brain.get("goals_state"))
    rhythm = _ensure_dict(brain.get("rhythm_state"))
    emotion = _ensure_dict(brain.get("emotional_state"))
    relationship = _ensure_dict(brain.get("relationship_state"))
    environment = _ensure_dict(brain.get("environment_state"))
    habits = _ensure_dict(brain.get("habits_state"))
    focus = _ensure_dict(brain.get("focus_state"))
    identity = _ensure_dict(brain.get("identity_state"))
    friction_points = _ensure_list(brain.get("friction_points"))
    life_chapter = _ensure_dict(brain.get("life_chapter"))

    dominant_emotion = str(emotion.get("dominant") or "").lower()
    sentiment_trend = str(emotion.get("sentiment_trend") or "").lower()
    fragility = _to_float(emotion.get("fragility"), 0.0)

    body_energy = _to_float(rhythm.get("body_energy"), 0.5)
    mind_focus = _to_float(rhythm.get("mind_focus"), 0.5)
    stress_trend = str(rhythm.get("stress_trend") or "").lower()

    trust = _to_float(relationship.get("trust_score"), 0.5)
    attune = _to_float(relationship.get("attunement_score"), 0.5)
    closeness = (relationship.get("closeness_stage") or "").strip()

    focus_outcome = _to_float(focus.get("outcome"), 0.5)
    focus_status = (focus.get("status") or "").lower()
    focus_distractions = focus.get("distraction_pattern")

    intention_alignment = _to_float(identity.get("intention_alignment"), 0.6)
    identity_mode = str(identity.get("mode") or "").lower()

    travel_flag = bool(environment.get("travel_flag"))
    meeting_load = _sum_minutes(environment.get("calendar_blocks"))
    weather = str(environment.get("weather") or "").lower()
    env_tags = _ensure_list(environment.get("environment_tags"))

    streaks = [
        _to_float(h.get("streak_count"), 0.0) for h in habits.get("top_habits", []) if isinstance(h, dict)
    ]
    habit_confidence = [
        _to_float(h.get("confidence"), 0.0) for h in habits.get("top_habits", []) if isinstance(h, dict)
    ]
    habit_consistency = _avg(streaks, 0.0)
    habit_motivation = _avg(habit_confidence, 0.5)

    friction_count = len(friction_points)

    stressed = (
        "stress" in dominant_emotion
        or "anxious" in dominant_emotion
        or "overwhelm" in dominant_emotion
        or fragility > 0.6
        or stress_trend == "rising"
    )
    low_mood = any(tok in dominant_emotion for tok in ["sad", "low", "tired", "down"])
    energized = body_energy > 0.68 or mind_focus > 0.7 or "excited" in dominant_emotion
    calm = dominant_emotion in {"neutral", "calm", "steady"} and not stressed and not low_mood
    rhythm_trough = body_energy < 0.42
    rhythm_peak = body_energy > 0.65
    cognitive_load_high = friction_count >= 3 or meeting_load > 300

    profile: Dict[str, Any] = {
        "tone_profile": "warm",
        "pacing": "medium",
        "conversation_depth": "medium",
        "guidance_intensity": "supportive",
        "nudge_frequency": "medium",
        "reflection_invitations": "light",
        "planner_style": "structured",
        "proactiveness": "balanced",
        "emotional_alignment": "grounding",
        "avoid_modes": [],
        "session_context": {"reason": "momentum"},
    }

    # Emotional rules
    if stressed:
        profile.update(
            {
                "tone_profile": "soft",
                "pacing": "short",
                "conversation_depth": "surface",
                "guidance_intensity": "minimal",
                "proactiveness": "passive",
                "reflection_invitations": "none",
                "emotional_alignment": "calming",
                "session_context": {"reason": "stress"},
            }
        )
        profile["avoid_modes"].extend(["no_deep_emotion", "no_intense_planning"])
    elif low_mood:
        profile.update(
            {
                "tone_profile": "warm",
                "pacing": "medium",
                "conversation_depth": "surface",
                "guidance_intensity": "supportive",
                "reflection_invitations": "light",
                "proactiveness": "balanced",
                "emotional_alignment": "grounding",
                "session_context": {"reason": "fatigue"},
            }
        )
        profile["avoid_modes"].append("no_intense_planning")
    elif energized:
        profile.update(
            {
                "tone_profile": "uplifting",
                "pacing": "extended",
                "conversation_depth": "reflective",
                "guidance_intensity": "active",
                "proactiveness": "proactive",
                "planner_style": "advisory",
                "emotional_alignment": "energizing",
                "session_context": {"reason": "momentum"},
            }
        )
    elif calm:
        profile.update(
            {
                "tone_profile": "focused",
                "conversation_depth": "medium",
                "planner_style": "structured",
                "guidance_intensity": "supportive",
                "session_context": {"reason": "steady"},
            }
        )

    # Rhythm influence
    if rhythm_trough:
        profile["tone_profile"] = "soft"
        profile["pacing"] = "short"
        profile["guidance_intensity"] = "supportive"
        profile["proactiveness"] = "passive"
        profile["emotional_alignment"] = "grounding"
        profile["avoid_modes"].append("no_intense_planning")
        profile["session_context"] = {"reason": "fatigue"}
    elif rhythm_peak:
        profile["guidance_intensity"] = "active"
        profile["pacing"] = "medium"
        profile["planner_style"] = "advisory" if profile["planner_style"] != "light-touch" else profile["planner_style"]
        profile["proactiveness"] = "proactive"
        profile["emotional_alignment"] = "energizing"
        profile["session_context"] = {"reason": "momentum"}

    # Relationship state
    if trust < 0.4:
        profile["nudge_frequency"] = "low"
        profile["proactiveness"] = "passive"
        profile["tone_profile"] = "soft"
    elif attune > 0.7 or closeness.lower() == "strong bond":
        profile["nudge_frequency"] = "high"
        profile["conversation_depth"] = "reflective"
        profile["reflection_invitations"] = "deep"

    # Focus state
    if focus_outcome >= 0.7 and focus_status == "ended":
        profile["planner_style"] = "structured" if profile["planner_style"] != "advisory" else "advisory"
        profile["guidance_intensity"] = "active"
        profile["conversation_depth"] = "medium"
    elif focus_outcome <= 0.4 or focus_distractions:
        profile["planner_style"] = "light-touch"
        profile["guidance_intensity"] = "minimal"
        profile["proactiveness"] = "passive"
        profile["avoid_modes"].append("no_intense_planning")

    # Identity/purpose alignment
    if intention_alignment < 0.5 or "drift" in identity_mode:
        profile["tone_profile"] = "warm"
        profile["guidance_intensity"] = "supportive"
        profile["reflection_invitations"] = "light"
        profile["proactiveness"] = "passive"
        profile["planner_style"] = "light-touch"
        profile["avoid_modes"].append("no_intense_planning")
        profile["session_context"] = {"reason": "growth"}

    # Environment
    if travel_flag:
        profile["pacing"] = "short"
        profile["planner_style"] = "light-touch"
        profile["guidance_intensity"] = "minimal"
        profile["proactiveness"] = "passive"
        profile["avoid_modes"].append("no_intense_planning")
        profile["session_context"] = {"reason": "travel"}
    if meeting_load > 300:
        profile["pacing"] = "short"
        profile["planner_style"] = "light-touch"
        profile["conversation_depth"] = "surface"
        profile["guidance_intensity"] = "supportive"
        profile["nudge_frequency"] = "low"
    if "rain" in weather or "storm" in weather or any("rain" in str(tag).lower() for tag in env_tags):
        profile["emotional_alignment"] = "grounding"

    # Habits & growth
    if habit_consistency >= 3 and habit_motivation >= 0.6:
        profile["proactiveness"] = "proactive" if profile["proactiveness"] != "passive" else "balanced"
        profile["planner_style"] = "structured" if profile["planner_style"] != "light-touch" else "light-touch"
        profile["nudge_frequency"] = "medium" if profile["nudge_frequency"] == "low" else profile["nudge_frequency"]
    else:
        profile["proactiveness"] = "balanced" if profile["proactiveness"] == "proactive" else profile["proactiveness"]
        profile["guidance_intensity"] = "supportive" if profile["guidance_intensity"] == "active" else profile["guidance_intensity"]

    # Friction/cognitive load
    if cognitive_load_high:
        profile["pacing"] = "short"
        profile["planner_style"] = "light-touch"
        profile["guidance_intensity"] = "minimal"
        profile["proactiveness"] = "passive"
        profile["avoid_modes"].append("no_intense_planning")
        profile["session_context"] = {"reason": "stress"}

    # Life chapter nuance
    if life_chapter.get("chapter") and profile["conversation_depth"] == "medium":
        profile["conversation_depth"] = "reflective"
        profile["reflection_invitations"] = "light"

    # Deduplicate avoid modes
    profile["avoid_modes"] = sorted(set(profile["avoid_modes"]))

    return profile


__all__ = ["compute_behavior_profile"]
