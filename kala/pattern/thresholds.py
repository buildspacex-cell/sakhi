"""Crystallization thresholds — pattern promotion rules.

Patterns must meet evidence thresholds before being promoted to
"crystallized" status.  This prevents single-turn identity modifications
and ensures patterns represent earned understanding.

Each pattern type has different thresholds based on:
- min_mentions: Minimum times the pattern must appear
- window_days: Time window for counting mentions
- min_confidence: Minimum average confidence score
- min_distinct_days: Pattern must appear across multiple days
- requires_consistency: Whether pattern must be consistent (not contradictory)

Pure computation — no DB, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CrystallizationThreshold:
    """Defines when a pattern becomes 'crystallized' (earned)."""

    min_mentions: int
    window_days: int
    min_confidence: float
    min_distinct_days: int = 1
    requires_consistency: bool = False
    decay_rate: float = 0.15
    boost_per_occurrence: float = 0.05


# ---------------------------------------------------------------------------
# Per-type threshold configurations
# ---------------------------------------------------------------------------

CRYSTALLIZATION_THRESHOLDS: dict[str, CrystallizationThreshold] = {
    "core_value": CrystallizationThreshold(
        min_mentions=5,
        window_days=30,
        min_confidence=0.7,
        min_distinct_days=3,
        requires_consistency=True,
        decay_rate=0.10,
        boost_per_occurrence=0.03,
    ),
    "shadow": CrystallizationThreshold(
        min_mentions=3,
        window_days=21,
        min_confidence=0.6,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.12,
        boost_per_occurrence=0.04,
    ),
    "light": CrystallizationThreshold(
        min_mentions=3,
        window_days=21,
        min_confidence=0.6,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.12,
        boost_per_occurrence=0.04,
    ),
    "theme": CrystallizationThreshold(
        min_mentions=5,
        window_days=30,
        min_confidence=0.6,
        min_distinct_days=3,
        requires_consistency=True,
        decay_rate=0.15,
        boost_per_occurrence=0.05,
    ),
    "concern": CrystallizationThreshold(
        min_mentions=3,
        window_days=14,
        min_confidence=0.5,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.20,
        boost_per_occurrence=0.06,
    ),
    "relationship": CrystallizationThreshold(
        min_mentions=4,
        window_days=30,
        min_confidence=0.6,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.10,
        boost_per_occurrence=0.04,
    ),
    "goal": CrystallizationThreshold(
        min_mentions=3,
        window_days=21,
        min_confidence=0.5,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.15,
        boost_per_occurrence=0.05,
    ),
    "trait": CrystallizationThreshold(
        min_mentions=7,
        window_days=60,
        min_confidence=0.75,
        min_distinct_days=5,
        requires_consistency=True,
        decay_rate=0.08,
        boost_per_occurrence=0.02,
    ),
    "contradiction": CrystallizationThreshold(
        min_mentions=2,
        window_days=30,
        min_confidence=0.7,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.25,
        boost_per_occurrence=0.10,
    ),
}


# ---------------------------------------------------------------------------
# Threshold checking
# ---------------------------------------------------------------------------


def check_threshold(
    pattern_type: str,
    mention_count: int,
    distinct_days: int,
    avg_confidence: float,
    span_days: int,
) -> tuple[bool, float, str]:
    """Check if a pattern meets its crystallization threshold.

    Returns ``(threshold_met, final_confidence, reason)``.
    """
    threshold = CRYSTALLIZATION_THRESHOLDS.get(pattern_type)
    if not threshold:
        return False, 0.0, f"Unknown pattern type: {pattern_type}"

    reasons: list[str] = []

    if mention_count < threshold.min_mentions:
        reasons.append(f"mentions ({mention_count}/{threshold.min_mentions})")

    if distinct_days < threshold.min_distinct_days:
        reasons.append(f"distinct_days ({distinct_days}/{threshold.min_distinct_days})")

    if avg_confidence < threshold.min_confidence:
        reasons.append(f"confidence ({avg_confidence:.2f}/{threshold.min_confidence})")

    if reasons:
        return False, avg_confidence, f"Below threshold: {', '.join(reasons)}"

    boost = min(0.25, (mention_count - threshold.min_mentions) * threshold.boost_per_occurrence)
    final_confidence = min(0.95, avg_confidence + boost)

    return True, final_confidence, "Threshold met"


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------


def calculate_decay(
    pattern_type: str,
    weeks_since_last_seen: float,
    current_confidence: float,
) -> float:
    """Calculate decayed confidence for patterns not recently seen.

    Returns the new confidence score after applying exponential decay
    based on the pattern type's decay rate.
    """
    threshold = CRYSTALLIZATION_THRESHOLDS.get(pattern_type)
    if not threshold:
        return current_confidence

    decay = threshold.decay_rate * weeks_since_last_seen
    new_confidence = max(0.0, current_confidence - decay)

    return round(new_confidence, 3)


__all__ = [
    "CrystallizationThreshold",
    "CRYSTALLIZATION_THRESHOLDS",
    "check_threshold",
    "calculate_decay",
]
