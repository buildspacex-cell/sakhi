"""
Drift & Friction — Pure state-math for dosha imbalance detection.

Vikriti (Sanskrit: "deviation") represents the current state of imbalance
relative to one's constitutional baseline (Prakruti).

Friction Framework Mapping:
- Vata elevated  → Chaos Friction    (scattered, anxious, overwhelmed)
- Pitta elevated → Intensity Friction (driven, irritable, burning out)
- Kapha elevated → Stagnation Friction (stuck, sluggish, unmotivated)

Drift percentage indicates how far from baseline the person currently is.
Higher drift = greater imbalance = more targeted recommendations needed.

All functions are pure computation — zero DB, LLM, or sakhi dependencies.
"""

from __future__ import annotations

import math
from typing import Any

# =============================================================================
# Constants
# =============================================================================

# Friction state descriptions for user-facing display
FRICTION_STATES: dict[str, dict[str, Any]] = {
    "chaos": {
        "name": "Chaos Friction",
        "dosha": "vata",
        "description": (
            "Your energy is scattered and variable. Mind racing, "
            "difficulty focusing, anxiety may be present."
        ),
        "short": "Scattered, anxious, overwhelmed",
        "recommendations_focus": ["grounding", "routine", "warmth", "calming"],
    },
    "intensity": {
        "name": "Intensity Friction",
        "dosha": "pitta",
        "description": (
            "You're running hot - driven but potentially burning out. "
            "Irritability, perfectionism, or impatience may show up."
        ),
        "short": "Driven, irritable, burning out",
        "recommendations_focus": ["cooling", "moderation", "play", "surrender"],
    },
    "stagnation": {
        "name": "Stagnation Friction",
        "dosha": "kapha",
        "description": (
            "Energy feels heavy and stuck. Motivation is low, "
            "inertia is high, and change feels difficult."
        ),
        "short": "Stuck, sluggish, unmotivated",
        "recommendations_focus": ["stimulation", "movement", "lightness", "novelty"],
    },
    "balanced": {
        "name": "Balanced Flow",
        "dosha": None,
        "description": (
            "You're close to your natural baseline. "
            "Energy is sustainable and rhythms are working."
        ),
        "short": "Aligned, sustainable, flowing",
        "recommendations_focus": ["maintenance", "prevention", "optimization"],
    },
}

# Drift thresholds for friction classification
DRIFT_THRESHOLDS: dict[str, int] = {
    "mild": 15,       # 15%+ drift = mild imbalance
    "moderate": 25,   # 25%+ drift = moderate imbalance
    "significant": 40,  # 40%+ drift = significant imbalance
}


# =============================================================================
# Pure computation functions
# =============================================================================


