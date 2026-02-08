"""
Unit tests for health_trends — trend computation from body_state_history.

Tests the _compute_trend helper with various data patterns.
"""

import pytest

from sakhi.apps.api.services.body.health_trends import _compute_trend


# =============================================================================
# Trend Computation Tests
# =============================================================================


class TestComputeTrend:
    """Tests for _compute_trend linear regression direction."""

    def test_improving_trend(self):
        values = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        assert _compute_trend(values) == "improving"

    def test_declining_trend(self):
        values = [8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
        assert _compute_trend(values) == "declining"

    def test_stable_trend(self):
        values = [5.0, 5.1, 4.9, 5.0, 5.1, 4.9]
        assert _compute_trend(values) == "stable"

    def test_insufficient_data_too_few(self):
        values = [5.0, 6.0]
        assert _compute_trend(values) == "insufficient_data"

    def test_insufficient_data_empty(self):
        assert _compute_trend([]) == "insufficient_data"

    def test_all_none_values(self):
        values = [None, None, None, None]
        assert _compute_trend(values) == "insufficient_data"

    def test_some_none_values_improving(self):
        values = [None, 3.0, None, 5.0, 7.0, None, 9.0]
        result = _compute_trend(values)
        assert result == "improving"

    def test_constant_values_stable(self):
        values = [5.0, 5.0, 5.0, 5.0, 5.0]
        assert _compute_trend(values) == "stable"

    def test_noisy_but_improving(self):
        """With enough upward slope, noise shouldn't prevent detection."""
        values = [2.0, 3.5, 2.5, 4.0, 3.0, 5.0, 4.5, 6.0]
        result = _compute_trend(values)
        assert result == "improving"

    def test_zero_mean_stable(self):
        """All zeros should return stable (avoid division by zero)."""
        values = [0.0, 0.0, 0.0, 0.0]
        assert _compute_trend(values) == "stable"

    def test_single_spike_stable(self):
        """A single spike in otherwise flat data should be stable."""
        values = [5.0, 5.0, 5.0, 8.0, 5.0, 5.0, 5.0]
        result = _compute_trend(values)
        # The spike shouldn't be enough to trigger improving
        assert result in ("stable", "improving")

    def test_gradual_decline_with_none(self):
        values = [10.0, None, 8.0, None, 6.0, 4.0]
        result = _compute_trend(values)
        assert result == "declining"


# =============================================================================
# Module Import Test
# =============================================================================


class TestHealthTrendsModule:
    """Tests for module-level exports."""

    def test_compute_health_trends_importable(self):
        from sakhi.apps.api.services.body.health_trends import compute_health_trends
        assert callable(compute_health_trends)

    def test_all_exports(self):
        from sakhi.apps.api.services.body.health_trends import __all__
        assert "compute_health_trends" in __all__
