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

Pure drift/friction math lives in ``kala.state.drift``.
This module adds DB-backed vikriti computation + orchestration.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict

# Re-export pure computation from kala (single source of truth)
from kala.state.drift import (  # noqa: F401
    DRIFT_THRESHOLDS,
    FRICTION_STATES,
    classify_friction_state,
    compute_baseline_drift,
)
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.ayurveda.prakruti import get_prakruti

LOGGER = logging.getLogger(__name__)


async def compute_current_vikriti(
    person_id: str,
    window_days: int = 7,
    reference_time: datetime | None = None,
) -> Dict[str, Any]:
    """
    Compute current Vikriti (state) from recent episodic data.

    Uses exponential decay weighting: more recent episodes have more weight.

    Args:
        person_id: The person's ID
        window_days: Number of days to look back (default 7)
        reference_time: Optional anchor time for window queries (defaults to now).
                        Pass a simulated timestamp for backdated data.

    Returns:
        Dict with current_dosha, confidence, computed_from, and episode_count
    """
    now = reference_time or datetime.now(timezone.utc)
    try:
        rows = await dbfetch(
            """
            SELECT state_vector, created_at
            FROM memory_episodic
            WHERE user_id = $1
              AND state_vector IS NOT NULL
              AND created_at > $2::timestamptz - INTERVAL '%s days'
            ORDER BY created_at DESC
            """ % window_days,
            person_id,
            now,
        )

        if not rows:
            return {
                "current_dosha": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34},
                "confidence": 0.2,
                "computed_from": f"last_{window_days}_days",
                "episode_count": 0,
                "computed_at": now.isoformat(),
            }

        # Exponential decay weighting (lambda = 0.5, so half-life ~ 1.4 days)
        decay_lambda = 0.5
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
                  AND computed_at > $2::timestamptz - INTERVAL '%s days'
                  AND vata_score IS NOT NULL
                ORDER BY computed_at DESC
                """ % window_days,
                person_id,
                now,
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
                "computed_at": now.isoformat(),
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
            "computed_at": now.isoformat(),
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
            "computed_at": now.isoformat(),
        }


async def get_full_friction_state(
    person_id: str,
    reference_time: datetime | None = None,
) -> Dict[str, Any]:
    """
    Get complete friction state for a person.

    Combines Prakruti, Vikriti, drift, and friction classification.

    Args:
        reference_time: Optional anchor for window queries (defaults to now).
    """
    now = reference_time or datetime.now(timezone.utc)
    prakruti = await get_prakruti(person_id)
    if not prakruti:
        # Use default balanced baseline if no Prakruti stored
        prakruti = {
            "type": "Balanced",
            "primary": None,
            "dosha_baseline": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34},
            "source": "default",
        }

    vikriti = await compute_current_vikriti(person_id, reference_time=now)
    drift = compute_baseline_drift(prakruti, vikriti)
    friction = classify_friction_state(drift, vikriti)

    return {
        "operating_system": prakruti.get("type"),
        "baseline": prakruti,
        "current_state": vikriti,
        "drift": drift,
        "friction": friction,
        "computed_at": now.isoformat(),
    }


__all__ = [
    "compute_current_vikriti",
    "compute_baseline_drift",
    "classify_friction_state",
    "get_full_friction_state",
    "FRICTION_STATES",
    "DRIFT_THRESHOLDS",
]
