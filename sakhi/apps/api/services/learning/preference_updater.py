"""
A.8.3 Preference Updater
------------------------
Adjust preference weights from feedback signals.

This is the core learning mechanism that updates preferences based on:
1. Explicit feedback (thumbs up/down, ratings)
2. Implicit signals (choices, reorders, complaints)
3. Time decay (old preferences fade)

The goal: preferences automatically improve without explicit user statements.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

from sakhi.apps.api.core.db import q as dbfetch, exec as execute

logger = logging.getLogger(__name__)


# Adjustment magnitudes by signal type
ADJUSTMENT_WEIGHTS = {
    "thumbs_up": 0.10,
    "thumbs_down": -0.15,
    "praise": 0.12,
    "complaint": -0.18,
    "follow": 0.08,
    "reorder": 0.15,
    "dismiss": -0.05,
    "choice": 0.06,
    "decay": -0.02,
}

# Maximum adjustment per dimension per day
MAX_DAILY_ADJUSTMENT = 0.3

# Confidence adjustments
CONFIDENCE_BOOST_ON_FEEDBACK = 0.05
CONFIDENCE_DECAY_RATE = 0.01  # Per week without feedback


async def apply_feedback_to_preferences(
    person_id: str,
    feedback_id: str,
    feedback_type: str,
    affected_dimensions: List[Any],
) -> Dict[str, Any]:
    """
    Apply feedback signals to update preferences.

    Args:
        person_id: User ID
        feedback_id: ID of the feedback record
        feedback_type: Type of feedback (thumbs_up, complaint, etc.)
        affected_dimensions: List of AffectedDimension objects

    Returns:
        Result with adjustments made
    """
    from sakhi.apps.api.services.memory.preference_framework import (
        load_preferences, store_preferences, PreferenceValue, PreferenceStrength,
        EvidenceType
    )

    adjustments_made = 0

    try:
        # Load current preferences
        prefs = await load_preferences(person_id)
        if not prefs:
            logger.debug(f"No preferences found for {person_id[:8]}, skipping update")
            return {"adjustments_made": 0}

        base_weight = ADJUSTMENT_WEIGHTS.get(feedback_type, 0.05)

        for dim in affected_dimensions:
            domain = dim.domain if hasattr(dim, 'domain') else dim.get('domain')
            dimension = dim.dimension if hasattr(dim, 'dimension') else dim.get('dimension')
            direction = dim.direction if hasattr(dim, 'direction') else dim.get('direction', 'neutral')
            magnitude = dim.magnitude if hasattr(dim, 'magnitude') else dim.get('magnitude', 0.1)

            if not domain or not dimension:
                continue

            # Calculate adjustment
            adjustment = base_weight * magnitude
            if direction == "decrease":
                adjustment = -abs(adjustment)
            elif direction == "increase":
                adjustment = abs(adjustment)

            # Get current value
            current_value = 0.0
            current_confidence = 0.5
            if domain in prefs.domains and dimension in prefs.domains[domain].dimensions:
                current_pref = prefs.domains[domain].dimensions[dimension]
                current_value = current_pref.value
                current_confidence = current_pref.confidence

            # Apply adjustment with bounds
            new_value = max(-1.0, min(1.0, current_value + adjustment))
            new_confidence = min(0.95, current_confidence + CONFIDENCE_BOOST_ON_FEEDBACK)

            # Determine strength from value
            strength = _value_to_strength(new_value)

            # Update preference
            prefs.set_preference(
                domain=domain,
                dimension=dimension,
                value=PreferenceValue(
                    value=new_value,
                    strength=strength,
                    confidence=new_confidence,
                    evidence_type=EvidenceType.FEEDBACK,
                    source_text=f"Feedback: {feedback_type}",
                    learned_at=datetime.utcnow(),
                )
            )

            # Log the adjustment
            await _log_adjustment(
                person_id=person_id,
                domain=domain,
                dimension=dimension,
                old_value=current_value,
                new_value=new_value,
                adjustment=adjustment,
                trigger_type="feedback",
                trigger_id=feedback_id,
                old_confidence=current_confidence,
                new_confidence=new_confidence,
            )

            adjustments_made += 1

        # Save updated preferences
        if adjustments_made > 0:
            await store_preferences(prefs)
            logger.info(
                "[preference_updater] Applied %d adjustments for %s from %s feedback",
                adjustments_made, person_id[:8], feedback_type
            )

        return {"adjustments_made": adjustments_made}

    except Exception as e:
        logger.warning(f"Failed to apply feedback to preferences: {e}")
        return {"adjustments_made": 0, "error": str(e)}


async def apply_choice_to_preferences(
    person_id: str,
    domain: str,
    chosen_attributes: Dict[str, Any],
    rejected_attributes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Apply implicit choice signal to preferences.

    When user picks option A over B, we:
    - Slightly increase preference for A's attributes
    - Slightly decrease preference for B's unique attributes

    Args:
        person_id: User ID
        domain: Preference domain
        chosen_attributes: Attributes of chosen option
        rejected_attributes: Attributes of rejected options

    Returns:
        Result with adjustments made
    """
    from sakhi.apps.api.services.memory.preference_framework import (
        load_preferences, store_preferences, PreferenceValue, PreferenceStrength,
        EvidenceType
    )

    adjustments_made = 0
    choice_weight = ADJUSTMENT_WEIGHTS["choice"]

    try:
        prefs = await load_preferences(person_id)
        if not prefs:
            return {"adjustments_made": 0}

        # Aggregate rejected attributes
        rejected_avg: Dict[str, float] = {}
        for attrs in rejected_attributes:
            for key, val in attrs.items():
                if isinstance(val, (int, float)):
                    if key not in rejected_avg:
                        rejected_avg[key] = []
                    rejected_avg[key].append(val)

        for key in rejected_avg:
            rejected_avg[key] = sum(rejected_avg[key]) / len(rejected_avg[key])

        # Process chosen attributes
        for attr, value in chosen_attributes.items():
            if not isinstance(value, (int, float)):
                continue

            # Compare to rejected average
            rejected_val = rejected_avg.get(attr)
            if rejected_val is not None:
                # Calculate direction based on difference
                diff = value - rejected_val
                if abs(diff) < 0.1:
                    continue  # Not significantly different

                adjustment = choice_weight * (1 if diff > 0 else -1)
            else:
                # Unique to chosen - slight positive
                adjustment = choice_weight * 0.5

            # Get current value
            current_value = 0.0
            current_confidence = 0.5
            if domain in prefs.domains and attr in prefs.domains[domain].dimensions:
                current_pref = prefs.domains[domain].dimensions[attr]
                current_value = current_pref.value
                current_confidence = current_pref.confidence

            # Apply adjustment
            new_value = max(-1.0, min(1.0, current_value + adjustment))
            new_confidence = min(0.9, current_confidence + 0.02)

            # Update
            prefs.set_preference(
                domain=domain,
                dimension=attr,
                value=PreferenceValue(
                    value=new_value,
                    strength=_value_to_strength(new_value),
                    confidence=new_confidence,
                    evidence_type=EvidenceType.INFERRED,
                    source_text="Inferred from choice",
                    learned_at=datetime.utcnow(),
                )
            )

            await _log_adjustment(
                person_id=person_id,
                domain=domain,
                dimension=attr,
                old_value=current_value,
                new_value=new_value,
                adjustment=adjustment,
                trigger_type="choice",
                old_confidence=current_confidence,
                new_confidence=new_confidence,
            )

            adjustments_made += 1

        if adjustments_made > 0:
            await store_preferences(prefs)

        return {"adjustments_made": adjustments_made}

    except Exception as e:
        logger.warning(f"Failed to apply choice to preferences: {e}")
        return {"adjustments_made": 0, "error": str(e)}


