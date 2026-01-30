"""
Crystallization Thresholds — Pattern Promotion Rules

Patterns must meet evidence thresholds before being promoted to
"crystallized" status. This prevents single-turn identity modifications
and ensures patterns represent earned understanding.

Each pattern type has different thresholds based on:
- min_mentions: Minimum times the pattern must appear
- window_days: Time window for counting mentions
- min_confidence: Minimum average confidence score
- min_distinct_days: Pattern must appear across multiple days
- requires_consistency: Whether pattern must be consistent (not contradictory)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class CrystallizationThreshold:
    """Defines when a pattern becomes 'crystallized' (earned)."""

    # Minimum mentions before pattern is considered
    min_mentions: int

    # Time window for counting mentions (days)
    window_days: int

    # Minimum average confidence score (0-1)
    min_confidence: float

    # Minimum distinct days the pattern must appear
    min_distinct_days: int = 1

    # Whether pattern requires consistency across mentions
    requires_consistency: bool = False

    # Decay rate per week when pattern stops appearing (0-1)
    decay_rate: float = 0.15

    # Boost per occurrence when pattern continues (+confidence)
    boost_per_occurrence: float = 0.05


# Different thresholds for different pattern types
CRYSTALLIZATION_THRESHOLDS: Dict[str, CrystallizationThreshold] = {
    # Core values: Fundamental principles they live by
    # High threshold - these are identity-defining
    "core_value": CrystallizationThreshold(
        min_mentions=5,
        window_days=30,
        min_confidence=0.7,
        min_distinct_days=3,
        requires_consistency=True,
        decay_rate=0.10,  # Slow decay - values are stable
        boost_per_occurrence=0.03,
    ),

    # Shadow patterns: Inner friction, avoidance, fear
    # Moderate threshold - need confirmation but not too high
    "shadow": CrystallizationThreshold(
        min_mentions=3,
        window_days=21,
        min_confidence=0.6,
        min_distinct_days=2,
        requires_consistency=False,  # Shadows can be inconsistent
        decay_rate=0.12,
        boost_per_occurrence=0.04,
    ),

    # Light patterns: Moments of alignment, clarity, growth
    # Moderate threshold
    "light": CrystallizationThreshold(
        min_mentions=3,
        window_days=21,
        min_confidence=0.6,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.12,
        boost_per_occurrence=0.04,
    ),

    # Themes: Recurring topics in their life
    # Higher threshold for stable themes
    "theme": CrystallizationThreshold(
        min_mentions=5,
        window_days=30,
        min_confidence=0.6,
        min_distinct_days=3,
        requires_consistency=True,
        decay_rate=0.15,
        boost_per_occurrence=0.05,
    ),

    # Concerns: Things they're worried about
    # Lower threshold - concerns can be acute
    "concern": CrystallizationThreshold(
        min_mentions=3,
        window_days=14,
        min_confidence=0.5,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.20,  # Faster decay - concerns resolve
        boost_per_occurrence=0.06,
    ),

    # Relationships: People in their life
    # Moderate threshold
    "relationship": CrystallizationThreshold(
        min_mentions=4,
        window_days=30,
        min_confidence=0.6,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.10,
        boost_per_occurrence=0.04,
    ),

    # Goals: Things they want to achieve
    # Lower threshold - goals can emerge quickly
    "goal": CrystallizationThreshold(
        min_mentions=3,
        window_days=21,
        min_confidence=0.5,
        min_distinct_days=2,
        requires_consistency=False,
        decay_rate=0.15,
        boost_per_occurrence=0.05,
    ),

    # Traits: Stable characteristics
    # High threshold - traits are identity-level
    "trait": CrystallizationThreshold(
        min_mentions=7,
        window_days=60,
        min_confidence=0.75,
        min_distinct_days=5,
        requires_consistency=True,
        decay_rate=0.08,  # Very slow decay
        boost_per_occurrence=0.02,
    ),

    # Contradictions: Conflicting statements
    # Special case - need just 2 contradictory signals
    "contradiction": CrystallizationThreshold(
        min_mentions=2,
        window_days=30,
        min_confidence=0.7,
        min_distinct_days=2,
        requires_consistency=False,  # Contradictions are inherently inconsistent
        decay_rate=0.25,  # Can resolve quickly
        boost_per_occurrence=0.10,
    ),
}


def check_threshold(
    pattern_type: str,
    mention_count: int,
    distinct_days: int,
    avg_confidence: float,
    span_days: int,
) -> tuple[bool, float, str]:
    """
    Check if a pattern meets crystallization threshold.

    Args:
        pattern_type: Type of pattern (core_value, shadow, etc.)
        mention_count: Number of times pattern was detected
        distinct_days: Number of unique days pattern appeared
        avg_confidence: Average confidence across mentions
        span_days: Days between first and last mention

    Returns:
        Tuple of (threshold_met, final_confidence, reason)
    """
    threshold = CRYSTALLIZATION_THRESHOLDS.get(pattern_type)
    if not threshold:
        return False, 0.0, f"Unknown pattern type: {pattern_type}"

    reasons: List[str] = []

    # Check minimum mentions
    if mention_count < threshold.min_mentions:
        reasons.append(f"mentions ({mention_count}/{threshold.min_mentions})")

    # Check distinct days
    if distinct_days < threshold.min_distinct_days:
        reasons.append(f"distinct_days ({distinct_days}/{threshold.min_distinct_days})")

    # Check confidence
    if avg_confidence < threshold.min_confidence:
        reasons.append(f"confidence ({avg_confidence:.2f}/{threshold.min_confidence})")

    # Check window (span must be within window)
    if span_days > threshold.window_days:
        # Pattern spans too long - may need to consider only recent mentions
        # For now, we allow longer spans but note it
        pass

    if reasons:
        return False, avg_confidence, f"Below threshold: {', '.join(reasons)}"

    # Calculate boosted confidence based on evidence strength
    boost = min(0.25, (mention_count - threshold.min_mentions) * threshold.boost_per_occurrence)
    final_confidence = min(0.95, avg_confidence + boost)

    return True, final_confidence, "Threshold met"


def calculate_decay(
    pattern_type: str,
    weeks_since_last_seen: float,
    current_confidence: float,
) -> float:
    """
    Calculate decayed confidence for patterns not recently seen.

    Args:
        pattern_type: Type of pattern
        weeks_since_last_seen: Weeks since last occurrence
        current_confidence: Current confidence score

    Returns:
        New confidence score after decay
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
