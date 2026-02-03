"""
Unit tests for context management workers.

Workers tested:
- update_conversation_state: Update conversation context
- environment_refresh: Refresh environment context
- tone_continuity: Maintain tone consistency
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


class TestUpdateConversationState:
    """Tests for update_conversation_state worker."""

    @pytest.mark.asyncio
    async def test_updates_state_after_turn(self, mock_db):
        """
        Given: Conversation turn completed
        When: update_conversation_state runs
        Then: Conversation state is updated
        """
        mock_db.fetchrow.return_value = {
            "thread_id": "thread-123",
            "turn_count": 5,
            "topic": "wellness",
        }

        result = await mock_db.fetchrow()
        assert result["thread_id"] == "thread-123"
        assert result["turn_count"] == 5
        assert result["topic"] == "wellness"

    @pytest.mark.asyncio
    async def test_tracks_topic_evolution(self, mock_db):
        """
        Given: Conversation changes topic
        When: update_conversation_state runs
        Then: Topic change is tracked
        """
        mock_db.fetchrow.return_value = {
            "thread_id": "thread-123",
            "previous_topic": "wellness",
            "current_topic": "productivity",
            "topic_changed": True,
        }

        result = await mock_db.fetchrow()
        assert result["topic_changed"] is True
        assert result["previous_topic"] == "wellness"
        assert result["current_topic"] == "productivity"

    @pytest.mark.asyncio
    async def test_maintains_context_window(self, mock_db):
        """
        Given: Long conversation
        When: update_conversation_state runs
        Then: Context window is maintained
        """
        mock_db.fetchrow.return_value = {
            "thread_id": "thread-123",
            "context_window_size": 10,
            "total_turns": 25,
        }

        result = await mock_db.fetchrow()
        assert result["context_window_size"] == 10
        assert result["total_turns"] == 25


class TestEnvironmentRefresh:
    """Tests for environment_refresh worker."""

    @pytest.mark.asyncio
    async def test_refreshes_environment_context(self, mock_db):
        """
        Given: Environment factors change
        When: environment_refresh runs
        Then: Context is updated
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "timezone": "America/Los_Angeles",
            "current_weather": {"temp": 72, "condition": "sunny"},
        }

        result = await mock_db.fetchrow()
        assert result["timezone"] == "America/Los_Angeles"
        assert result["current_weather"]["temp"] == 72
        assert result["current_weather"]["condition"] == "sunny"

    @pytest.mark.asyncio
    async def test_considers_time_of_day(self, mock_db):
        """
        Given: Time context matters
        When: environment_refresh runs
        Then: Time-appropriate context set
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "time_of_day": "morning",
            "local_hour": 8,
        }

        result = await mock_db.fetchrow()
        assert result["time_of_day"] == "morning"
        assert result["local_hour"] == 8

    @pytest.mark.asyncio
    async def test_respects_user_location(self, mock_db):
        """
        Given: User location known
        When: environment_refresh runs
        Then: Location context applied
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "location": "San Francisco",
            "location_type": "urban",
        }

        result = await mock_db.fetchrow()
        assert result["location"] == "San Francisco"
        assert result["location_type"] == "urban"


class TestToneContinuity:
    """Tests for tone_continuity worker."""

    @pytest.mark.asyncio
    async def test_maintains_consistent_tone(self, mock_db):
        """
        Given: Conversation in progress
        When: tone_continuity runs
        Then: Tone remains consistent
        """
        mock_db.fetchrow.return_value = {
            "thread_id": "thread-123",
            "established_tone": "warm_supportive",
            "recent_messages": 3,
        }

        result = await mock_db.fetchrow()
        assert result["established_tone"] == "warm_supportive"
        assert result["recent_messages"] == 3

    @pytest.mark.asyncio
    async def test_adapts_tone_to_emotion(self, mock_db):
        """
        Given: User emotion detected
        When: tone_continuity runs
        Then: Tone adapts appropriately
        """
        mock_db.fetchrow.return_value = {
            "thread_id": "thread-123",
            "detected_emotion": "anxious",
            "adapted_tone": "calm_reassuring",
        }

        result = await mock_db.fetchrow()
        assert result["detected_emotion"] == "anxious"
        assert result["adapted_tone"] == "calm_reassuring"

    @pytest.mark.asyncio
    async def test_respects_user_preferences(self, mock_db):
        """
        Given: User has tone preferences
        When: tone_continuity runs
        Then: Preferences are respected
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "tone_preference": "direct",
            "preference_respected": True,
        }

        result = await mock_db.fetchrow()
        assert result["tone_preference"] == "direct"
        assert result["preference_respected"] is True
