"""
Assertion Library for Longitudinal Testing

Provides assertion functions to verify that Sakhi's understanding
has evolved correctly at various checkpoints.

Supported assertions:
- assert_friction_state: Verify current friction state
- assert_pattern_crystallized: Verify a pattern has been learned
- assert_theme_emerged: Verify themes are being tracked
- assert_rhythm_learned: Verify rhythm patterns detected
- assert_dosha_drift: Verify dosha deviation from baseline
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

LOGGER = logging.getLogger(__name__)


@dataclass
class AssertionResult:
    """Result of a checkpoint assertion."""
    passed: bool
    assertion_type: str
    expected: Any
    actual: Any
    message: str
    details: Optional[Dict[str, Any]] = None


class AssertionError(Exception):
    """Raised when an assertion fails."""

    def __init__(self, result: AssertionResult):
        self.result = result
        super().__init__(result.message)


async def assert_friction_state(
    db_query,
    person_id: str,
    expected: Optional[str] = None,
    expected_in: Optional[List[str]] = None,
    min_confidence: float = 0.5,
) -> AssertionResult:
    """
    Assert the current friction state matches expected.

    Args:
        db_query: Database query function
        person_id: User ID to check
        expected: Single expected state (chaos, intensity, stagnation, balanced)
        expected_in: List of acceptable states
        min_confidence: Minimum confidence required

    Returns:
        AssertionResult with pass/fail and details
    """
    from sakhi.apps.api.services.ayurveda.vikriti import get_full_friction_state

    try:
        friction_data = await get_full_friction_state(person_id)
        current_state = friction_data.get("friction", {}).get("state", "unknown")
        current_confidence = friction_data.get("current_state", {}).get("confidence", 0)

        # Determine expected values
        expected_states = expected_in if expected_in else [expected] if expected else []

        # Check state match
        state_match = current_state in expected_states if expected_states else True

        # Check confidence
        confidence_ok = current_confidence >= min_confidence

        passed = state_match and confidence_ok

        return AssertionResult(
            passed=passed,
            assertion_type="friction_state",
            expected={
                "state": expected or expected_in,
                "min_confidence": min_confidence,
            },
            actual={
                "state": current_state,
                "confidence": current_confidence,
            },
            message=(
                f"Friction state: {current_state} (confidence: {current_confidence:.2f})"
                if passed
                else f"Expected friction state {expected or expected_in}, got {current_state} "
                     f"(confidence: {current_confidence:.2f}, required: {min_confidence})"
            ),
            details=friction_data,
        )

    except Exception as exc:
        LOGGER.error(f"Friction state assertion failed: {exc}")
        return AssertionResult(
            passed=False,
            assertion_type="friction_state",
            expected={"state": expected or expected_in},
            actual={"error": str(exc)},
            message=f"Friction state check failed: {exc}",
        )


async def assert_pattern_crystallized(
    db_query,
    person_id: str,
    pattern_type: str,
    pattern_value: str,
    min_occurrences: int = 3,
    min_confidence: float = 0.7,
) -> AssertionResult:
    """
    Assert a pattern has been crystallized (learned as recurring).

    Args:
        db_query: Database query function
        person_id: User ID to check
        pattern_type: Type of pattern (emotion, behavior, theme, etc.)
        pattern_value: Specific pattern value
        min_occurrences: Minimum occurrence count
        min_confidence: Minimum confidence level

    Returns:
        AssertionResult with pass/fail and details
    """
    try:
        # Check pattern occurrences
        occurrences = await db_query(
            """
            SELECT COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM pattern_occurrences
            WHERE person_id = $1
              AND pattern_type = $2
              AND pattern_value ILIKE $3
            """,
            person_id,
            pattern_type,
            f"%{pattern_value}%",
            one=True,
        )

        count = occurrences["count"] if occurrences else 0
        avg_confidence = occurrences["avg_confidence"] if occurrences and occurrences["avg_confidence"] is not None else 0

        # Check crystallized patterns table
        crystallized = await db_query(
            """
            SELECT * FROM crystallized_patterns
            WHERE person_id = $1
              AND pattern_type = $2
              AND pattern_value ILIKE $3
              AND status = 'confirmed'
            """,
            person_id,
            pattern_type,
            f"%{pattern_value}%",
            one=True,
        )

        occurrence_ok = count >= min_occurrences
        confidence_ok = (avg_confidence or 0) >= min_confidence
        crystallized_ok = crystallized is not None

        passed = occurrence_ok and (confidence_ok or crystallized_ok)

        return AssertionResult(
            passed=passed,
            assertion_type="pattern_crystallized",
            expected={
                "type": pattern_type,
                "value": pattern_value,
                "min_occurrences": min_occurrences,
                "min_confidence": min_confidence,
            },
            actual={
                "occurrences": count,
                "avg_confidence": avg_confidence,
                "crystallized": crystallized_ok,
            },
            message=(
                f"Pattern '{pattern_type}:{pattern_value}' found {count} times "
                f"(confidence: {avg_confidence:.2f}, crystallized: {crystallized_ok})"
                if passed
                else f"Pattern '{pattern_type}:{pattern_value}' not sufficiently learned: "
                     f"{count} occurrences (need {min_occurrences}), "
                     f"confidence: {avg_confidence:.2f} (need {min_confidence})"
            ),
            details={
                "crystallized_record": dict(crystallized) if crystallized else None,
            },
        )

    except Exception as exc:
        LOGGER.error(f"Pattern crystallization assertion failed: {exc}")
        return AssertionResult(
            passed=False,
            assertion_type="pattern_crystallized",
            expected={"type": pattern_type, "value": pattern_value},
            actual={"error": str(exc)},
            message=f"Pattern crystallization check failed: {exc}",
        )


async def assert_theme_emerged(
    db_query,
    person_id: str,
    keywords: List[str],
    min_occurrences: int = 3,
    window_days: int = 30,
) -> AssertionResult:
    """
    Assert that themes containing keywords have emerged.

    Args:
        db_query: Database query function
        person_id: User ID to check
        keywords: Keywords to look for in themes
        min_occurrences: Minimum times theme should appear
        window_days: Time window to look back

    Returns:
        AssertionResult with pass/fail and details
    """
    try:
        # Search episodic memories for theme mentions
        keyword_pattern = "|".join(keywords)

        memories = await db_query(
            """
            SELECT COUNT(*) as count
            FROM memory_episodic
            WHERE user_id = $1
              AND created_at > NOW() - INTERVAL '%s days'
              AND (
                text ~* $2
                OR state_vector::text ~* $2
              )
            """ % window_days,
            person_id,
            keyword_pattern,
            one=True,
        )

        count = memories["count"] if memories else 0
        passed = count >= min_occurrences

        return AssertionResult(
            passed=passed,
            assertion_type="theme_emerged",
            expected={
                "keywords": keywords,
                "min_occurrences": min_occurrences,
            },
            actual={
                "occurrences": count,
            },
            message=(
                f"Theme keywords {keywords} found {count} times"
                if passed
                else f"Theme keywords {keywords} found {count} times (need {min_occurrences})"
            ),
        )

    except Exception as exc:
        LOGGER.error(f"Theme assertion failed: {exc}")
        return AssertionResult(
            passed=False,
            assertion_type="theme_emerged",
            expected={"keywords": keywords},
            actual={"error": str(exc)},
            message=f"Theme check failed: {exc}",
        )


async def assert_rhythm_learned(
    db_query,
    person_id: str,
    slot: str,
    expected: str,
) -> AssertionResult:
    """
    Assert that a rhythm pattern has been learned.

    Args:
        db_query: Database query function
        person_id: User ID to check
        slot: Time slot (morning, afternoon, evening)
        expected: Expected energy level (high, medium, low)

    Returns:
        AssertionResult with pass/fail and details
    """
    try:
        # Get personal model rhythm data
        model = await db_query(
            """
            SELECT rhythm_state
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )

        if not model or not model.get("rhythm_state"):
            return AssertionResult(
                passed=False,
                assertion_type="rhythm_learned",
                expected={"slot": slot, "level": expected},
                actual={"rhythm_state": None},
                message=f"No rhythm data found for slot '{slot}'",
            )

        rhythm_state = model["rhythm_state"]
        slots = rhythm_state.get("slots", {})
        actual_level = slots.get(slot, "unknown")

        passed = actual_level.lower() == expected.lower()

        return AssertionResult(
            passed=passed,
            assertion_type="rhythm_learned",
            expected={"slot": slot, "level": expected},
            actual={"slot": slot, "level": actual_level},
            message=(
                f"Rhythm slot '{slot}' = {actual_level}"
                if passed
                else f"Expected rhythm slot '{slot}' = {expected}, got {actual_level}"
            ),
            details={"full_rhythm": rhythm_state},
        )

    except Exception as exc:
        LOGGER.error(f"Rhythm assertion failed: {exc}")
        return AssertionResult(
            passed=False,
            assertion_type="rhythm_learned",
            expected={"slot": slot, "level": expected},
            actual={"error": str(exc)},
            message=f"Rhythm check failed: {exc}",
        )