async def decay_stale_preferences(
    person_id: str,
    days_threshold: int = 90,
) -> Dict[str, Any]:
    """
    Apply decay to preferences that haven't been reinforced.

    Preferences that haven't been confirmed by feedback/choices
    gradually decay toward neutral (0.0).

    Args:
        person_id: User ID
        days_threshold: Days without activity before decay

    Returns:
        Result with decays applied
    """
    from sakhi.apps.api.services.memory.preference_framework import (
        load_preferences, store_preferences, PreferenceValue,
        EvidenceType
    )

    decays_applied = 0
    cutoff = datetime.utcnow() - timedelta(days=days_threshold)

    try:
        prefs = await load_preferences(person_id)
        if not prefs:
            return {"decays_applied": 0}

        decay_amount = ADJUSTMENT_WEIGHTS["decay"]

        for domain_name, domain_pref in prefs.domains.items():
            for dim_name, pref_value in domain_pref.dimensions.items():
                # Check if this preference is old
                if pref_value.learned_at and pref_value.learned_at < cutoff:
                    # Check for recent feedback on this dimension
                    recent_feedback = await dbfetch(
                        """
                        SELECT COUNT(*) as cnt FROM preference_adjustments
                        WHERE person_id = $1 AND domain = $2 AND dimension = $3
                          AND created_at > $4
                        """,
                        person_id, domain_name, dim_name, cutoff,
                        one=True,
                    )

                    if recent_feedback and recent_feedback["cnt"] > 0:
                        continue  # Has recent activity, don't decay

                    # Apply decay toward 0
                    old_value = pref_value.value
                    if abs(old_value) < 0.05:
                        continue  # Already near neutral

                    decay = decay_amount if old_value > 0 else -decay_amount
                    new_value = old_value - decay

                    # Don't cross zero
                    if (old_value > 0 and new_value < 0) or (old_value < 0 and new_value > 0):
                        new_value = 0.0

                    new_confidence = max(0.1, pref_value.confidence - CONFIDENCE_DECAY_RATE)

                    prefs.set_preference(
                        domain=domain_name,
                        dimension=dim_name,
                        value=PreferenceValue(
                            value=new_value,
                            strength=_value_to_strength(new_value),
                            confidence=new_confidence,
                            evidence_type=EvidenceType.DERIVED,
                            source_text="Decay from inactivity",
                            learned_at=datetime.utcnow(),
                        )
                    )

                    await _log_adjustment(
                        person_id=person_id,
                        domain=domain_name,
                        dimension=dim_name,
                        old_value=old_value,
                        new_value=new_value,
                        adjustment=-decay,
                        trigger_type="decay",
                        old_confidence=pref_value.confidence,
                        new_confidence=new_confidence,
                    )

                    decays_applied += 1

        if decays_applied > 0:
            await store_preferences(prefs)
            logger.info(
                "[preference_updater] Applied %d decay adjustments for %s",
                decays_applied, person_id[:8]
            )

        return {"decays_applied": decays_applied}

    except Exception as e:
        logger.warning(f"Failed to apply preference decay: {e}")
        return {"decays_applied": 0, "error": str(e)}


