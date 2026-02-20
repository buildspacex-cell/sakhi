"""Pattern trajectory — tracking how patterns evolve over time.

Pure computation — no DB, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PatternCandidate:
    """A pattern candidate aggregated from occurrences."""

    pattern_type: str
    pattern_value: str
    mention_count: int
    distinct_days: int
    avg_confidence: float
    first_seen: datetime
    last_seen: datetime
    evidence_ids: list[str] = field(default_factory=list)
    evidence_snippets: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CrystallizationResult:
    """Result of a crystallization run."""

    person_id: str
    run_type: str  # daily, weekly, monthly
    window_days: int
    patterns_checked: int
    patterns_crystallized: int
    patterns_updated: int
    patterns_decayed: int
    new_patterns: list[str] = field(default_factory=list)
    updated_patterns: list[str] = field(default_factory=list)


def calculate_trajectory(
    current_mentions: int,
    previous_mentions: int,
    span_days: int,
) -> str:
    """Calculate pattern trajectory based on mention frequency.

    Returns one of: ``'improving'``, ``'worsening'``, ``'stable'``,
    ``'emerging'``, ``'fading'``.
    """
    if previous_mentions == 0:
        return "emerging"

    if current_mentions == 0:
        return "fading"

    current_rate = current_mentions / max(1, span_days)
    previous_rate = previous_mentions / max(1, span_days)

    if current_rate > previous_rate * 1.2:
        return "improving"
    elif current_rate < previous_rate * 0.8:
        return "worsening"
    else:
        return "stable"


__all__ = [
    "PatternCandidate",
    "CrystallizationResult",
    "calculate_trajectory",
]
