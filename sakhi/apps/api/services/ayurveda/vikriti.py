"""
Vikriti Service — Current State & Drift Detection

Vikriti (Sanskrit: "deviation") represents the current state of imbalance
relative to one's constitutional baseline (Prakruti).

Friction Framework Mapping:
- Vata elevated → Chaos Friction (scattered, anxious, overwhelmed)
- Pitta elevated → Intensity Friction (driven, irritable, burning out)
- Kapha elevated → Stagnation Friction (stuck, sluggish, unmotivated)

Drift percentage indicates how far from baseline the person currently is.
Higher drift = greater imbalance = more targeted recommendations needed.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.ayurveda.prakruti import get_prakruti, CONSTITUTION_NAMES

LOGGER = logging.getLogger(__name__)

# Friction state descriptions for user-facing display
FRICTION_STATES = {
    "chaos": {
        "name": "Chaos Friction",
        "dosha": "vata",
        "description": "Your energy is scattered and variable. Mind racing, difficulty focusing, anxiety may be present.",
        "short": "Scattered, anxious, overwhelmed",
        "recommendations_focus": ["grounding", "routine", "warmth", "calming"],
    },
    "intensity": {
        "name": "Intensity Friction",
        "dosha": "pitta",
        "description": "You're running hot - driven but potentially burning out. Irritability, perfectionism, or impatience may show up.",
        "short": "Driven, irritable, burning out",
        "recommendations_focus": ["cooling", "moderation", "play", "surrender"],
    },
    "stagnation": {
        "name": "Stagnation Friction",
        "dosha": "kapha",
        "description": "Energy feels heavy and stuck. Motivation is low, inertia is high, and change feels difficult.",
        "short": "Stuck, sluggish, unmotivated",
        "recommendations_focus": ["stimulation", "movement", "lightness", "novelty"],
    },
    "balanced": {
        "name": "Balanced Flow",
        "dosha": None,
        "description": "You're close to your natural baseline. Energy is sustainable and rhythms are working.",
        "short": "Aligned, sustainable, flowing",
        "recommendations_focus": ["maintenance", "prevention", "optimization"],
    },
}

# Drift thresholds for friction classification
DRIFT_THRESHOLDS = {
    "mild": 15,      # 15%+ drift = mild imbalance
    "moderate": 25,  # 25%+ drift = moderate imbalance
    "significant": 40,  # 40%+ drift = significant imbalance
}


async def compute_current_vikriti(
    person_id: str,
    window_days: int = 7,
) -> Dict[str, Any]:
    """
    Compute current Vikriti (state) from recent episodic data.

    Uses exponential decay weighting: more recent episodes have more weight.

    Args:
        person_id: The person's ID
        window_days: Number of days to look back (default 7)

    Returns:
        Dict with current_dosha, confidence, computed_from, and episode_count
    """
    try:
        rows = await dbfetch(
            """
            SELECT state_vector, created_at
            FROM memory_episodic
            WHERE user_id = $1
              AND state_vector IS NOT NULL
              AND created_at > NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC
            """ % window_days,
            person_id,
        )

        if not rows:
            return {
                "current_dosha": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34},
                "confidence": 0.2,
                "computed_from": f"last_{window_days}_days",
                "episode_count": 0,
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Exponential decay weighting (lambda = 0.5, so half-life ~ 1.4 days)
        decay_lambda = 0.5
        now = datetime.now(timezone.utc)
        weighted_totals = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
        total_weight = 0.0

        for row in rows:
            sv = row.get("state_vector") or {}
            # Handle case where state_vector is stored as JSON string
            if isinstance(sv, str):
                import json
                try:
                    sv = json.loads(sv)
                except json.JSONDecodeError:
                    sv = {}
            dosha = sv.get("dosha") or {}
            created_at = row.get("created_at")

            if not dosha or not created_at:
                continue

            # Calculate days ago and apply exponential decay
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            days_ago = (now - created_at).total_seconds() / 86400
            weight = math.exp(-decay_lambda * days_ago)

            weighted_totals["vata"] += dosha.get("vata", 0.33) * weight
            weighted_totals["pitta"] += dosha.get("pitta", 0.33) * weight
            weighted_totals["kapha"] += dosha.get("kapha", 0.34) * weight
            total_weight += weight

        # Integrate body dosha from body_state_history (HealthKit data)
        # Body dosha scores get 40% weight relative to journal-derived scores
        has_body = False
        try:
            body_rows = await dbfetch(
                """
                SELECT vata_score, pitta_score, kapha_score, computed_at
                FROM body_state_history
                WHERE person_id = $1
                  AND computed_at > NOW() - INTERVAL '%s days'
                  AND vata_score IS NOT NULL
                ORDER BY computed_at DESC
                """ % window_days,
                person_id,
            )
            for brow in (body_rows or []):
                b_vata = brow.get("vata_score")
                b_pitta = brow.get("pitta_score")
                b_kapha = brow.get("kapha_score")
                b_created = brow.get("computed_at")
                if b_vata is None or b_pitta is None or b_kapha is None or not b_created:
                    continue
                if isinstance(b_created, str):
                    b_created = datetime.fromisoformat(b_created.replace("Z", "+00:00"))
                b_days_ago = (now - b_created).total_seconds() / 86400
                b_weight = math.exp(-decay_lambda * b_days_ago) * 0.4  # 40% body weight
                weighted_totals["vata"] += float(b_vata) * b_weight
                weighted_totals["pitta"] += float(b_pitta) * b_weight
                weighted_totals["kapha"] += float(b_kapha) * b_weight
                total_weight += b_weight
                has_body = True
        except Exception as body_exc:
            LOGGER.debug("[Vikriti] body_state_history fetch failed: %s", body_exc)

        if total_weight == 0:
            return {
                "current_dosha": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34},
                "confidence": 0.2,
                "computed_from": f"last_{window_days}_days",
                "episode_count": len(rows),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Normalize
        current_dosha = {
            k: round(v / total_weight, 3) for k, v in weighted_totals.items()
        }

        # Ensure sum to 1.0
        total = sum(current_dosha.values())
        if total > 0:
            current_dosha = {k: round(v / total, 3) for k, v in current_dosha.items()}
        adjustment = 1.0 - sum(current_dosha.values())
        current_dosha["kapha"] = round(current_dosha["kapha"] + adjustment, 3)

        # Confidence based on episode count, recency, and body data availability
        confidence = min(0.9, 0.3 + len(rows) * 0.1)
        if has_body:
            confidence = min(0.95, confidence + 0.15)

        return {
            "current_dosha": current_dosha,
            "confidence": round(confidence, 2),
            "computed_from": f"last_{window_days}_days",
            "episode_count": len(rows),
            "has_body_data": has_body,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        LOGGER.warning(
            "[Vikriti] computation failed",
            extra={"person_id": person_id, "error": str(exc)},
        )
        return {
            "current_dosha": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34},
            "confidence": 0.1,
            "computed_from": f"last_{window_days}_days",
            "episode_count": 0,
            "error": str(exc),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }


def compute_baseline_drift(
    prakruti: Dict[str, Any],
    vikriti: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute drift between constitutional baseline and current state.

    Uses Euclidean distance in 3D dosha space, normalized to percentage.

    Args:
        prakruti: Constitutional baseline with dosha_baseline
        vikriti: Current state with current_dosha

    Returns:
        Dict with drift_percentage, primary_contributor, direction, and raw_distances
    """
    baseline = prakruti.get("dosha_baseline") or {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}
    current = vikriti.get("current_dosha") or {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

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
        primary_contributor = max(elevated, key=elevated.get)
        direction = "elevated"
    else:
        # All doshas depleted or zero — pick largest absolute deviation
        abs_distances = {k: abs(v) for k, v in distances.items()}
        primary_contributor = max(abs_distances, key=abs_distances.get)
        direction = "depleted"

    return {
        "drift_percentage": drift_percentage,
        "primary_contributor": primary_contributor,
        "direction": direction,
        "raw_distances": distances,
        "severity": _classify_severity(drift_percentage),
    }


def _classify_severity(drift_percentage: float) -> str:
    """Classify drift severity."""
    if drift_percentage < DRIFT_THRESHOLDS["mild"]:
        return "minimal"
    elif drift_percentage < DRIFT_THRESHOLDS["moderate"]:
        return "mild"
    elif drift_percentage < DRIFT_THRESHOLDS["significant"]:
        return "moderate"
    else:
        return "significant"


def classify_friction_state(
    drift: Dict[str, Any],
    vikriti: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Map dosha imbalance to Friction Framework state.

    Args:
        drift: Drift data from compute_baseline_drift
        vikriti: Optional current Vikriti for additional context

    Returns:
        Dict with state, name, description, dosha, and severity
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
            primary = max(elevated_doshas, key=elevated_doshas.get)
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


async def get_full_friction_state(person_id: str) -> Dict[str, Any]:
    """
    Get complete friction state for a person.

    Combines Prakruti, Vikriti, drift, and friction classification.
    """
    prakruti = await get_prakruti(person_id)
    if not prakruti:
        # Use default balanced baseline if no Prakruti stored
        prakruti = {
            "type": "Balanced",
            "primary": None,
            "dosha_baseline": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34},
            "source": "default",
        }

    vikriti = await compute_current_vikriti(person_id)
    drift = compute_baseline_drift(prakruti, vikriti)
    friction = classify_friction_state(drift, vikriti)

    return {
        "operating_system": prakruti.get("type"),
        "baseline": prakruti,
        "current_state": vikriti,
        "drift": drift,
        "friction": friction,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


__all__ = [
    "compute_current_vikriti",
    "compute_baseline_drift",
    "classify_friction_state",
    "get_full_friction_state",
    "FRICTION_STATES",
    "DRIFT_THRESHOLDS",
]
