from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _stability_score(moment_model: Dict[str, Any]) -> float:
    stability = (moment_model or {}).get("stability")
    return {"stable": 0.8, "fragile": 0.4, "volatile": 0.2}.get(stability, 0.5)


def _alignment_or_conflict_strength(conflict_state: Dict[str, Any], alignment_state: Dict[str, Any]) -> float:
    conflict_score = float((conflict_state or {}).get("conflict_score") or 0)
    conflict_present = (conflict_state or {}).get("present") is True
    alignment_tension = float((alignment_state or {}).get("tension_score") or 0)
    base = max(conflict_score, alignment_tension)
    if conflict_present and base < 0.6:
        base = 0.6
    return min(1.0, base)


def _continuity_signal(continuity_state: Dict[str, Any]) -> float:
    turns = len((continuity_state or {}).get("last_text_turns") or [])
    return 0.15 if turns >= 4 else 0.05


def _compute_confidence(
    evidence_conf: float,
    moment_model: Dict[str, Any],
    conflict_state: Dict[str, Any],
    alignment_state: Dict[str, Any],
    continuity_state: Dict[str, Any],
) -> float:
    stability = _stability_score(moment_model)
    align_conf = _alignment_or_conflict_strength(conflict_state, alignment_state)
    cont = _continuity_signal(continuity_state)
    confidence = (evidence_conf * 0.35) + (stability * 0.25) + (align_conf * 0.25) + (cont * 0.15)
    return min(1.0, max(0.0, confidence))


def _decision_domain(conflict_state: Dict[str, Any], alignment_state: Dict[str, Any], identity_state: Dict[str, Any]) -> str:
    if (conflict_state or {}).get("present") or (conflict_state or {}).get("conflicts"):
        return "inner tension"
    if (alignment_state or {}).get("tension_score") and alignment_state.get("tension_score") >= 0.6:
        return "values vs priority"
    if (identity_state or {}).get("drift_score"):
        return "identity drift"
    return "general consideration"


def _current_tension(conflict_state: Dict[str, Any], alignment_state: Dict[str, Any], identity_state: Dict[str, Any]) -> str:
    if (conflict_state or {}).get("dominant_conflict"):
        return str(conflict_state.get("dominant_conflict"))
    if (alignment_state or {}).get("tension_score") and alignment_state.get("tension_score") >= 0.6:
        return "alignment tension"
    if (identity_state or {}).get("drift_score"):
        return "identity drift"
    return "unclear tension"


def _neutral_options() -> List[str]:
    return [
        "Name the trade-offs on each side without choosing yet.",
        "Note what matters most in one line before moving further.",
        "Hold both possibilities for a moment; see what stays relevant.",
        "Consider a tiny, reversible step to learn without committing.",
    ]


def compute_deliberation_scaffold(
    *,
    moment_model: Dict[str, Any],
    evidence_pack: Dict[str, Any],
    conflict_state: Dict[str, Any],
    alignment_state: Dict[str, Any],
    identity_state: Dict[str, Any],
    forecast_state: Dict[str, Any],
    continuity_state: Dict[str, Any],
) -> Dict[str, Any] | None:
    # Gate: moment model must be clarify/expand
    mode = (moment_model or {}).get("recommended_companion_mode")
    if mode not in {"clarify", "expand"}:
        return None

    # Tension signals
    tension_present = False
    if (conflict_state or {}).get("present") or (conflict_state or {}).get("conflicts"):
        tension_present = True
    if (alignment_state or {}).get("tension_score") and alignment_state.get("tension_score") >= 0.6:
        tension_present = True
    if (identity_state or {}).get("drift_score"):
        tension_present = True
    if ((forecast_state or {}).get("risk_windows") or {}).get("overwhelm_window"):
        tension_present = True
    if not tension_present:
        return None

    anchors = (evidence_pack or {}).get("anchors") or []
    evidence_conf = float((evidence_pack or {}).get("confidence") or 0)
    stability_val = _stability_score(moment_model)
    emotional_intensity = (moment_model or {}).get("emotional_intensity")
    stability_label = (moment_model or {}).get("stability")

    confidence = _compute_confidence(
        evidence_conf,
        moment_model,
        conflict_state,
        alignment_state,
        continuity_state,
    )

    # Suppression rules
    if confidence < 0.45:
        return None
    if len(anchors) < 1:
        return None
    if emotional_intensity == "high" and stability_label in {"volatile", "fragile"}:
        return None

    domain = _decision_domain(conflict_state, alignment_state, identity_state)
    tension_label = _current_tension(conflict_state, alignment_state, identity_state)

    options = _neutral_options()[:3]
    signals_used = ["moment_model", "evidence_pack", "conflict_state", "alignment_state", "identity_state", "forecast_state"]

    return {
        "current_tension": tension_label,
        "decision_domain": domain,
        "options": options,
        "signals_used": signals_used,
        "explicitly_not_deciding": True,
        "confidence": confidence,
    }


__all__ = ["compute_deliberation_scaffold"]
