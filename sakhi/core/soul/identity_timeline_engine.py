from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from sakhi.apps.api.core.llm import call_llm


def compute_fast_identity_timeline_frame(
    episodic_tail: Sequence[Dict[str, Any]] | None,
    soul_state: Dict[str, Any] | None,
    emotion_state: Dict[str, Any] | None,
    rhythm_state: Dict[str, Any] | None,
    identity_momentum_state: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Deterministic, no LLM, <5ms.
    """
    def _ensure_dict(val: Any) -> Dict[str, Any]:
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return {}

    tail = episodic_tail or []
    soul = _ensure_dict(soul_state)
    emotion = _ensure_dict(emotion_state)
    rhythm = _ensure_dict(rhythm_state)
    momentum = _ensure_dict(identity_momentum_state)

    shadow = soul.get("shadow") or []
    light = soul.get("light") or []
    friction = soul.get("friction") or soul.get("conflicts") or []
    mood = (emotion.get("dominant") or emotion.get("summary") or "neutral").lower()
    energy = float(rhythm.get("body_energy") or rhythm.get("energy") or 0.5)
    focus = float(rhythm.get("mind_focus") or rhythm.get("focus") or 0.5)
    momentum_score = float(momentum.get("momentum_score") or 0.5)

    # phase detection (simple heuristics)
    if momentum_score > 0.7 and energy > 0.6:
        current_phase = "exploration"
    elif len(friction) > 0 and momentum_score < 0.4:
        current_phase = "transition"
    elif len(light) > len(shadow) and energy < 0.5:
        current_phase = "renewal"
    else:
        current_phase = "steady"

    phase_intensity = max(0.0, min(1.0, momentum_score))

    # persona shift tendency
    trend_tokens = ("new", "change", "shift", "transition")
    trend_hits = sum(1 for ep in tail[-5:] if any(t in str(ep.get("text") or "").lower() for t in trend_tokens))
    if trend_hits > 1:
        persona_shift_tendency = "expanding"
    elif momentum_score < 0.3:
        persona_shift_tendency = "contracting"
    else:
        persona_shift_tendency = "stable"

    shadow_pressure = max(0.0, min(1.0, (len(shadow) + len(friction)) * 0.1))

    emerging_identity_signal = None
    themes = soul.get("identity_themes") or []
    if themes:
        emerging_identity_signal = themes[0]
    elif light:
        emerging_identity_signal = light[0]

    return {
        "current_phase": current_phase,
        "phase_intensity": phase_intensity,
        "persona_shift_tendency": persona_shift_tendency,
        "shadow_pressure": shadow_pressure,
        "emerging_identity_signal": emerging_identity_signal,
    }


async def compute_deep_identity_timeline(
    person_id: str,
    episodic: Sequence[Dict[str, Any]],
    soul_state: Dict[str, Any],
    emotion_state: Dict[str, Any],
    rhythm_state: Dict[str, Any],
    identity_momentum_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Worker-time LLM pipeline for identity timeline/persona evolution.
    """
    prompt = (
        "You are Sakhi's Identity Timeline engine. Given soul_state, emotion_state, rhythm_state, identity_momentum_state, and episodic history, "
        "return JSON with: weekly_identity_phase, persona_evolution, timeline_nodes, transitions_detected, identity_arc, persona_arc, "
        "renewal_signals, shadow_integration_progress, long_term_identity_projection. Concise JSON only."
    )
    payload = {
        "person_id": person_id,
        "soul_state": soul_state or {},
        "emotion_state": emotion_state or {},
        "rhythm_state": rhythm_state or {},
        "identity_momentum_state": identity_momentum_state or {},
        "episodic": episodic or [],
    }
    result = await call_llm(messages=[{"role": "user", "content": f"{prompt}\n\nPAYLOAD:\n{payload}"}])
    if isinstance(result, dict):
        return result
    return {"identity_arc": str(result)}