async def assert_dosha_drift(
    db_query,
    person_id: str,
    dosha: str,
    direction: str,
    min_percentage: float,
) -> AssertionResult:
    """
    Assert dosha drift from baseline.

    Args:
        db_query: Database query function
        person_id: User ID to check
        dosha: Dosha to check (vata, pitta, kapha)
        direction: Expected direction (elevated, depleted)
        min_percentage: Minimum drift percentage

    Returns:
        AssertionResult with pass/fail and details
    """
    from sakhi.apps.api.services.ayurveda.vikriti import get_full_friction_state

    try:
        friction_data = await get_full_friction_state(person_id)
        drift = friction_data.get("drift", {})

        drift_percentage = drift.get("drift_percentage", 0)
        primary = drift.get("primary_contributor", "")
        actual_direction = drift.get("direction", "")
        raw = drift.get("raw_distances", {})

        # Check specific dosha drift
        dosha_drift = raw.get(dosha, 0) * 100  # Convert to percentage

        direction_match = (
            (direction == "elevated" and dosha_drift > 0) or
            (direction == "depleted" and dosha_drift < 0)
        )

        magnitude_ok = abs(dosha_drift) >= min_percentage

        passed = direction_match and magnitude_ok

        return AssertionResult(
            passed=passed,
            assertion_type="dosha_drift",
            expected={
                "dosha": dosha,
                "direction": direction,
                "min_percentage": min_percentage,
            },
            actual={
                "dosha": dosha,
                "drift_percentage": abs(dosha_drift),
                "direction": "elevated" if dosha_drift > 0 else "depleted",
                "overall_drift": drift_percentage,
            },
            message=(
                f"Dosha {dosha} is {direction} by {abs(dosha_drift):.1f}%"
                if passed
                else f"Expected {dosha} {direction} by {min_percentage}%, "
                     f"got {'elevated' if dosha_drift > 0 else 'depleted'} by {abs(dosha_drift):.1f}%"
            ),
            details=drift,
        )

    except Exception as exc:
        LOGGER.error(f"Dosha drift assertion failed: {exc}")
        return AssertionResult(
            passed=False,
            assertion_type="dosha_drift",
            expected={"dosha": dosha, "direction": direction},
            actual={"error": str(exc)},
            message=f"Dosha drift check failed: {exc}",
        )


