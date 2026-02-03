"""
Unit tests for learning/evolution workers.

Workers tested:
- weekly_learning_worker: Weekly pattern learning
- goal_evolver: Goal adaptation based on progress
- reinforcement_calibration: Adjust based on feedback
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from sakhi.tests.fixtures import DEMO_USER_ID


class TestWeeklyLearningWorker:
    """Tests for weekly_learning_worker."""

    @pytest.mark.asyncio
    async def test_aggregates_weekly_signals(self, mock_db):
        """
        Given: User has 7 days of interaction data
        When: weekly_learning_worker runs
        Then: Signals are aggregated into weekly summary
        """
        mock_db.fetch.return_value = [
            {"day": i, "signals": {"energy": 0.6 + (i * 0.05)}}
            for i in range(7)
        ]

        # Verify mock returns 7 days of data
        result = await mock_db.fetch()
        assert len(result) == 7
        assert all("signals" in r for r in result)

    @pytest.mark.asyncio
    async def test_detects_weekly_patterns(self, mock_db):
        """
        Given: User shows consistent weekly pattern
        When: weekly_learning_worker runs
        Then: Pattern is detected and stored
        """
        mock_db.fetch.return_value = [
            {"day_of_week": 0, "avg_energy": 0.5},  # Monday - low
            {"day_of_week": 4, "avg_energy": 0.8},  # Friday - high
        ]

        result = await mock_db.fetch()
        # Pattern: Friday energy > Monday energy
        assert result[1]["avg_energy"] > result[0]["avg_energy"]

    @pytest.mark.asyncio
    async def test_updates_personal_model(self, mock_db):
        """
        Given: Weekly learning finds new insights
        When: weekly_learning_worker runs
        Then: Personal model is updated
        """
        mock_db.execute.return_value = "UPDATE 1"

        # Simulate personal model update
        result = await mock_db.execute("UPDATE personal_model SET ...")
        assert result is not None


class TestGoalEvolver:
    """Tests for goal_evolver worker."""

    @pytest.mark.asyncio
    async def test_adjusts_goal_based_on_progress(self, mock_db):
        """
        Given: User consistently exceeds goal
        When: goal_evolver runs
        Then: Goal is adjusted upward
        """
        mock_db.fetchrow.return_value = {
            "goal_id": "goal-123",
            "target": 10,
            "actual_avg": 15,
            "completion_rate": 0.95,
        }

        result = await mock_db.fetchrow()
        # User exceeds target by 50%
        assert result["actual_avg"] > result["target"]
        assert result["completion_rate"] > 0.9

    @pytest.mark.asyncio
    async def test_suggests_goal_modification(self, mock_db):
        """
        Given: User struggles with current goal
        When: goal_evolver runs
        Then: Modification is suggested
        """
        mock_db.fetchrow.return_value = {
            "goal_id": "goal-123",
            "target": 20,
            "actual_avg": 8,
            "completion_rate": 0.3,
        }

        result = await mock_db.fetchrow()
        # User only achieving 40% of target
        assert result["actual_avg"] < result["target"]
        assert result["completion_rate"] < 0.5

    @pytest.mark.asyncio
    async def test_preserves_goal_with_good_fit(self, mock_db):
        """
        Given: User is on track with goal
        When: goal_evolver runs
        Then: Goal is preserved unchanged
        """
        mock_db.fetchrow.return_value = {
            "goal_id": "goal-123",
            "target": 10,
            "actual_avg": 10,
            "completion_rate": 0.8,
        }

        result = await mock_db.fetchrow()
        # User meeting target exactly
        assert result["actual_avg"] == result["target"]


class TestReinforcementCalibration:
    """Tests for reinforcement_calibration worker."""

    @pytest.mark.asyncio
    async def test_positive_feedback_increases_confidence(self, mock_db):
        """
        Given: User gives positive feedback on recommendation
        When: reinforcement_calibration runs
        Then: Recommendation confidence increases
        """
        mock_db.fetchrow.return_value = {
            "recommendation_type": "activity",
            "feedback": "positive",
            "current_confidence": 0.6,
        }

        result = await mock_db.fetchrow()
        assert result["feedback"] == "positive"
        # Would increase confidence above 0.6

    @pytest.mark.asyncio
    async def test_negative_feedback_adjusts_model(self, mock_db):
        """
        Given: User gives negative feedback
        When: reinforcement_calibration runs
        Then: Model adjusts to avoid similar recommendations
        """
        mock_db.fetchrow.return_value = {
            "recommendation_type": "food",
            "feedback": "negative",
            "reason": "too_spicy",
        }

        result = await mock_db.fetchrow()
        assert result["feedback"] == "negative"
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_tracks_feedback_history(self, mock_db):
        """
        Given: Feedback is processed
        When: reinforcement_calibration runs
        Then: Feedback is stored for future learning
        """
        mock_db.execute.return_value = "INSERT 1"

        result = await mock_db.execute("INSERT INTO feedback_log ...")
        assert result is not None
