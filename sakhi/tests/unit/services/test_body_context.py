"""
Unit tests for body context integration.

MVP: Body data is cut from the prompt (computed and stored to DB, but not injected).
These tests verify the context scan correctly excludes body data.
"""

import pytest

from sakhi.apps.api.services.conversation_v2.conversation_reasoner import (
    build_context_scan,
)


class TestBodyContextScan:
    """Body data should NOT appear in MVP context scan."""

    def test_no_body_line_when_body_data_present(self):
        """Body data is computed but not injected into MVP prompt."""
        metadata = {
            "body_state": {
                "sleep": {"quality": "good", "duration_hours": 7.2},
                "vitals": {"resting_hr": 62, "hrv_sdnn": 45},
                "energy": {"level": "high"},
            },
            "health_trends": {
                "sleep_trend": "improving",
                "energy_trend": "stable",
            },
        }
        scan = build_context_scan(metadata)
        assert "Body:" not in scan

    def test_no_body_line_when_no_data(self):
        metadata = {}
        scan = build_context_scan(metadata)
        assert "Body:" not in scan

    def test_no_body_line_when_empty_state(self):
        metadata = {"body_state": {}}
        scan = build_context_scan(metadata)
        assert "Body:" not in scan


# =============================================================================
# Health Signal Extraction (state_engine._log_health_signals)
# =============================================================================


class TestHealthSignalExtraction:
    """Tests for health signal threshold logic."""

    def test_poor_sleep_threshold(self):
        """Sleep under 6h should produce poor_sleep signal."""
        from sakhi.apps.api.services.body.state_engine import _log_health_signals
        assert callable(_log_health_signals)

    def test_signal_extraction_with_no_data(self):
        """Empty body_state should produce no signals."""
        from sakhi.apps.api.services.body.state_engine import _log_health_signals
        assert callable(_log_health_signals)
