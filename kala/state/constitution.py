"""
Constitution — Pure computation for Ayurvedic constitutional type.

Prakruti (Sanskrit: "nature") represents the innate constitution a person
is born with. This baseline doesn't change but understanding it helps
interpret current state (Vikriti) deviations.

User-Facing Names (Friction Framework):
- Adaptive       (Vata-dominant):  Creative, quick-thinking, variable energy
- Performance    (Pitta-dominant): Driven, focused, goal-oriented
- Conservation   (Kapha-dominant): Steady, grounded, methodical

Combined types use hyphenated names: Adaptive-Performance, etc.

All functions are pure computation — zero DB, LLM, or sakhi dependencies.
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# Constants
# =============================================================================

# User-facing names mapped to doshas
CONSTITUTION_NAMES: dict[str, str] = {
    "vata": "Adaptive",
    "pitta": "Performance",
    "kapha": "Conservation",
}

# Reverse mapping
DOSHA_FROM_NAME: dict[str, str] = {
    "adaptive": "vata",
    "performance": "pitta",
    "conservation": "kapha",
}


# =============================================================================
# Pure computation functions
# =============================================================================


def compute_dosha_from_quiz(responses: dict[str, Any]) -> dict[str, float]:
    """
    Map quiz responses to dosha scores.

    Expected response keys (from onboarding quiz):
    - body_type: "light_thin" | "medium_muscular" | "solid_heavy"
    - energy_pattern: "variable_bursts" | "focused_sustained" | "steady_slow"
    - stress_response: "anxious_scattered" | "irritable_intense" | "withdrawn_sluggish"
    - sleep_pattern: "light_variable" | "moderate_efficient" | "deep_heavy"
    - work_style: "creative_multitask" | "goal_driven" | "methodical_consistent"
    """
    scores: dict[str, float] = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}

    # Body type mapping
    body_map = {
        "light_thin": ("vata", 1.0),
        "medium_muscular": ("pitta", 1.0),
        "solid_heavy": ("kapha", 1.0),
    }
    body_type = responses.get("body_type", "").lower().replace(" ", "_")
    if body_type in body_map:
        dosha, weight = body_map[body_type]
        scores[dosha] += weight

    # Energy pattern mapping
    energy_map = {
        "variable_bursts": ("vata", 1.0),
        "focused_sustained": ("pitta", 1.0),
        "steady_slow": ("kapha", 1.0),
    }
    energy = responses.get("energy_pattern", "").lower().replace(" ", "_")
    if energy in energy_map:
        dosha, weight = energy_map[energy]
        scores[dosha] += weight

    # Stress response mapping
    stress_map = {
        "anxious_scattered": ("vata", 1.0),
        "irritable_intense": ("pitta", 1.0),
        "withdrawn_sluggish": ("kapha", 1.0),
    }
    stress = responses.get("stress_response", "").lower().replace(" ", "_")
    if stress in stress_map:
        dosha, weight = stress_map[stress]
        scores[dosha] += weight

    # Sleep pattern mapping
    sleep_map = {
        "light_variable": ("vata", 1.0),
        "moderate_efficient": ("pitta", 1.0),
        "deep_heavy": ("kapha", 1.0),
    }
    sleep = responses.get("sleep_pattern", "").lower().replace(" ", "_")
    if sleep in sleep_map:
        dosha, weight = sleep_map[sleep]
        scores[dosha] += weight

    # Work style mapping
    work_map = {
        "creative_multitask": ("vata", 1.0),
        "goal_driven": ("pitta", 1.0),
        "methodical_consistent": ("kapha", 1.0),
    }
    work = responses.get("work_style", "").lower().replace(" ", "_")
    if work in work_map:
        dosha, weight = work_map[work]
        scores[dosha] += weight

    # Normalize to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 2) for k, v in scores.items()}
    else:
        # Default to balanced if no responses
        scores = {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

    # Ensure exactly 1.0
    adjustment = 1.0 - sum(scores.values())
    scores["kapha"] = round(scores["kapha"] + adjustment, 2)

    return scores


def determine_constitution_type(dosha_baseline: dict[str, float]) -> tuple[str, str]:
    """
    Determine primary dosha and user-facing constitution name.

    Returns (primary_dosha, constitution_name).
    If secondary dosha is within 10% of primary, a combined name is used
    (e.g. "Adaptive-Performance").
    """
    sorted_doshas = sorted(dosha_baseline.items(), key=lambda x: x[1], reverse=True)

    primary = sorted_doshas[0][0]
    primary_score = sorted_doshas[0][1]
    secondary = sorted_doshas[1][0]
    secondary_score = sorted_doshas[1][1]

    primary_name = CONSTITUTION_NAMES[primary]

    # If secondary is within 10% of primary, use combined name
    if abs(primary_score - secondary_score) < 0.1:
        secondary_name = CONSTITUTION_NAMES[secondary]
        return primary, f"{primary_name}-{secondary_name}"

    return primary, primary_name


__all__ = [
    "CONSTITUTION_NAMES",
    "DOSHA_FROM_NAME",
    "compute_dosha_from_quiz",
    "determine_constitution_type",
]
