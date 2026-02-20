"""Pattern crystallization — temporal pattern lifecycle management."""

from kala.pattern.thresholds import (
    CRYSTALLIZATION_THRESHOLDS,
    CrystallizationThreshold,
    calculate_decay,
    check_threshold,
)
from kala.pattern.trajectory import (
    CrystallizationResult,
    PatternCandidate,
    calculate_trajectory,
)

__all__ = [
    "CRYSTALLIZATION_THRESHOLDS",
    "CrystallizationResult",
    "CrystallizationThreshold",
    "PatternCandidate",
    "calculate_decay",
    "calculate_trajectory",
    "check_threshold",
]
