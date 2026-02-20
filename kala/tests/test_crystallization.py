"""Tests for kala.pattern — crystallization thresholds, decay, and trajectory."""

from __future__ import annotations

from datetime import datetime, timezone

from kala.pattern.thresholds import (
    CRYSTALLIZATION_THRESHOLDS,
    calculate_decay,
    check_threshold,
)
from kala.pattern.trajectory import (
    CrystallizationResult,
    PatternCandidate,
    calculate_trajectory,
)

# ---------------------------------------------------------------------------
# check_threshold
# ---------------------------------------------------------------------------


class TestCheckThreshold:
    def test_core_value_meets_threshold(self) -> None:
        met, conf, reason = check_threshold(
            pattern_type="core_value",
            mention_count=6,
            distinct_days=4,
            avg_confidence=0.8,
            span_days=25,
        )
        assert met is True
        assert conf >= 0.8
        assert reason == "Threshold met"

    def test_core_value_below_mentions(self) -> None:
        met, conf, reason = check_threshold(
            pattern_type="core_value",
            mention_count=2,
            distinct_days=2,
            avg_confidence=0.8,
            span_days=10,
        )
        assert met is False
        assert "mentions" in reason

    def test_core_value_below_confidence(self) -> None:
        met, conf, reason = check_threshold(
            pattern_type="core_value",
            mention_count=5,
            distinct_days=3,
            avg_confidence=0.5,
            span_days=20,
        )
        assert met is False
        assert "confidence" in reason

    def test_core_value_below_distinct_days(self) -> None:
        met, conf, reason = check_threshold(
            pattern_type="core_value",
            mention_count=5,
            distinct_days=1,
            avg_confidence=0.8,
            span_days=20,
        )
        assert met is False
        assert "distinct_days" in reason

    def test_shadow_meets_threshold(self) -> None:
        met, conf, _ = check_threshold(
            pattern_type="shadow",
            mention_count=3,
            distinct_days=2,
            avg_confidence=0.7,
            span_days=14,
        )
        assert met is True

    def test_concern_lower_threshold(self) -> None:
        met, conf, _ = check_threshold(
            pattern_type="concern",
            mention_count=3,
            distinct_days=2,
            avg_confidence=0.5,
            span_days=10,
        )
        assert met is True

    def test_trait_high_threshold(self) -> None:
        met, _, reason = check_threshold(
            pattern_type="trait",
            mention_count=5,
            distinct_days=3,
            avg_confidence=0.8,
            span_days=40,
        )
        assert met is False  # Needs 7 mentions and 5 distinct days

    def test_unknown_pattern_type(self) -> None:
        met, conf, reason = check_threshold(
            pattern_type="nonexistent",
            mention_count=100,
            distinct_days=100,
            avg_confidence=1.0,
            span_days=1,
        )
        assert met is False
        assert "Unknown" in reason

    def test_confidence_boost_with_excess_mentions(self) -> None:
        """Extra mentions beyond threshold boost confidence."""
        met, conf, _ = check_threshold(
            pattern_type="core_value",
            mention_count=10,  # 5 more than minimum
            distinct_days=5,
            avg_confidence=0.75,
            span_days=25,
        )
        assert met is True
        assert conf > 0.75  # Boosted

    def test_confidence_capped_at_95(self) -> None:
        met, conf, _ = check_threshold(
            pattern_type="contradiction",
            mention_count=100,
            distinct_days=50,
            avg_confidence=0.95,
            span_days=25,
        )
        assert met is True
        assert conf <= 0.95

    def test_all_pattern_types_have_thresholds(self) -> None:
        for ptype in CRYSTALLIZATION_THRESHOLDS:
            met, conf, reason = check_threshold(
                pattern_type=ptype,
                mention_count=100,
                distinct_days=100,
                avg_confidence=0.95,
                span_days=5,
            )
            assert met is True, f"{ptype} should meet threshold with high values"


# ---------------------------------------------------------------------------
# calculate_decay
# ---------------------------------------------------------------------------


class TestCalculateDecay:
    def test_one_week_decay(self) -> None:
        result = calculate_decay("core_value", 1.0, 0.8)
        # core_value decay_rate = 0.10 → 0.8 - 0.10*1 = 0.70
        assert result == 0.7

    def test_two_week_decay(self) -> None:
        result = calculate_decay("core_value", 2.0, 0.8)
        assert result == 0.6

    def test_no_decay_at_zero_weeks(self) -> None:
        result = calculate_decay("core_value", 0.0, 0.8)
        assert result == 0.8

    def test_concern_faster_decay(self) -> None:
        # concern decay_rate = 0.20
        result = calculate_decay("concern", 2.0, 0.8)
        assert result == 0.4

    def test_trait_slow_decay(self) -> None:
        # trait decay_rate = 0.08
        result = calculate_decay("trait", 1.0, 0.8)
        assert result == 0.72

    def test_decay_floors_at_zero(self) -> None:
        result = calculate_decay("concern", 100.0, 0.5)
        assert result == 0.0

    def test_unknown_type_no_change(self) -> None:
        result = calculate_decay("nonexistent", 5.0, 0.8)
        assert result == 0.8


# ---------------------------------------------------------------------------
# calculate_trajectory
# ---------------------------------------------------------------------------


class TestCalculateTrajectory:
    def test_emerging(self) -> None:
        assert calculate_trajectory(5, 0, 10) == "emerging"

    def test_fading(self) -> None:
        assert calculate_trajectory(0, 5, 10) == "fading"

    def test_improving(self) -> None:
        assert calculate_trajectory(10, 5, 10) == "improving"

    def test_worsening(self) -> None:
        assert calculate_trajectory(3, 10, 10) == "worsening"

    def test_stable(self) -> None:
        assert calculate_trajectory(5, 5, 10) == "stable"

    def test_zero_span_days(self) -> None:
        # Should not divide by zero
        result = calculate_trajectory(5, 3, 0)
        assert result in ("improving", "worsening", "stable", "emerging", "fading")


# ---------------------------------------------------------------------------
# Dataclass constructors
# ---------------------------------------------------------------------------


class TestDataclasses:
    def test_pattern_candidate(self) -> None:
        pc = PatternCandidate(
            pattern_type="core_value",
            pattern_value="resilience",
            mention_count=5,
            distinct_days=3,
            avg_confidence=0.8,
            first_seen=datetime(2025, 1, 1, tzinfo=timezone.utc),
            last_seen=datetime(2025, 1, 20, tzinfo=timezone.utc),
        )
        assert pc.pattern_type == "core_value"
        assert pc.evidence_ids == []

    def test_crystallization_result(self) -> None:
        cr = CrystallizationResult(
            person_id="test-user",
            run_type="daily",
            window_days=14,
            patterns_checked=10,
            patterns_crystallized=3,
            patterns_updated=2,
            patterns_decayed=1,
        )
        assert cr.new_patterns == []
        assert cr.patterns_crystallized == 3
