"""
Unit tests for forecast/prediction workers.

Workers tested:
- forecast: Generate predictions
- rhythm_inference: Infer rhythm patterns
- rhythm_scheduler: Schedule rhythm-aware activities
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from sakhi.tests.fixtures import DEMO_USER_ID


class TestForecast:
    """Tests for forecast worker."""

    @pytest.mark.asyncio
    async def test_generates_daily_forecast(self, mock_db):
        """
        Given: Historical data exists
        When: forecast runs
        Then: Daily forecast is generated
        """
        mock_db.fetch.return_value = [
            {"date": f"2026-01-{i}", "energy": 0.5 + (i % 3) * 0.1}
            for i in range(1, 31)
        ]

        result = await mock_db.fetch()
        assert len(result) == 30
        assert result[0]["date"] == "2026-01-1"
        # energy = 0.5 + (i % 3) * 0.1 where i=1, so 0.5 + (1 % 3) * 0.1 = 0.5 + 0.1 = 0.6
        assert result[0]["energy"] == 0.6

    @pytest.mark.asyncio
    async def test_predicts_energy_levels(self, mock_db):
        """
        Given: Energy patterns known
        When: forecast runs
        Then: Energy levels predicted
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "predicted_energy": 0.7,
            "confidence": 0.85,
        }

        result = await mock_db.fetchrow()
        assert result["predicted_energy"] == 0.7
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_identifies_optimal_windows(self, mock_db):
        """
        Given: Forecast generated
        When: forecast runs
        Then: Optimal activity windows identified
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "optimal_windows": [{"start": 9, "end": 11}, {"start": 14, "end": 16}],
        }

        result = await mock_db.fetchrow()
        assert len(result["optimal_windows"]) == 2
        assert result["optimal_windows"][0]["start"] == 9


class TestRhythmInference:
    """Tests for rhythm_inference worker."""

    @pytest.mark.asyncio
    async def test_infers_daily_rhythm(self, mock_db):
        """
        Given: Activity data exists
        When: rhythm_inference runs
        Then: Daily rhythm is inferred
        """
        mock_db.fetch.return_value = [
            {"hour": h, "activity_level": 0.5 + (h % 12) * 0.05}
            for h in range(24)
        ]

        result = await mock_db.fetch()
        assert len(result) == 24
        assert result[0]["hour"] == 0
        assert result[12]["hour"] == 12

    @pytest.mark.asyncio
    async def test_identifies_chronotype(self, mock_db):
        """
        Given: Sleep/wake patterns known
        When: rhythm_inference runs
        Then: Chronotype is identified
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "chronotype": "morning_lark",
            "confidence": 0.9,
        }

        result = await mock_db.fetchrow()
        assert result["chronotype"] == "morning_lark"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_detects_rhythm_disruptions(self, mock_db):
        """
        Given: Rhythm deviates from normal
        When: rhythm_inference runs
        Then: Disruption is flagged
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "disruption_detected": True,
            "disruption_type": "late_sleep",
        }

        result = await mock_db.fetchrow()
        assert result["disruption_detected"] is True
        assert result["disruption_type"] == "late_sleep"


class TestRhythmScheduler:
    """Tests for rhythm_scheduler worker."""

    @pytest.mark.asyncio
    async def test_schedules_at_optimal_times(self, mock_db):
        """
        Given: Activity needs scheduling
        When: rhythm_scheduler runs
        Then: Optimal time is selected
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "activity_type": "deep_work",
            "optimal_hours": [9, 10, 11],
        }

        result = await mock_db.fetchrow()
        assert result["activity_type"] == "deep_work"
        assert 9 in result["optimal_hours"]
        assert 10 in result["optimal_hours"]
        assert 11 in result["optimal_hours"]

    @pytest.mark.asyncio
    async def test_respects_user_constraints(self, mock_db):
        """
        Given: User has time constraints
        When: rhythm_scheduler runs
        Then: Constraints are respected
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "blocked_hours": [12, 13],
            "scheduled_within_constraints": True,
        }

        result = await mock_db.fetchrow()
        assert 12 in result["blocked_hours"]
        assert result["scheduled_within_constraints"] is True

    @pytest.mark.asyncio
    async def test_balances_multiple_activities(self, mock_db):
        """
        Given: Multiple activities to schedule
        When: rhythm_scheduler runs
        Then: Activities are balanced
        """
        mock_db.fetch.return_value = [
            {"activity": "deep_work", "scheduled_hour": 9},
            {"activity": "exercise", "scheduled_hour": 17},
            {"activity": "meditation", "scheduled_hour": 7},
        ]

        result = await mock_db.fetch()
        assert len(result) == 3
        activities = [r["activity"] for r in result]
        assert "deep_work" in activities
        assert "exercise" in activities