def compute_baseline_drift(
    prakruti: dict[str, Any],
    vikriti: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute drift between constitutional baseline and current state.

    Uses Euclidean distance in 3D dosha space, normalized to percentage.

    Args:
        prakruti: Constitutional baseline with ``dosha_baseline``
        vikriti: Current state with ``current_dosha``

    Returns:
        Dict with drift_percentage, primary_contributor, direction,
        raw_distances, and severity.
    """
    baseline = prakruti.get("dosha_baseline") or {
        "vata": 0.33, "pitta": 0.33, "kapha": 0.34,
    }
    current = vikriti.get("current_dosha") or {
        "vata": 0.33, "pitta": 0.33, "kapha": 0.34,
    }

    # Calculate per-dosha drift
    distances = {
        "vata": round(current.get("vata", 0.33) - baseline.get("vata", 0.33), 3),
        "pitta": round(current.get("pitta", 0.33) - baseline.get("pitta", 0.33), 3),
        "kapha": round(current.get("kapha", 0.34) - baseline.get("kapha", 0.34), 3),
    }

    # Euclidean distance (max possible ~1.15 when going from 0,0,1 to 1,0,0)
    euclidean = math.sqrt(sum(d ** 2 for d in distances.values()))

    # Normalize to percentage (max ~115% → scale to 100%)
    drift_percentage = round(min(100, euclidean * 87), 1)  # 87 ≈ 100/1.15

    # Find primary contributor — prefer elevated doshas (positive deviation)
    # because elevated doshas drive friction states (chaos/intensity/stagnation).
    elevated = {k: v for k, v in distances.items() if v > 0}
    if elevated:
        primary_contributor = max(elevated, key=elevated.get)  # type: ignore[arg-type]
        direction = "elevated"
    else:
        # All doshas depleted or zero — pick largest absolute deviation
        abs_distances = {k: abs(v) for k, v in distances.items()}
        primary_contributor = max(abs_distances, key=abs_distances.get)  # type: ignore[arg-type]
        direction = "depleted"

    return {
        "drift_percentage": drift_percentage,
        "primary_contributor": primary_contributor,
        "direction": direction,
        "raw_distances": distances,
        "severity": classify_severity(drift_percentage),
    }


def classify_severity(drift_percentage: float) -> str:
    """Classify drift severity from percentage."""
    if drift_percentage < DRIFT_THRESHOLDS["mild"]:
        return "minimal"
    elif drift_percentage < DRIFT_THRESHOLDS["moderate"]:
        return "mild"
    elif drift_percentage < DRIFT_THRESHOLDS["significant"]:
        return "moderate"
    else:
        return "significant"


def classify_friction_state(
    drift: dict[str, Any],
    vikriti: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Map dosha imbalance to Friction Framework state.

    Args:
        drift: Drift data from :func:`compute_baseline_drift`
        vikriti: Optional current Vikriti for additional context

    Returns:
        Dict with state, name, description, dosha, severity, and
        recommendations_focus.
    """
    drift_percentage = drift.get("drift_percentage", 0)
    primary = drift.get("primary_contributor", "vata")
    direction = drift.get("direction", "elevated")

    # If drift is minimal, return balanced
    if drift_percentage < DRIFT_THRESHOLDS["mild"]:
        state_info = FRICTION_STATES["balanced"]
        return {
            "state": "balanced",
            "name": state_info["name"],
            "description": state_info["description"],
            "short": state_info["short"],
            "dosha": None,
            "drift_percentage": drift_percentage,
            "severity": "minimal",
            "recommendations_focus": state_info["recommendations_focus"],
        }

    # Only elevated states trigger friction (depleted states are different)
    if direction != "elevated":
        # If primary is depleted, look at what's elevated instead
        distances = drift.get("raw_distances", {})
        elevated_doshas = {k: v for k, v in distances.items() if v > 0}
        if elevated_doshas:
            primary = max(elevated_doshas, key=elevated_doshas.get)  # type: ignore[arg-type]
        else:
            # All depleted - unusual, return balanced
            state_info = FRICTION_STATES["balanced"]
            return {
                "state": "balanced",
                "name": state_info["name"],
                "description": state_info["description"],
                "short": state_info["short"],
                "dosha": None,
                "drift_percentage": drift_percentage,
                "severity": drift.get("severity", "minimal"),
                "recommendations_focus": state_info["recommendations_focus"],
            }

    # Map dosha to friction state
    dosha_to_friction = {
        "vata": "chaos",
        "pitta": "intensity",
        "kapha": "stagnation",
    }

    friction_key = dosha_to_friction.get(primary, "chaos")
    state_info = FRICTION_STATES[friction_key]

    return {
        "state": friction_key,
        "name": state_info["name"],
        "description": state_info["description"],
        "short": state_info["short"],
        "dosha": primary,
        "drift_percentage": drift_percentage,
        "severity": drift.get("severity", "mild"),
        "recommendations_focus": state_info["recommendations_focus"],
    }


__all__ = [
    "DRIFT_THRESHOLDS",
    "FRICTION_STATES",
    "classify_friction_state",
    "classify_severity",
    "compute_baseline_drift",
]
