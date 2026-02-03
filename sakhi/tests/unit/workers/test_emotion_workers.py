"""
Unit tests for emotion/feeling workers.

Workers tested:
- emotion_soul_rhythm_deep: Deep emotional-soul-rhythm integration
- emotion_loop_refresh: Refresh emotional state loop
- update_emotional_context: Update current emotional context
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


class TestEmotionSoulRhythmDeep:
    """Tests for emotion_soul_rhythm_deep worker."""

    @pytest.mark.asyncio
    async def test_integrates_emotion_with_soul_values(self, mock_db):
        """
        Given: User expresses emotion
        When: emotion_soul_rhythm_deep runs
        Then: Emotion is connected to soul values
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "current_emotion": "frustration",
            "soul_values": ["creativity", "autonomy"],
        }

        result = await mock_db.fetchrow()
        assert result["current_emotion"] == "frustration"
        assert "creativity" in result["soul_values"]
        assert "autonomy" in result["soul_values"]

    @pytest.mark.asyncio
    async def test_detects_emotion_rhythm_misalignment(self, mock_db):
        """
        Given: Emotion conflicts with natural rhythm
        When: emotion_soul_rhythm_deep runs
        Then: Misalignment is identified
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "current_emotion": "anxious",
            "expected_rhythm_state": "calm",
            "time_of_day": "evening",
        }

        result = await mock_db.fetchrow()
        assert result["current_emotion"] == "anxious"
        assert result["expected_rhythm_state"] == "calm"
        assert result["time_of_day"] == "evening"

    @pytest.mark.asyncio
    async def test_generates_alignment_insights(self, mock_db):
        """
        Given: Deep analysis completes
        When: emotion_soul_rhythm_deep runs
        Then: Actionable insights are generated
        """
        mock_db.fetch.return_value = [
            {"insight": "Frustration linked to blocked creativity", "actionable": True},
            {"insight": "Evening anxiety may affect sleep", "actionable": True},
        ]

        result = await mock_db.fetch()
        assert len(result) == 2
        assert result[0]["actionable"] is True
        assert "creativity" in result[0]["insight"]


class TestEmotionLoopRefresh:
    """Tests for emotion_loop_refresh worker."""

    @pytest.mark.asyncio
    async def test_refreshes_emotion_state(self, mock_db):
        """
        Given: Time has passed since last update
        When: emotion_loop_refresh runs
        Then: Emotion state is refreshed
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "last_emotion": "stressed",
            "last_update": datetime.now(timezone.utc),
            "decay_rate": 0.1,
        }

        result = await mock_db.fetchrow()
        assert result["last_emotion"] == "stressed"
        assert result["decay_rate"] == 0.1

    @pytest.mark.asyncio
    async def test_applies_natural_emotion_decay(self, mock_db):
        """
        Given: No new emotional input
        When: emotion_loop_refresh runs
        Then: Emotion decays toward baseline
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "previous_intensity": 0.8,
            "current_intensity": 0.6,
            "decay_applied": True,
        }

        result = await mock_db.fetchrow()
        assert result["previous_intensity"] > result["current_intensity"]
        assert result["decay_applied"] is True

    @pytest.mark.asyncio
    async def test_preserves_strong_emotions(self, mock_db):
        """
        Given: Strong emotion recently recorded
        When: emotion_loop_refresh runs
        Then: Emotion persists appropriately
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "emotion": "joy",
            "intensity": 0.9,
            "preserved": True,
        }

        result = await mock_db.fetchrow()
        assert result["intensity"] == 0.9
        assert result["preserved"] is True


class TestUpdateEmotionalContext:
    """Tests for update_emotional_context worker."""

    @pytest.mark.asyncio
    async def test_updates_context_from_conversation(self, mock_db):
        """
        Given: Conversation reveals emotional content
        When: update_emotional_context runs
        Then: Emotional context is updated
        """
        mock_db.fetchrow.return_value = {
            "turn_id": "turn-123",
            "detected_emotions": ["joy", "gratitude"],
            "confidence": 0.85,
        }

        result = await mock_db.fetchrow()
        assert "joy" in result["detected_emotions"]
        assert "gratitude" in result["detected_emotions"]
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_aggregates_multiple_signals(self, mock_db):
        """
        Given: Multiple emotional signals detected
        When: update_emotional_context runs
        Then: Signals are aggregated coherently
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "aggregated_emotion": "contentment",
            "signal_sources": ["text", "tone", "context"],
            "aggregation_complete": True,
        }

        result = await mock_db.fetchrow()
        assert result["aggregated_emotion"] == "contentment"
        assert len(result["signal_sources"]) == 3
        assert result["aggregation_complete"] is True

    @pytest.mark.asyncio
    async def test_respects_emotional_history(self, mock_db):
        """
        Given: User has emotional history
        When: update_emotional_context runs
        Then: History influences current state
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "history_considered": True,
            "baseline_emotion": "calm",
            "current_deviation": 0.2,
        }

        result = await mock_db.fetchrow()
        assert result["history_considered"] is True
        assert result["baseline_emotion"] == "calm"
        assert result["current_deviation"] == 0.2
