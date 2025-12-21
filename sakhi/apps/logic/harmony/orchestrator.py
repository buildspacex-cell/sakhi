from __future__ import annotations

import asyncio
import re
from typing import Any, Dict

from sakhi.apps.logic.brain import brain_engine
from sakhi.apps.logic.brain.brain_engine import _ensure_dict
from sakhi.apps.logic.companion.behavior_engine import compute_behavior_profile
from sakhi.apps.logic.insight import insight_engine


def triage_text(user_text: str, behavior_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Light triage to inform which engines to activate."""
    text = (user_text or "").lower()
    intent_signals = any(tok in text for tok in ["plan", "schedule", "goal", "next step", "todo", "task"])
    reflective_signals = any(tok in text for tok in ["why", "feel", "feeling", "reflect", "meaning", "insight"])
    energy_signals = any(tok in text for tok in ["tired", "energy", "fatigue", "exhaust", "drained"])
    relationship_signals = any(tok in text for tok in ["trust", "relationship", "you and i", "feel heard"])
    identity_signals = any(tok in text for tok in ["identity", "values", "purpose", "who i am"])

    depth = behavior_profile.get("conversation_depth", "surface")
    session_reason = (behavior_profile.get("session_context") or {}).get("reason")

    return {
        "intent_request": intent_signals,
        "reflective_request": reflective_signals or depth == "reflective",
        "energy_request": energy_signals or session_reason in {"fatigue", "stress"},
        "relationship_focus": relationship_signals,
        "identity_focus": identity_signals,
        "session_reason": session_reason,
    }


def decide_activation(triage: Dict[str, Any], behavior_profile: Dict[str, Any]) -> Dict[str, bool]:
    """Declarative activation rules for engines."""
    planner_style = behavior_profile.get("planner_style", "structured")
    depth = behavior_profile.get("conversation_depth", "medium")

    planner_active = triage.get("intent_request") and planner_style != "none"
    if planner_style == "light-touch":
        planner_active = planner_active and depth != "surface"

    insight_active = triage.get("reflective_request") or depth == "reflective"

    rhythm_active = triage.get("energy_request")

    relationship_active = True  # light state update hooks

    soul_active = triage.get("identity_focus")

    return {
        "planner": planner_active,
        "insight": insight_active,
        "rhythm": rhythm_active,
        "relationship": relationship_active,
        "soul": soul_active,
    }


async def run_unified_turn(person_id: str, user_text: str, *, mode: str = "today") -> Dict[str, Any]:
    """
    Harmony orchestrator: fetch brain, behavior, triage, decide activations, call engines.
    """
    brain = await brain_engine.get_brain_state(person_id, force_refresh=False)
    behavior_profile = compute_behavior_profile(brain)
    triage = triage_text(user_text, behavior_profile)
    activation = decide_activation(triage, behavior_profile)

    planner_payload = None  # planner runs in workers; route only carries activation signal
    insight_bundle = None
    rhythm_hint: Dict[str, Any] | None = None
    relationship_update: Dict[str, Any] | None = None

    # Insight
    if activation["insight"]:
        try:
            insight_bundle = await insight_engine.generate_insights(person_id, mode=mode, behavior_profile=behavior_profile)
        except Exception:
            insight_bundle = {"error": "insight_unavailable"}

    # Rhythm hint (do not force heavy recompute)
    if activation["rhythm"]:
        rhythm_state = _ensure_dict(brain.get("rhythm_state"))
        rhythm_hint = {
            "body_energy": rhythm_state.get("body_energy"),
            "stress_trend": rhythm_state.get("stress_trend"),
        }

    # Relationship update marker (no DB write here to avoid double writes)
    if activation["relationship"]:
        relationship_update = _ensure_dict(brain.get("relationship_state"))

    return {
        "brain": brain,
        "behavior_profile": behavior_profile,
        "triage": triage,
        "activation": activation,
        "planner": planner_payload,
        "insight": insight_bundle,
        "rhythm_hint": rhythm_hint,
        "relationship_state": relationship_update,
    }


__all__ = ["run_unified_turn", "triage_text", "decide_activation"]
