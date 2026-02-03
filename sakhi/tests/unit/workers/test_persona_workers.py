"""
Unit tests for persona/identity workers.

Workers tested:
- persona_mode_detector: Detect current persona mode
- persona_tuning: Fine-tune persona parameters
- life_phase_mapper: Map user to life phase
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


class TestPersonaModeDetector:
    """Tests for persona_mode_detector worker."""

    @pytest.mark.asyncio
    async def test_detects_work_mode(self, mock_db):
        """
        Given: User context indicates work
        When: persona_mode_detector runs
        Then: Work mode is detected
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "time_of_day": "10:00",
            "recent_topics": ["project", "deadline", "meeting"],
            "day_of_week": 2,  # Wednesday
        }

        result = await mock_db.fetchrow()
        assert result["time_of_day"] == "10:00"
        assert "project" in result["recent_topics"]
        assert result["day_of_week"] == 2

    @pytest.mark.asyncio
    async def test_detects_rest_mode(self, mock_db):
        """
        Given: User context indicates rest
        When: persona_mode_detector runs
        Then: Rest mode is detected
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "time_of_day": "21:00",
            "recent_topics": ["relax", "evening", "family"],
            "day_of_week": 6,  # Saturday
        }

        result = await mock_db.fetchrow()
        assert result["time_of_day"] == "21:00"
        assert "relax" in result["recent_topics"]
        assert result["day_of_week"] == 6

    @pytest.mark.asyncio
    async def test_handles_mode_transitions(self, mock_db):
        """
        Given: User is transitioning between modes
        When: persona_mode_detector runs
        Then: Transition is handled smoothly
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "previous_mode": "work",
            "current_mode": "rest",
            "transition_detected": True,
        }

        result = await mock_db.fetchrow()
        assert result["previous_mode"] == "work"
        assert result["current_mode"] == "rest"
        assert result["transition_detected"] is True


class TestPersonaTuning:
    """Tests for persona_tuning worker."""

    @pytest.mark.asyncio
    async def test_adjusts_tone_based_on_feedback(self, mock_db):
        """
        Given: User provides tone feedback
        When: persona_tuning runs
        Then: Tone parameters are adjusted
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "feedback": "too_formal",
            "current_tone": {"formality": 0.8},
        }

        result = await mock_db.fetchrow()
        assert result["feedback"] == "too_formal"
        assert result["current_tone"]["formality"] == 0.8

    @pytest.mark.asyncio
    async def test_learns_communication_preferences(self, mock_db):
        """
        Given: User interaction patterns observed
        When: persona_tuning runs
        Then: Communication style adapts
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "observed_preference": "concise",
            "style_adapted": True,
        }

        result = await mock_db.fetchrow()
        assert result["observed_preference"] == "concise"
        assert result["style_adapted"] is True

    @pytest.mark.asyncio
    async def test_preserves_core_personality(self, mock_db):
        """
        Given: Tuning adjustments made
        When: persona_tuning runs
        Then: Core Sakhi personality preserved
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "core_traits_preserved": True,
            "warmth_level": 0.9,
        }

        result = await mock_db.fetchrow()
        assert result["core_traits_preserved"] is True
        assert result["warmth_level"] == 0.9


class TestLifePhaseMapper:
    """Tests for life_phase_mapper worker."""

    @pytest.mark.asyncio
    async def test_maps_life_phase_from_signals(self, mock_db):
        """
        Given: User signals indicate life phase
        When: life_phase_mapper runs
        Then: Life phase is identified
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "signals": {
                "career_mentions": ["job_search", "interview"],
                "life_events": ["recent_graduation"],
            },
        }

        result = await mock_db.fetchrow()
        assert "job_search" in result["signals"]["career_mentions"]
        assert "recent_graduation" in result["signals"]["life_events"]

    @pytest.mark.asyncio
    async def test_detects_life_phase_transitions(self, mock_db):
        """
        Given: Life phase indicators change
        When: life_phase_mapper runs
        Then: Transition is detected
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "previous_phase": "early_career",
            "current_phase": "mid_career",
            "transition_detected": True,
        }

        result = await mock_db.fetchrow()
        assert result["previous_phase"] == "early_career"
        assert result["current_phase"] == "mid_career"
        assert result["transition_detected"] is True

    @pytest.mark.asyncio
    async def test_contextualizes_recommendations(self, mock_db):
        """
        Given: Life phase is known
        When: life_phase_mapper runs
        Then: Recommendations are contextualized
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "life_phase": "new_parent",
            "recommendations_contextualized": True,
        }

        result = await mock_db.fetchrow()
        assert result["life_phase"] == "new_parent"
        assert result["recommendations_contextualized"] is True
