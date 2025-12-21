from __future__ import annotations

from typing import Any, Dict, Sequence

def compute_fast_rhythm_soul_frame(st: Sequence[Dict[str, Any]] | None, rhythm: Dict[str, Any] | None, soul: Dict[str, Any] | None) -> Dict[str, Any]:
    """Deterministic, turn-time computation (<3ms, no LLM)."""
    rhythm = rhythm or {}
    soul = soul or {}
    if isinstance(rhythm, str):
        try:
            import json

            rhythm = json.loads(rhythm)
        except Exception:
            rhythm = {}
    if not isinstance(rhythm, dict):
        rhythm = {}
    if isinstance(soul, str):
        try:
            import json

            soul = json.loads(soul)
        except Exception:
            soul = {}
    if not isinstance(soul, dict):
        soul = {}
    short_term = st or []

    values = soul.get("core_values") or []
    shadow = soul.get("shadow") or []
    light = soul.get("light") or []
    conflicts = soul.get("conflicts") or []
    energy = float(rhythm.get("body_energy") or 0.5)
    mind_focus = float(rhythm.get("mind_focus") or 0.5)

    # coherence: weighted by energy/focus and value presence vs conflicts
    base = (len(values) + 1) / ((len(conflicts) or 0) + 2)
    energy_factor = (energy + mind_focus) / 2
    coherence_score = max(0.0, min(1.0, base * 0.5 + energy_factor * 0.5))

    identity_momentum = (len(light) + 1) / (len(shadow) + len(conflicts) + 2)
    identity_momentum = max(0.0, min(1.0, identity_momentum))

    shadow_pressure = (len(shadow) + len(conflicts)) / ((len(light) + 1) * 3)
    shadow_disruption = max(0.0, min(1.0, shadow_pressure))

    # rhythm tone adjust: if energy low and shadow high, recommend softer pacing
    if energy < 0.4 or shadow_disruption > 0.6:
        rhythm_tone_adjustment = "soft"
    elif energy > 0.7 and shadow_disruption < 0.3:
        rhythm_tone_adjustment = "energized"
    else:
        rhythm_tone_adjustment = "steady"

    return {
        "coherence_score": coherence_score,
        "identity_momentum": identity_momentum,
        "shadow_disruption": shadow_disruption,
        "rhythm_tone_adjustment": rhythm_tone_adjustment,
    }


async def compute_deep_rhythm_soul(person_id: str, episodic: Sequence[Dict[str, Any]], rhythm_state: Dict[str, Any], soul_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker-time, can use LLM router if available.
    Output keys:
      - value_energy_map
      - weekly_coherence_summary
      - life_phase_interaction
      - shadow_cycle_effects
      - recommended_pacing_style
    """
    from sakhi.apps.api.core.llm import call_llm

    payload = {
        "person_id": person_id,
        "rhythm_state": rhythm_state or {},
        "soul_state": soul_state or {},
        "episodic": episodic or [],
    }
    prompt = (
        "You are Sakhi's Rhythm×Soul deep analyzer. "
        "Given rhythm_state, soul_state, and episodic signals, return JSON with keys: "
        "value_energy_map (map), weekly_coherence_summary (string), life_phase_interaction (string), "
        "shadow_cycle_effects (string), recommended_pacing_style (string). "
        "Be concise, JSON only."
    )
    result = await call_llm(messages=[{"role": "user", "content": f"{prompt}\n\nPAYLOAD:\n{payload}"}])
    if isinstance(result, dict):
        return result
    return {"weekly_coherence_summary": str(result)}
