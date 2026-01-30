"""
Prakruti Service — Constitutional Type Computation

Prakruti (Sanskrit: "nature") represents the innate constitution a person
is born with. This baseline doesn't change but understanding it helps
interpret current state (Vikriti) deviations.

User-Facing Names (Friction Framework):
- Adaptive (Vata-dominant): Creative, quick-thinking, variable energy
- Performance (Pitta-dominant): Driven, focused, goal-oriented
- Conservation (Kapha-dominant): Steady, grounded, methodical

Combined types use hyphenated names: Adaptive-Performance, Performance-Conservation, etc.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)

# User-facing names mapped to doshas
CONSTITUTION_NAMES = {
    "vata": "Adaptive",
    "pitta": "Performance",
    "kapha": "Conservation",
}

# Reverse mapping
DOSHA_FROM_NAME = {
    "adaptive": "vata",
    "performance": "pitta",
    "conservation": "kapha",
}


def _compute_dosha_from_quiz(responses: Dict[str, Any]) -> Dict[str, float]:
    """
    Map quiz responses to dosha scores.

    Expected response keys (from onboarding quiz):
    - body_type: "light_thin" | "medium_muscular" | "solid_heavy"
    - energy_pattern: "variable_bursts" | "focused_sustained" | "steady_slow"
    - stress_response: "anxious_scattered" | "irritable_intense" | "withdrawn_sluggish"
    - sleep_pattern: "light_variable" | "moderate_efficient" | "deep_heavy"
    - work_style: "creative_multitask" | "goal_driven" | "methodical_consistent"
    """
    scores = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}

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


def _determine_constitution_type(dosha_baseline: Dict[str, float]) -> tuple[str, str]:
    """
    Determine primary and secondary dosha for naming.

    Returns (primary_dosha, constitution_name)
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


async def compute_prakruti_from_onboarding(
    person_id: str,
    responses: Dict[str, Any],
    store: bool = True,
) -> Dict[str, Any]:
    """
    Compute Prakruti (constitutional type) from onboarding quiz responses.

    Args:
        person_id: The person's ID
        responses: Quiz response dictionary
        store: Whether to store in personal_model.operating_system

    Returns:
        Dict with type, primary dosha, dosha_baseline, and source
    """
    dosha_baseline = _compute_dosha_from_quiz(responses)
    primary, constitution_name = _determine_constitution_type(dosha_baseline)

    result = {
        "type": constitution_name,
        "primary": primary,
        "dosha_baseline": dosha_baseline,
        "source": "onboarding_quiz",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    if store:
        try:
            # Store in personal_model.operating_system
            await dbexec(
                """
                UPDATE personal_model
                SET operating_system = $2::jsonb,
                    updated_at = NOW()
                WHERE person_id = $1
                """,
                person_id,
                result,
            )
            LOGGER.info(
                "[Prakruti] stored constitution",
                extra={
                    "person_id": person_id,
                    "type": constitution_name,
                    "primary": primary,
                },
            )
        except Exception as exc:
            LOGGER.warning(
                "[Prakruti] failed to store",
                extra={"person_id": person_id, "error": str(exc)},
            )

    return result


async def get_prakruti(person_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored Prakruti for a person.

    Returns None if not yet computed.
    """
    try:
        row = await dbfetch(
            """
            SELECT operating_system
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
        if row and row.get("operating_system"):
            os_data = row["operating_system"]
            # Handle case where data is stored as JSON string
            if isinstance(os_data, str):
                import json
                try:
                    os_data = json.loads(os_data)
                except json.JSONDecodeError:
                    return None
            return os_data
    except Exception as exc:
        LOGGER.warning(
            "[Prakruti] failed to retrieve",
            extra={"person_id": person_id, "error": str(exc)},
        )
    return None


async def infer_prakruti_from_history(
    person_id: str,
    window_days: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Infer Prakruti from historical episodic data if no onboarding quiz.

    Uses aggregated state_vector patterns over time to estimate baseline.
    This is a fallback for users who skip onboarding.
    """
    try:
        rows = await dbfetch(
            """
            SELECT state_vector
            FROM memory_episodic
            WHERE user_id = $1
              AND state_vector IS NOT NULL
              AND created_at > NOW() - INTERVAL '%s days'
            ORDER BY created_at ASC
            """ % window_days,
            person_id,
        )

        if not rows or len(rows) < 5:
            return None

        # Average the dosha scores across all episodes
        totals = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
        count = 0

        for row in rows:
            sv = row.get("state_vector") or {}
            dosha = sv.get("dosha") or {}
            if dosha:
                totals["vata"] += dosha.get("vata", 0.33)
                totals["pitta"] += dosha.get("pitta", 0.33)
                totals["kapha"] += dosha.get("kapha", 0.34)
                count += 1

        if count == 0:
            return None

        # Average and normalize
        dosha_baseline = {k: round(v / count, 2) for k, v in totals.items()}
        total = sum(dosha_baseline.values())
        if total > 0:
            dosha_baseline = {k: round(v / total, 2) for k, v in dosha_baseline.items()}

        primary, constitution_name = _determine_constitution_type(dosha_baseline)

        return {
            "type": constitution_name,
            "primary": primary,
            "dosha_baseline": dosha_baseline,
            "source": "inferred_from_history",
            "episode_count": count,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        LOGGER.warning(
            "[Prakruti] inference failed",
            extra={"person_id": person_id, "error": str(exc)},
        )
        return None


__all__ = [
    "compute_prakruti_from_onboarding",
    "get_prakruti",
    "infer_prakruti_from_history",
    "CONSTITUTION_NAMES",
    "DOSHA_FROM_NAME",
]
