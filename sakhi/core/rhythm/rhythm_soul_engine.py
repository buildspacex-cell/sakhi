from __future__ import annotations

from typing import Any, Dict, Sequence
import datetime as dt
import json

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


def compute_deep_rhythm_soul(person_id: str, episodic: Sequence[Dict[str, Any]], rhythm_state: Dict[str, Any], soul_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic sensemaking over rhythm_state and soul_state.
    Detects alignment/tension; no narrative, no advice, no LLM.
    """
    def _clamp(val: float) -> float:
        return max(0.0, min(1.0, val))

    def _coerce_dict(value: Any) -> Dict[str, Any]:
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

    rhythm = rhythm_state or {}
    soul = soul_state or {}
    if isinstance(rhythm, str):
        try:
            rhythm = json.loads(rhythm)
        except Exception:
            rhythm = {}
    if isinstance(soul, str):
        try:
            soul = json.loads(soul)
        except Exception:
            soul = {}
    if not isinstance(rhythm, dict):
        rhythm = {}
    if not isinstance(soul, dict):
        soul = {}

    overall = _coerce_dict(rhythm.get("overall"))
    energy = float(overall.get("energy_level") or 0.5)
    load = float(overall.get("load_level") or 0.0)
    recovery = float(overall.get("recovery_level") or 0.0)
    strain = float(overall.get("strain_level") or 0.0)
    window_days = int(rhythm.get("window_days") or overall.get("window_days") or 0)

    slots = _coerce_dict(rhythm.get("slots"))
    tension_zones = []
    coherence_zones = []
    soul_values = soul.get("core_values") or []
    for slot, metrics in slots.items():
        metrics = _coerce_dict(metrics)
        e = float(metrics.get("energy_level") or 0.5)
        l = float(metrics.get("load_level") or 0.0)
        s = float(metrics.get("strain_level") or 0.0)
        r = float(metrics.get("recovery_level") or 0.0)
        for value in soul_values:
            if not value:
                continue
            if l > e + 0.1 or s > e:
                tension_zones.append(
                    {
                        "value": value,
                        "time_slot": slot,
                        "signal": "high_load_conflicting_with_value",
                    }
                )
            elif e > l + s + 0.1:
                coherence_zones.append(
                    {
                        "value": value,
                        "time_slot": slot,
                        "signal": "sufficient_energy_for_value",
                    }
                )
            elif e < 0.4:
                tension_zones.append(
                    {
                        "value": value,
                        "time_slot": slot,
                        "signal": "low_energy_against_value",
                    }
                )

    alignment_level = _clamp(0.5 + (energy - load) * 0.25 + (recovery - strain) * 0.25)
    dominant_tension = tension_zones[0]["signal"] if tension_zones else None

    return {
        "alignment_level": alignment_level,
        "dominant_tension": dominant_tension,
        "tension_zones": tension_zones,
        "coherence_zones": coherence_zones,
        "window_days": window_days,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }
