from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

# Rhythm thresholds (descriptive, not prescriptive)
LOW_ENERGY_THRESHOLD = 0.4
HIGH_LOAD_THRESHOLD = 0.6
HIGH_STRAIN_THRESHOLD = 0.6
SUFFICIENT_ENERGY_THRESHOLD = 0.5
LOW_LOAD_THRESHOLD = 0.4
LOW_STRAIN_THRESHOLD = 0.4
MAX_ZONES_PER_VALUE = 1
CONDITION_PRIORITY = ["persistent_negative", "high_volatility", "high_activation"]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def compute_emotion_soul_rhythm_state(
    emotion_state: Dict[str, Any],
    soul_state: Dict[str, Any],
    rhythm_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Sensemaking join of emotion, soul, and rhythm signals.
    No advice, no narrative, deterministic only.
    """
    window_days = min(
        emotion_state.get("window_days", 0) or 0,
        rhythm_state.get("window_days", 0) or 0,
    )
    now = dt.datetime.utcnow().isoformat()

    conditions: Dict[str, bool] = emotion_state.get("conditions") or {}
    soul_values: List[str] = [v for v in (soul_state.get("core_values") or []) if v]
    if not soul_values:
        fallback = soul_state.get("identity_themes") or []
        soul_values = [v for v in fallback[:2] if v]

    overall = rhythm_state.get("overall") or rhythm_state
    energy_level = float(overall.get("energy_level", 0) or 0.0)
    load_level = float(overall.get("load_level", 0) or 0.0)
    strain_level = float(overall.get("strain_level", 0) or 0.0)

    rhythm_constraints: List[str] = []
    rhythm_supports: List[str] = []
    if energy_level < LOW_ENERGY_THRESHOLD:
        rhythm_constraints.append("low_energy")
    if load_level > HIGH_LOAD_THRESHOLD:
        rhythm_constraints.append("high_load")
    if strain_level > HIGH_STRAIN_THRESHOLD:
        rhythm_constraints.append("high_strain")
    if energy_level >= SUFFICIENT_ENERGY_THRESHOLD:
        rhythm_supports.append("sufficient_energy")
    if load_level <= LOW_LOAD_THRESHOLD:
        rhythm_supports.append("low_load")
    if strain_level <= LOW_STRAIN_THRESHOLD:
        rhythm_supports.append("low_strain")

    tension_zones: List[Dict[str, Any]] = []
    coherence_zones: List[Dict[str, Any]] = []

    # Salience gating: one zone per value, with deterministic priority
    for value in soul_values:
        chosen_zone: Dict[str, Any] | None = None
        for cond_name in CONDITION_PRIORITY:
            cond_active = conditions.get(cond_name)
            if not cond_active:
                continue
            if rhythm_constraints:
                constraint = rhythm_constraints[0]
                chosen_zone = {
                    "value": value,
                    "emotion_condition": cond_name,
                    "rhythm_constraint": constraint,
                    "signal": f"{cond_name}_with_{constraint}",
                }
                break
            if rhythm_supports:
                support = rhythm_supports[0]
                chosen_zone = {
                    "value": value,
                    "emotion_condition": cond_name,
                    "rhythm_support": support,
                    "signal": f"{cond_name}_with_{support}",
                }
                break
        if chosen_zone:
            # enforce single zone per value
            if chosen_zone.get("rhythm_constraint"):
                tension_zones.append(chosen_zone)
            else:
                coherence_zones.append(chosen_zone)
            continue
        # If nothing matched the priority list, allow a single coherence from any active condition + support
        if rhythm_supports:
            for cond_name, cond_active in conditions.items():
                if cond_active:
                    support = rhythm_supports[0]
                    coherence_zones.append(
                        {
                            "value": value,
                            "emotion_condition": cond_name,
                            "rhythm_support": support,
                            "signal": f"{cond_name}_with_{support}",
                        }
                    )
                    break
        if len(tension_zones) + len(coherence_zones) >= MAX_ZONES_PER_VALUE:
            continue

    # Deduplicate globally by (value, signal)
    seen_signals = set()
    final_tension: List[Dict[str, Any]] = []
    final_coherence: List[Dict[str, Any]] = []
    for zone in tension_zones:
        key = (zone.get("value"), zone.get("signal"))
        if key in seen_signals:
            continue
        seen_signals.add(key)
        final_tension.append(zone)
    for zone in coherence_zones:
        key = (zone.get("value"), zone.get("signal"))
        if key in seen_signals:
            continue
        seen_signals.add(key)
        final_coherence.append(zone)

    alignment_level = 1.0 - (len(final_tension) / max(1, len(soul_values)))
    alignment_level = _clamp(alignment_level)

    state: Dict[str, Any] = {
        "alignment_level": alignment_level,
        "tension_zones": final_tension,
        "coherence_zones": final_coherence,
        "dominant_tension": None,
        "window_days": window_days,
        "updated_at": now,
    }

    if final_tension:
        first = final_tension[0]
        state["dominant_tension"] = f"{first['value']}_{first['emotion_condition']}_{first.get('rhythm_constraint')}"

    return state


def compute_fast_esr_frame(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Legacy shim: turn_v2 imports this symbol. The deep join is
    handled by compute_emotion_soul_rhythm_state above. This shim
    returns an empty frame to satisfy the interface without adding
    new behavior.
    """
    return {}


async def compute_deep_esr(
    person_id: str,
    episodic_records: List[Dict[str, Any]],
    emotion_state: Dict[str, Any],
    soul_state: Dict[str, Any],
    rhythm_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deep ESR computation from historical episodic records.

    Aggregates soul/rhythm/emotion signals across episodic history
    for a richer, time-weighted analysis.
    """
    import json

    # Helper to ensure dict from potentially JSON string
    def _ensure_dict(val: Any) -> Dict[str, Any]:
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        return {}

    # Aggregate soul signals from episodic records
    all_core_values: List[str] = []
    all_shadows: List[str] = []
    all_lights: List[str] = []

    for record in episodic_records:
        soul = record.get("soul") or {}
        soul = _ensure_dict(soul)
        if isinstance(soul, dict):
            all_core_values.extend(soul.get("core_values") or [])
            all_shadows.extend(soul.get("shadows") or [])
            all_lights.extend(soul.get("lights") or [])
        elif isinstance(soul, list):
            # Handle case where soul is stored as list of values
            all_core_values.extend(soul)

    # Count frequencies
    from collections import Counter
    value_counts = Counter(all_core_values)
    shadow_counts = Counter(all_shadows)
    light_counts = Counter(all_lights)

    # Merge with current soul_state
    merged_soul = dict(_ensure_dict(soul_state))
    if value_counts:
        merged_soul["core_values"] = [v for v, _ in value_counts.most_common(5)]
    if shadow_counts:
        merged_soul["shadows"] = [s for s, _ in shadow_counts.most_common(3)]
    if light_counts:
        merged_soul["lights"] = [l for l, _ in light_counts.most_common(3)]

    # Compute base ESR state
    base_state = compute_emotion_soul_rhythm_state(emotion_state, merged_soul, rhythm_state)

    # Add deep analysis metadata
    base_state["deep_analysis"] = {
        "episodic_count": len(episodic_records),
        "unique_values": len(value_counts),
        "unique_shadows": len(shadow_counts),
        "unique_lights": len(light_counts),
        "top_values": [v for v, _ in value_counts.most_common(3)],
    }
    base_state["person_id"] = person_id

    return base_state
