from __future__ import annotations

import datetime
from typing import Any, Dict, Iterable, List, Optional, Set

from sakhi.apps.engine.mini_flow.adjuster import determine_rhythm_slot


def _pick_emotional_intensity(emotion_state: Dict[str, Any]) -> str:
    mode = (emotion_state or {}).get("mode") or (emotion_state or {}).get("current")
    volatility = (emotion_state or {}).get("volatility") or 0
    drift = abs((emotion_state or {}).get("drift") or 0)
    if mode == "volatile" or volatility > 0.6 or drift > 0.35:
        return "high"
    if volatility > 0.35 or drift > 0.2:
        return "medium"
    return "low"


def _pick_stability(emotion_state: Dict[str, Any], coherence_state: Dict[str, Any]) -> str:
    volatility = (emotion_state or {}).get("volatility") or 0
    mode = (emotion_state or {}).get("mode")
    coherence_score = (coherence_state or {}).get("coherence_score")
    fragmentation = (coherence_state or {}).get("fragmentation_index")
    if mode == "volatile" or volatility > 0.5 or (fragmentation is not None and fragmentation > 0.6):
        return "volatile"
    if (coherence_score is not None and coherence_score < 0.45) or (fragmentation is not None and fragmentation > 0.4):
        return "fragile"
    return "stable"


def _pick_cognitive_load(mind_state: Dict[str, Any]) -> str:
    load = (mind_state or {}).get("cognitive_load")
    if load is None:
        return "medium"
    try:
        load_val = float(load)
    except Exception:
        return "medium"
    if load_val >= 0.7:
        return "overloaded"
    if load_val >= 0.4:
        return "medium"
    return "low"


def _pick_energy_state(forecast_state: Dict[str, Any]) -> str:
    fatigue_prob = (
        (forecast_state or {})
        .get("emotion_forecast", {})
        .get("fatigue_prob")
        or 0
    )
    motivation_prob = (
        (forecast_state or {})
        .get("emotion_forecast", {})
        .get("motivation_prob")
        or 0
    )
    if fatigue_prob > 0.65:
        return "low"
    if motivation_prob > 0.6:
        return "high"
    return "medium"


def _collect_risks(forecast_state: Dict[str, Any]) -> List[str]:
    risks: Set[str] = set()
    emo_fc = (forecast_state or {}).get("emotion_forecast") or {}
    if (emo_fc.get("fatigue_prob") or 0) > 0.65:
        risks.add("fatigue")
    if (emo_fc.get("irritability_prob") or 0) > 0.55:
        risks.add("irritability")
    if ((forecast_state or {}).get("risk_windows") or {}).get("overwhelm_window"):
        risks.add("overwhelm")
    return sorted(risks)


def _continuity_state(gap_hours: Optional[float], restart: bool, continuity: Dict[str, Any]) -> str:
    if restart or (gap_hours is not None and gap_hours > 3):
        return "restarting"
    turns = len((continuity or {}).get("last_text_turns") or [])
    if turns <= 2:
        return "fragmented"
    return "flowing"


def _dominant_need(
    emotional_intensity: str,
    stability: str,
    cognitive_load: str,
    energy_state: str,
    risks: Iterable[str],
    rhythm_slot: str,
) -> str:
    if energy_state == "low" or "fatigue" in risks:
        return "rest"
    if stability in {"volatile", "fragile"} or "overwhelm" in risks:
        return "grounding"
    if cognitive_load == "overloaded":
        return "clarity"
    if emotional_intensity == "low" and stability == "stable" and energy_state != "low":
        return "expansion" if rhythm_slot in {"morning", "midday"} else "reflection"
    return "reflection"


def _mode_from_need(need: str) -> str:
    return {
        "grounding": "ground",
        "clarity": "clarify",
        "expansion": "expand",
        "rest": "pause",
        "reflection": "reflect",
    }.get(need, "hold")


def compute_moment_model(
    *,
    emotion_state: Dict[str, Any] | None,
    coherence_state: Dict[str, Any] | None,
    alignment_state: Dict[str, Any] | None,
    mind_state: Dict[str, Any] | None,
    forecast_state: Dict[str, Any] | None,
    continuity_state: Dict[str, Any] | None,
    gap_hours: Optional[float],
    restart: bool,
    active_scaffolds: Dict[str, Any] | None = None,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    Deterministic, per-turn moment classifier.
    No LLM. No persistence. Strictly rule-based.
    """
    now_dt = now or datetime.datetime.utcnow()
    rhythm_window = determine_rhythm_slot(now_dt)

    emotional_intensity = _pick_emotional_intensity(emotion_state or {})
    stability = _pick_stability(emotion_state or {}, coherence_state or {})
    cognitive_load = _pick_cognitive_load(mind_state or {})
    energy_state = _pick_energy_state(forecast_state or {})
    risks = _collect_risks(forecast_state or {})
    continuity_val = _continuity_state(gap_hours, restart, continuity_state or {})

    # Light conservative guards: if alignment/coherence is low, bias toward grounding/clarity.
    coherence_score = (coherence_state or {}).get("coherence_score")
    alignment_score = (alignment_state or {}).get("alignment_score")
    if coherence_score is not None and coherence_score < 0.45:
        risks.append("overwhelm")
    if alignment_score is not None and alignment_score < 0.4 and "fatigue" not in risks:
        risks.append("fatigue")  # conservative slow-down
    risks = sorted(set(risks))

    need = _dominant_need(
        emotional_intensity,
        stability,
        cognitive_load,
        energy_state,
        risks,
        rhythm_window,
    )

    # Conservative fallback: conflicting signals collapse to reflect/hold.
    conflicting = False
    if emotional_intensity == "high" and energy_state == "low" and cognitive_load == "overloaded":
        conflicting = True
    if emotional_intensity == "high" and stability in {"volatile", "fragile"} and "overwhelm" in risks:
        need = "grounding"
    recommended_mode = _mode_from_need(need)
    if conflicting:
        recommended_mode = "reflect"
    if continuity_val == "restarting":
        recommended_mode = "hold"

    return {
        "emotional_intensity": emotional_intensity,
        "stability": stability,
        "cognitive_load": cognitive_load,
        "energy_state": energy_state,
        "rhythm_window": rhythm_window,
        "risk_context": risks,
        "continuity_state": continuity_val,
        "dominant_need": need,
        "recommended_companion_mode": recommended_mode,
    }


__all__ = ["compute_moment_model"]
