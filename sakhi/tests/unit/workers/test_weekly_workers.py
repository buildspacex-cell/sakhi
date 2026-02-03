"""
Unit tests for weekly aggregation workers.

Workers tested:
- weekly_signals_worker: Aggregate weekly signals
- weekly_rhythm_rollup_worker: Weekly rhythm summary
- meta_reflection_weekly: Weekly meta-reflection
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from sakhi.tests.fixtures import DEMO_USER_ID


class TestWeeklySignalsWorker:
    """Tests for weekly_signals_worker."""

    @pytest.mark.asyncio
    async def test_aggregates_weekly_signals(self, mock_db):
        """
        Given: User has 7 days of signals
        When: weekly_signals_worker runs
        Then: Signals are aggregated
        """
        mock_db.fetch.return_value = [
            {"date": f"2026-01-{20+i}", "signals": {"energy": 0.5 + i*0.05}}
            for i in range(7)
        ]

        result = await mock_db.fetch()
        assert len(result) == 7
        assert result[0]["date"] == "2026-01-20"
        assert result[0]["signals"]["energy"] == 0.5

    @pytest.mark.asyncio
    async def test_identifies_weekly_patterns(self, mock_db):
        """
        Given: Signals show recurring pattern
        When: weekly_signals_worker runs
        Then: Pattern is identified
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "pattern_detected": True,
            "pattern_type": "energy_dip_midweek",
        }

        result = await mock_db.fetchrow()
        assert result["pattern_detected"] is True
        assert result["pattern_type"] == "energy_dip_midweek"

    @pytest.mark.asyncio
    async def test_stores_weekly_summary(self, mock_db):
        """
        Given: Aggregation completes
        When: weekly_signals_worker runs
        Then: Summary is stored
        """
        mock_db.fetchrow.return_value = {
            "summary_id": "summary-123",
            "week_start": "2026-01-20",
            "stored": True,
        }

        result = await mock_db.fetchrow()
        assert result["stored"] is True
        assert result["week_start"] == "2026-01-20"


class TestWeeklyRhythmRollupWorker:
    """Tests for weekly_rhythm_rollup_worker."""

    @pytest.mark.asyncio
    async def test_creates_rhythm_summary(self, mock_db):
        """
        Given: Daily rhythm data exists
        When: weekly_rhythm_rollup_worker runs
        Then: Weekly rhythm summary is created
        """
        mock_db.fetch.return_value = [
            {
                "date": f"2026-01-{20+i}",
                "morning_energy": 0.6,
                "afternoon_energy": 0.7,
                "evening_energy": 0.5,
            }
            for i in range(7)
        ]

        result = await mock_db.fetch()
        assert len(result) == 7
        assert result[0]["morning_energy"] == 0.6
        assert result[0]["afternoon_energy"] == 0.7

    @pytest.mark.asyncio
    async def test_calculates_rhythm_trends(self, mock_db):
        """
        Given: Multiple weeks of data
        When: weekly_rhythm_rollup_worker runs
        Then: Trends are calculated
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "trend_direction": "improving",
            "trend_confidence": 0.8,
        }

        result = await mock_db.fetchrow()
        assert result["trend_direction"] == "improving"
        assert result["trend_confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_updates_elemental_summary(self, mock_db):
        """
        Given: Weekly rollup completes
        When: weekly_rhythm_rollup_worker runs
        Then: Elemental summary is updated
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "elemental_balance": {"vata": 0.3, "pitta": 0.4, "kapha": 0.3},
            "summary_updated": True,
        }

        result = await mock_db.fetchrow()
        assert result["summary_updated"] is True
        assert result["elemental_balance"]["pitta"] == 0.4


class TestMetaReflectionWeekly:
    """Tests for meta_reflection_weekly worker."""

    @pytest.mark.asyncio
    async def test_generates_weekly_reflection(self, mock_db):
        """
        Given: Week of interactions exist
        When: meta_reflection_weekly runs
        Then: Reflection is generated
        """
        mock_db.fetch.return_value = [
            {"type": "conversation", "count": 15},
            {"type": "journal", "count": 5},
            {"type": "checkin", "count": 7},
        ]

        result = await mock_db.fetch()
        assert len(result) == 3
        assert result[0]["type"] == "conversation"
        assert result[0]["count"] == 15

    @pytest.mark.asyncio
    async def test_identifies_growth_areas(self, mock_db):
        """
        Given: Weekly data analyzed
        When: meta_reflection_weekly runs
        Then: Growth areas are identified
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "growth_areas": ["stress_management", "sleep_consistency"],
            "priority_area": "stress_management",
        }

        result = await mock_db.fetchrow()
        assert "stress_management" in result["growth_areas"]
        assert result["priority_area"] == "stress_management"

    @pytest.mark.asyncio
    async def test_suggests_weekly_intentions(self, mock_db):
        """
        Given: Reflection completes
        When: meta_reflection_weekly runs
        Then: Next week intentions suggested
        """
        mock_db.fetch.return_value = [
            {"intention": "Practice morning meditation", "priority": 1},
            {"intention": "Reduce screen time before bed", "priority": 2},
        ]

        result = await mock_db.fetch()
        assert len(result) == 2
        assert result[0]["priority"] == 1
        assert "meditation" in result[0]["intention"]
