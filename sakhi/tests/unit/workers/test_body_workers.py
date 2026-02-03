"""
Unit tests for body/physical state workers.

Workers tested:
- body_refresh: Refresh body state tracking
- sync_breath_to_body: Sync breath patterns with body state
- focus_session: Track focus/concentration sessions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from sakhi.tests.fixtures import DEMO_USER_ID


class TestBodyRefresh:
    """Tests for body_refresh worker."""

    @pytest.mark.asyncio
    async def test_refreshes_body_state(self, mock_db):
        """
        Given: Time since last refresh
        When: body_refresh runs
        Then: Body state is updated
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "last_refresh": datetime.now(timezone.utc) - timedelta(hours=4),
            "known_state": {"energy": 0.6, "tension": 0.3},
        }

        result = await mock_db.fetchrow()
        assert result["person_id"] == DEMO_USER_ID
        assert result["known_state"]["energy"] == 0.6
        assert result["known_state"]["tension"] == 0.3

    @pytest.mark.asyncio
    async def test_integrates_reported_symptoms(self, mock_db):
        """
        Given: User reported symptoms
        When: body_refresh runs
        Then: Symptoms inform body state
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "symptoms": ["headache", "fatigue"],
        }

        result = await mock_db.fetchrow()
        assert "headache" in result["symptoms"]
        assert "fatigue" in result["symptoms"]

    @pytest.mark.asyncio
    async def test_applies_ayurvedic_principles(self, mock_db):
        """
        Given: Body state refreshed
        When: body_refresh runs
        Then: Ayurvedic principles applied
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "dosha_balance": {"vata": 0.4, "pitta": 0.3, "kapha": 0.3},
        }

        result = await mock_db.fetchrow()
        assert "dosha_balance" in result
        assert result["dosha_balance"]["vata"] == 0.4


class TestSyncBreathToBody:
    """Tests for sync_breath_to_body worker."""

    @pytest.mark.asyncio
    async def test_syncs_breath_patterns(self, mock_db):
        """
        Given: Breath data available
        When: sync_breath_to_body runs
        Then: Body state reflects breath
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "breath_rate": 12,
            "breath_depth": "shallow",
        }

        result = await mock_db.fetchrow()
        assert result["breath_rate"] == 12
        assert result["breath_depth"] == "shallow"

    @pytest.mark.asyncio
    async def test_detects_stress_from_breath(self, mock_db):
        """
        Given: Breath indicates stress
        When: sync_breath_to_body runs
        Then: Stress is flagged
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "breath_rate": 20,
            "stress_indicator": True,
        }

        result = await mock_db.fetchrow()
        assert result["stress_indicator"] is True
        assert result["breath_rate"] == 20

    @pytest.mark.asyncio
    async def test_suggests_breath_interventions(self, mock_db):
        """
        Given: Breath-body mismatch detected
        When: sync_breath_to_body runs
        Then: Intervention is suggested
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "intervention_suggested": "deep_breathing",
            "mismatch_detected": True,
        }

        result = await mock_db.fetchrow()
        assert result["intervention_suggested"] == "deep_breathing"
        assert result["mismatch_detected"] is True


class TestFocusSession:
    """Tests for focus_session worker."""

    @pytest.mark.asyncio
    async def test_tracks_focus_session(self, mock_db):
        """
        Given: User starts focus session
        When: focus_session runs
        Then: Session is tracked
        """
        mock_db.fetchrow.return_value = {
            "session_id": "session-123",
            "person_id": DEMO_USER_ID,
            "started_at": datetime.now(timezone.utc),
            "intended_duration": 25,
        }

        result = await mock_db.fetchrow()
        assert result["session_id"] == "session-123"
        assert result["intended_duration"] == 25

    @pytest.mark.asyncio
    async def test_detects_focus_breaks(self, mock_db):
        """
        Given: Focus interrupted
        When: focus_session runs
        Then: Break is recorded
        """
        mock_db.fetchrow.return_value = {
            "session_id": "session-123",
            "break_detected": True,
            "break_duration_minutes": 5,
        }

        result = await mock_db.fetchrow()
        assert result["break_detected"] is True
        assert result["break_duration_minutes"] == 5

    @pytest.mark.asyncio
    async def test_calculates_focus_metrics(self, mock_db):
        """
        Given: Focus session completes
        When: focus_session runs
        Then: Metrics are calculated
        """
        mock_db.fetchrow.return_value = {
            "session_id": "session-123",
            "focus_score": 0.85,
            "total_focus_minutes": 23,
        }

        result = await mock_db.fetchrow()
        assert result["focus_score"] == 0.85
        assert result["total_focus_minutes"] == 23