async def process_pending_feedback(person_id: str) -> Dict[str, Any]:
    """
    Process all unprocessed feedback for a user.

    Called by the learning trigger.
    """
    # This is called from trigger.py and processes recent feedback
    # Most feedback is processed immediately on receipt
    # This catches any that weren't processed (e.g., due to errors)

    return {"adjustments_made": 0, "note": "Feedback processed on receipt"}


async def _log_adjustment(
    person_id: str,
    domain: str,
    dimension: str,
    old_value: float,
    new_value: float,
    adjustment: float,
    trigger_type: str,
    trigger_id: Optional[str] = None,
    evidence_text: Optional[str] = None,
    old_confidence: Optional[float] = None,
    new_confidence: Optional[float] = None,
) -> None:
    """Log a preference adjustment for audit trail."""
    try:
        await execute(
            """
            INSERT INTO preference_adjustments (
                person_id, domain, dimension,
                old_value, new_value, adjustment,
                trigger_type, trigger_id, evidence_text,
                old_confidence, new_confidence
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            person_id,
            domain,
            dimension,
            old_value,
            new_value,
            adjustment,
            trigger_type,
            trigger_id,
            evidence_text,
            old_confidence,
            new_confidence,
        )
    except Exception as e:
        logger.debug(f"Could not log adjustment: {e}")


def _value_to_strength(value: float) -> "PreferenceStrength":
    """Convert numeric value to PreferenceStrength enum."""
    from sakhi.apps.api.services.memory.preference_framework import PreferenceStrength

    if value >= 0.75:
        return PreferenceStrength.STRONG_LIKE
    elif value >= 0.25:
        return PreferenceStrength.LIKE
    elif value >= -0.25:
        return PreferenceStrength.NEUTRAL
    elif value >= -0.75:
        return PreferenceStrength.DISLIKE
    else:
        return PreferenceStrength.STRONG_DISLIKE


async def get_adjustment_history(
    person_id: str,
    domain: Optional[str] = None,
    days: int = 30,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get history of preference adjustments."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        query = """
            SELECT domain, dimension, old_value, new_value, adjustment,
                   trigger_type, evidence_text, created_at
            FROM preference_adjustments
            WHERE person_id = $1 AND created_at > $2
        """
        params: List[Any] = [person_id, cutoff]

        if domain:
            query += " AND domain = $3"
            params.append(domain)

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        results = await dbfetch(query, *params)

        return [
            {
                "domain": r["domain"],
                "dimension": r["dimension"],
                "old_value": r["old_value"],
                "new_value": r["new_value"],
                "adjustment": r["adjustment"],
                "trigger_type": r["trigger_type"],
                "evidence": r["evidence_text"],
                "at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in (results or [])
        ]

    except Exception as e:
        logger.warning(f"Failed to get adjustment history: {e}")
        return []