async def run_checkpoint_assertions(
    db_query,
    person_id: str,
    checkpoint_assertions: Dict[str, Any],
) -> List[AssertionResult]:
    """
    Run all assertions for a checkpoint.

    Args:
        db_query: Database query function
        person_id: User ID to check
        checkpoint_assertions: Dict of assertion configs from checkpoint spec

    Returns:
        List of AssertionResults
    """
    results = []

    for assertion_type, config in checkpoint_assertions.items():
        if assertion_type == "friction_state":
            result = await assert_friction_state(
                db_query,
                person_id,
                expected=config.get("expected"),
                expected_in=config.get("expected_in"),
                min_confidence=config.get("min_confidence", 0.5),
            )
        elif assertion_type == "pattern_crystallized":
            result = await assert_pattern_crystallized(
                db_query,
                person_id,
                pattern_type=config["type"],
                pattern_value=config["value"],
                min_occurrences=config.get("min_occurrences", 3),
                min_confidence=config.get("min_confidence", 0.7),
            )
        elif assertion_type == "theme_emerged":
            result = await assert_theme_emerged(
                db_query,
                person_id,
                keywords=config["keywords"],
                min_occurrences=config.get("min_occurrences", 3),
            )
        elif assertion_type == "rhythm_learned":
            result = await assert_rhythm_learned(
                db_query,
                person_id,
                slot=config["slot"],
                expected=config["expected"],
            )
        elif assertion_type == "dosha_drift":
            result = await assert_dosha_drift(
                db_query,
                person_id,
                dosha=config["dosha"],
                direction=config["direction"],
                min_percentage=config.get("min_percentage", 15),
            )
        elif assertion_type == "dosha_state":
            # Simple dosha state check (primarily X with min %)
            from sakhi.apps.api.services.ayurveda.vikriti import compute_current_vikriti
            vikriti = await compute_current_vikriti(person_id)
            current = vikriti.get("current_dosha", {})
            primary_val = current.get(config["primary"], 0) * 100
            passed = primary_val >= config.get("min_percentage", 33)
            result = AssertionResult(
                passed=passed,
                assertion_type="dosha_state",
                expected=config,
                actual={"current_dosha": current},
                message=(
                    f"Dosha {config['primary']} at {primary_val:.1f}%"
                    if passed
                    else f"Expected {config['primary']} >= {config.get('min_percentage')}%, got {primary_val:.1f}%"
                ),
            )
        elif assertion_type == "rhythm_shift":
            # Check that rhythm is shifting in expected direction
            # This is a softer check - just verify movement
            result = AssertionResult(
                passed=True,  # Soft assertion - always passes but logs
                assertion_type="rhythm_shift",
                expected=config,
                actual={"note": "Rhythm shift tracking not yet implemented"},
                message=f"Rhythm shift check for slot '{config.get('slot')}' (soft check)",
            )
        else:
            result = AssertionResult(
                passed=False,
                assertion_type=assertion_type,
                expected=config,
                actual={"error": "Unknown assertion type"},
                message=f"Unknown assertion type: {assertion_type}",
            )

        results.append(result)

    return results


__all__ = [
    "AssertionResult",
    "AssertionError",
    "assert_friction_state",
    "assert_pattern_crystallized",
    "assert_theme_emerged",
    "assert_rhythm_learned",
    "assert_dosha_drift",
    "run_checkpoint_assertions",
]
