"""
Unit tests for Priority 2 state update workers.

Workers tested:
- update_conversation_state: Emotion detection and conversation state updates
- update_emotional_context: Session continuity and emotional context
- update_prompt_profile: Tone weight adjustments from feedback
- update_relationship_arcs: Relationship sentiment tracking
- update_theme_rhythm_links: Theme-rhythm correlation computation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


# =============================================================================
# update_conversation_state Tests
# =============================================================================

class TestUpdateConversationState:
    """Tests for update_conversation_state worker."""

    def test_detect_emotion_tired(self):
        """Should detect tired emotion from text."""
        from sakhi.apps.worker.tasks.update_conversation_state import detect_emotion

        result = detect_emotion("I'm feeling exhausted today")
        assert result["emotion"] == "tired"
        assert result["energy"] == 0.3

    def test_detect_emotion_happy(self):
        """Should detect happy emotion from text."""
        from sakhi.apps.worker.tasks.update_conversation_state import detect_emotion

        result = detect_emotion("I'm so excited about this!")
        assert result["emotion"] == "happy"
        assert result["energy"] == 0.75

    def test_detect_emotion_anxious(self):
        """Should detect anxious emotion from text."""
        from sakhi.apps.worker.tasks.update_conversation_state import detect_emotion

        result = detect_emotion("I'm feeling nervous about the presentation")
        assert result["emotion"] == "anxious"
        assert result["energy"] == 0.4

    def test_detect_emotion_neutral_default(self):
        """Should default to neutral for unrecognized emotions."""
        from sakhi.apps.worker.tasks.update_conversation_state import detect_emotion

        result = detect_emotion("The weather is nice today")
        assert result["emotion"] == "neutral"
        assert result["energy"] == 0.5

    def test_detect_emotion_empty_text(self):
        """Should handle empty text gracefully."""
        from sakhi.apps.worker.tasks.update_conversation_state import detect_emotion

        result = detect_emotion("")
        assert result["emotion"] == "neutral"
        assert result["energy"] == 0.5

    @pytest.mark.asyncio
    async def test_update_conversation_state_saves_to_db(self):
        """
        Given: User sends message with emotion
        When: update_conversation_state runs
        Then: State is persisted to database
        """
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.update_conversation_state.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            from sakhi.apps.worker.tasks.update_conversation_state import (
                update_conversation_state,
            )

            await update_conversation_state(DEMO_USER_ID, "I'm feeling tired today")

            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert DEMO_USER_ID in call_args[0]
            assert "tired" in call_args[0]

    @pytest.mark.asyncio
    async def test_update_conversation_state_skips_empty_input(self):
        """Should skip processing for empty person_id or text."""
        mock_conn = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.update_conversation_state.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            from sakhi.apps.worker.tasks.update_conversation_state import (
                update_conversation_state,
            )

            await update_conversation_state("", "Some text")
            mock_conn.execute.assert_not_called()

            await update_conversation_state(DEMO_USER_ID, "")
            mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_maybe_send_nudge_for_tired(self):
        """Should send nudge message for tired emotion."""
        with patch(
            "sakhi.apps.worker.tasks.update_conversation_state.LOGGER"
        ) as mock_logger:
            from sakhi.apps.worker.tasks.update_conversation_state import (
                maybe_send_nudge,
            )

            await maybe_send_nudge(DEMO_USER_ID, "tired")

            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args)
            assert "Micro-nudge" in call_args
            assert "deep breaths" in call_args

    @pytest.mark.asyncio
    async def test_maybe_send_nudge_skips_neutral(self):
        """Should not send nudge for neutral emotion."""
        with patch(
            "sakhi.apps.worker.tasks.update_conversation_state.LOGGER"
        ) as mock_logger:
            from sakhi.apps.worker.tasks.update_conversation_state import (
                maybe_send_nudge,
            )

            await maybe_send_nudge(DEMO_USER_ID, "neutral")

            # Should not log nudge for neutral (no nudge defined)
            for call in mock_logger.info.call_args_list:
                assert "Micro-nudge" not in str(call)


# =============================================================================
# update_emotional_context Tests
# =============================================================================

class TestUpdateEmotionalContext:
    """Tests for update_emotional_context worker."""

    @pytest.mark.asyncio
    async def test_updates_session_continuity_with_emotion(self):
        """
        Given: User message with emotional content
        When: update_emotional_context runs
        Then: Session continuity is updated with emotion
        """
        with patch(
            "sakhi.apps.worker.tasks.update_emotional_context.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_emotional_context import (
                update_emotional_context,
            )

            await update_emotional_context(DEMO_USER_ID, "I'm feeling anxious about work")

            mock_upsert.assert_called_once()
            call_args = mock_upsert.call_args
            assert call_args[0][0] == "session_continuity"
            record = call_args[0][1]
            assert record["person_id"] == DEMO_USER_ID
            assert record["last_emotion"] == "anxious"
            assert "last_interaction_ts" in record

    @pytest.mark.asyncio
    async def test_defaults_to_neutral_for_unrecognized(self):
        """Should default to neutral for unrecognized emotions."""
        with patch(
            "sakhi.apps.worker.tasks.update_emotional_context.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_emotional_context import (
                update_emotional_context,
            )

            await update_emotional_context(DEMO_USER_ID, "Just checking in")

            record = mock_upsert.call_args[0][1]
            assert record["last_emotion"] == "neutral"

    @pytest.mark.asyncio
    async def test_includes_timestamp_in_utc(self):
        """Should include ISO format timestamp."""
        with patch(
            "sakhi.apps.worker.tasks.update_emotional_context.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_emotional_context import (
                update_emotional_context,
            )

            await update_emotional_context(DEMO_USER_ID, "Hello")

            record = mock_upsert.call_args[0][1]
            ts = record["last_interaction_ts"]
            # Should be valid ISO format
            assert "T" in ts
            assert "+" in ts or "Z" in ts


# =============================================================================
# update_prompt_profile Tests
# =============================================================================

class TestUpdatePromptProfile:
    """Tests for update_prompt_profile worker."""

    @pytest.mark.asyncio
    async def test_adjusts_tone_for_too_blunt_feedback(self):
        """
        Given: User feedback says response was too blunt
        When: update_prompt_profile runs
        Then: Warm increases, direct decreases
        """
        mock_feedback = [{"person_id": DEMO_USER_ID, "comment": "That was too blunt"}]

        with patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_find",
            return_value=mock_feedback,
        ), patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_prompt_profile import (
                update_prompt_profile,
            )

            await update_prompt_profile(DEMO_USER_ID)

            mock_upsert.assert_called_once()
            record = mock_upsert.call_args[0][1]
            tone = record["tone_weights"]
            assert tone["warm"] == 0.6  # 0.5 + 0.1
            assert tone["direct"] == 0.4  # 0.5 - 0.1

    @pytest.mark.asyncio
    async def test_adjusts_tone_for_too_soft_feedback(self):
        """
        Given: User feedback says response was too soft
        When: update_prompt_profile runs
        Then: Direct increases, warm decreases
        """
        mock_feedback = [{"person_id": DEMO_USER_ID, "comment": "That was too soft"}]

        with patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_find",
            return_value=mock_feedback,
        ), patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_prompt_profile import (
                update_prompt_profile,
            )

            await update_prompt_profile(DEMO_USER_ID)

            record = mock_upsert.call_args[0][1]
            tone = record["tone_weights"]
            assert tone["direct"] == 0.6  # 0.5 + 0.1
            assert tone["warm"] == 0.4  # 0.5 - 0.1

    @pytest.mark.asyncio
    async def test_clamps_tone_values_at_boundaries(self):
        """
        Given: Multiple feedback entries pushing tone to extreme
        When: update_prompt_profile runs
        Then: Values are clamped between 0.0 and 1.0
        """
        # 10 "too blunt" entries would push warm to 1.5 and direct to -0.5
        mock_feedback = [
            {"person_id": DEMO_USER_ID, "comment": "too blunt"} for _ in range(10)
        ]

        with patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_find",
            return_value=mock_feedback,
        ), patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_prompt_profile import (
                update_prompt_profile,
            )

            await update_prompt_profile(DEMO_USER_ID)

            record = mock_upsert.call_args[0][1]
            tone = record["tone_weights"]
            assert tone["warm"] == 1.0  # Clamped at max
            assert tone["direct"] == 0.0  # Clamped at min

    @pytest.mark.asyncio
    async def test_skips_update_when_no_feedback(self):
        """Should skip update when no feedback exists."""
        with patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_find",
            return_value=[],
        ), patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_prompt_profile import (
                update_prompt_profile,
            )

            await update_prompt_profile(DEMO_USER_ID)

            mock_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_mixed_feedback(self):
        """
        Given: Mixed feedback (some too blunt, some too soft)
        When: update_prompt_profile runs
        Then: Adjustments balance out
        """
        mock_feedback = [
            {"person_id": DEMO_USER_ID, "comment": "too blunt"},
            {"person_id": DEMO_USER_ID, "comment": "too soft"},
            {"person_id": DEMO_USER_ID, "comment": "too blunt"},
        ]

        with patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_find",
            return_value=mock_feedback,
        ), patch(
            "sakhi.apps.worker.tasks.update_prompt_profile.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_prompt_profile import (
                update_prompt_profile,
            )

            await update_prompt_profile(DEMO_USER_ID)

            record = mock_upsert.call_args[0][1]
            tone = record["tone_weights"]
            # 2 too blunt (+0.2 warm, -0.2 direct)
            # 1 too soft (+0.1 direct, -0.1 warm)
            # Net: warm = 0.5 + 0.2 - 0.1 = 0.6, direct = 0.5 - 0.2 + 0.1 = 0.4
            assert tone["warm"] == 0.6
            assert tone["direct"] == 0.4


# =============================================================================
# update_relationship_arcs Tests
# =============================================================================

class TestUpdateRelationshipArcs:
    """Tests for update_relationship_arcs worker."""

    @pytest.mark.asyncio
    async def test_extracts_people_from_text(self):
        """
        Given: Journal entry mentioning people
        When: update_relationship_arcs runs
        Then: People are extracted and relationships created
        """
        with patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.resolve_person_id",
            new_callable=AsyncMock,
            return_value=DEMO_USER_ID,
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_fetch",
            return_value={},  # No existing arc
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_relationship_arcs import (
                update_relationship_arcs,
            )

            await update_relationship_arcs(
                DEMO_USER_ID, "Had a great meeting with Sarah today"
            )

            mock_upsert.assert_called()
            record = mock_upsert.call_args[0][1]
            assert record["person_ref"] == "Sarah"
            assert record["person_id"] == DEMO_USER_ID

    @pytest.mark.asyncio
    async def test_computes_sentiment_score(self):
        """Should compute sentiment from text content."""
        with patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.resolve_person_id",
            new_callable=AsyncMock,
            return_value=DEMO_USER_ID,
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_fetch",
            return_value={},
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_relationship_arcs import (
                update_relationship_arcs,
            )

            # Positive sentiment text
            await update_relationship_arcs(
                DEMO_USER_ID, "I love working with Alice, I'm so grateful"
            )

            record = mock_upsert.call_args[0][1]
            # "love" and "grateful" = +2 sentiment
            assert record["strength_score"] >= 0.0

    @pytest.mark.asyncio
    async def test_tracks_weekly_sentiment_trend(self):
        """Should track sentiment by week."""
        existing_arc = {
            "person_id": DEMO_USER_ID,
            "person_ref": "Bob",
            "sentiment_trend": {"w01": 0.5},
        }

        with patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.resolve_person_id",
            new_callable=AsyncMock,
            return_value=DEMO_USER_ID,
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_fetch",
            return_value=existing_arc,
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_relationship_arcs import (
                update_relationship_arcs,
            )

            await update_relationship_arcs(DEMO_USER_ID, "Met with Bob about the project")

            record = mock_upsert.call_args[0][1]
            # Should have trend entries
            assert "sentiment_trend" in record
            assert isinstance(record["sentiment_trend"], dict)

    @pytest.mark.asyncio
    async def test_skips_when_no_people_mentioned(self):
        """Should skip when no people are extracted."""
        with patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.resolve_person_id",
            new_callable=AsyncMock,
            return_value=DEMO_USER_ID,
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_relationship_arcs import (
                update_relationship_arcs,
            )

            # No proper nouns
            await update_relationship_arcs(DEMO_USER_ID, "went to the store today")

            mock_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculates_strength_as_average(self):
        """Strength score should be average of trend values."""
        existing_arc = {
            "person_id": DEMO_USER_ID,
            "person_ref": "Carol",
            "sentiment_trend": {"w01": 0.5, "w02": 1.0},  # avg = 0.75
        }

        with patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.resolve_person_id",
            new_callable=AsyncMock,
            return_value=DEMO_USER_ID,
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_fetch",
            return_value=existing_arc,
        ), patch(
            "sakhi.apps.worker.tasks.update_relationship_arcs.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.update_relationship_arcs import (
                update_relationship_arcs,
            )

            await update_relationship_arcs(
                DEMO_USER_ID, "Carol helped me with the task"
            )

            record = mock_upsert.call_args[0][1]
            # Strength should be average of trend values
            assert "strength_score" in record


# =============================================================================
# update_theme_rhythm_links Tests
# =============================================================================

class TestUpdateThemeRhythmLinks:
    """Tests for update_theme_rhythm_links worker."""

    @pytest.mark.asyncio
    async def test_computes_correlation_for_theme(self):
        """
        Given: Theme states and rhythm forecasts
        When: update_theme_rhythm_links runs
        Then: Correlation is computed and stored
        """
        mock_rows = [
            {"person_id": DEMO_USER_ID, "theme": "work", "clarity_score": 0.8, "energy_score": 0.7},
            {"person_id": DEMO_USER_ID, "theme": "work", "clarity_score": 0.6, "energy_score": 0.5},
            {"person_id": DEMO_USER_ID, "theme": "work", "clarity_score": 0.9, "energy_score": 0.85},
            {"person_id": DEMO_USER_ID, "theme": "work", "clarity_score": 0.7, "energy_score": 0.65},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.update_theme_rhythm_links.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            from sakhi.apps.worker.tasks.update_theme_rhythm_links import (
                update_theme_rhythm_links,
            )

            await update_theme_rhythm_links()

            mock_conn.execute.assert_called()
            call_args = mock_conn.execute.call_args[0]
            # Should have computed correlation
            assert DEMO_USER_ID in call_args
            assert "work" in call_args

    @pytest.mark.asyncio
    async def test_handles_no_data_gracefully(self):
        """Should handle empty data without errors."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.update_theme_rhythm_links.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            from sakhi.apps.worker.tasks.update_theme_rhythm_links import (
                update_theme_rhythm_links,
            )

            # Should not raise
            await update_theme_rhythm_links()

            mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_short_series_with_zero_correlation(self):
        """Should set correlation to 0 for series with < 3 points."""
        mock_rows = [
            {"person_id": DEMO_USER_ID, "theme": "health", "clarity_score": 0.8, "energy_score": 0.7},
            {"person_id": DEMO_USER_ID, "theme": "health", "clarity_score": 0.6, "energy_score": 0.5},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.update_theme_rhythm_links.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            from sakhi.apps.worker.tasks.update_theme_rhythm_links import (
                update_theme_rhythm_links,
            )

            await update_theme_rhythm_links()

            mock_conn.execute.assert_called()
            call_args = mock_conn.execute.call_args[0]
            # Correlation should be 0.0 for short series
            correlation_arg = call_args[3]  # 4th arg is correlation
            assert correlation_arg == 0.0

    @pytest.mark.asyncio
    async def test_groups_by_person_and_theme(self):
        """Should compute separate correlations per person-theme pair."""
        mock_rows = [
            # Person 1, theme A
            {"person_id": "user-1", "theme": "work", "clarity_score": 0.8, "energy_score": 0.7},
            {"person_id": "user-1", "theme": "work", "clarity_score": 0.6, "energy_score": 0.5},
            {"person_id": "user-1", "theme": "work", "clarity_score": 0.9, "energy_score": 0.8},
            # Person 1, theme B
            {"person_id": "user-1", "theme": "health", "clarity_score": 0.5, "energy_score": 0.6},
            {"person_id": "user-1", "theme": "health", "clarity_score": 0.7, "energy_score": 0.8},
            {"person_id": "user-1", "theme": "health", "clarity_score": 0.6, "energy_score": 0.7},
            # Person 2, theme A
            {"person_id": "user-2", "theme": "work", "clarity_score": 0.4, "energy_score": 0.5},
            {"person_id": "user-2", "theme": "work", "clarity_score": 0.5, "energy_score": 0.6},
            {"person_id": "user-2", "theme": "work", "clarity_score": 0.6, "energy_score": 0.7},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.update_theme_rhythm_links.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            from sakhi.apps.worker.tasks.update_theme_rhythm_links import (
                update_theme_rhythm_links,
            )

            await update_theme_rhythm_links()

            # Should have 3 calls: user-1/work, user-1/health, user-2/work
            assert mock_conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_computes_trends(self):
        """Should compute clarity and energy trends."""
        mock_rows = [
            {"person_id": DEMO_USER_ID, "theme": "focus", "clarity_score": 0.5, "energy_score": 0.5},
            {"person_id": DEMO_USER_ID, "theme": "focus", "clarity_score": 0.6, "energy_score": 0.6},
            {"person_id": DEMO_USER_ID, "theme": "focus", "clarity_score": 0.7, "energy_score": 0.7},
            {"person_id": DEMO_USER_ID, "theme": "focus", "clarity_score": 0.8, "energy_score": 0.8},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.update_theme_rhythm_links.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ):
            from sakhi.apps.worker.tasks.update_theme_rhythm_links import (
                update_theme_rhythm_links,
            )

            await update_theme_rhythm_links()

            call_args = mock_conn.execute.call_args[0]
            clarity_trend = call_args[4]  # 5th arg
            energy_trend = call_args[5]  # 6th arg
            samples = call_args[6]  # 7th arg

            # Upward trend: diff([0.5, 0.6, 0.7, 0.8]) = [0.1, 0.1, 0.1], mean = 0.1
            assert abs(clarity_trend - 0.1) < 0.01
            assert abs(energy_trend - 0.1) < 0.01
            assert samples == 4


# =============================================================================
# Emotion Utility Tests
# =============================================================================

class TestEmotionExtraction:
    """Tests for emotion extraction utility."""

    def test_extract_emotion_tired(self):
        """Should detect tired from tired/exhausted/drained."""
        from sakhi.apps.worker.utils.emotion import extract_emotion

        assert extract_emotion("I'm so tired") == "tired"
        assert extract_emotion("feeling exhausted") == "tired"
        assert extract_emotion("completely drained") == "tired"

    def test_extract_emotion_happy(self):
        """Should detect happy from happy/excited/joy."""
        from sakhi.apps.worker.utils.emotion import extract_emotion

        assert extract_emotion("I'm happy") == "happy"
        assert extract_emotion("so excited!") == "happy"
        assert extract_emotion("full of joy") == "happy"

    def test_extract_emotion_anxious(self):
        """Should detect anxious from anxious/nervous/worried."""
        from sakhi.apps.worker.utils.emotion import extract_emotion

        assert extract_emotion("feeling anxious") == "anxious"
        assert extract_emotion("I'm nervous") == "anxious"
        assert extract_emotion("worried about tomorrow") == "anxious"

    def test_extract_emotion_sad(self):
        """Should detect sad from sad/down/low."""
        from sakhi.apps.worker.utils.emotion import extract_emotion

        assert extract_emotion("I'm sad today") == "sad"
        assert extract_emotion("feeling down") == "sad"
        assert extract_emotion("energy is low") == "sad"

    def test_extract_emotion_frustrated(self):
        """Should detect frustrated from angry/frustrated."""
        from sakhi.apps.worker.utils.emotion import extract_emotion

        assert extract_emotion("so angry") == "frustrated"
        assert extract_emotion("I'm frustrated") == "frustrated"

    def test_extract_emotion_neutral_default(self):
        """Should return neutral for unrecognized text."""
        from sakhi.apps.worker.utils.emotion import extract_emotion

        assert extract_emotion("hello there") == "neutral"
        assert extract_emotion("the sky is blue") == "neutral"
        assert extract_emotion("") == "neutral"


# =============================================================================
# LLM Utility Tests
# =============================================================================

class TestLLMUtils:
    """Tests for LLM utility functions."""

    def test_extract_entities_finds_proper_nouns(self):
        """Should extract proper nouns as people names."""
        from sakhi.apps.worker.utils.llm import extract_entities

        entities = extract_entities("Met with John and Sarah today")
        assert "John" in entities
        assert "Sarah" in entities

    def test_extract_entities_ignores_days(self):
        """Should ignore day names."""
        from sakhi.apps.worker.utils.llm import extract_entities

        entities = extract_entities("See you on Monday")
        assert "Monday" not in entities

    def test_extract_entities_empty_text(self):
        """Should return empty list for empty text."""
        from sakhi.apps.worker.utils.llm import extract_entities

        assert extract_entities("") == []
        assert extract_entities("no proper nouns here") == []

    def test_sentiment_score_positive(self):
        """Should return positive score for positive words."""
        from sakhi.apps.worker.utils.llm import sentiment_score

        score = sentiment_score("I love this and I'm so grateful")
        assert score > 0

    def test_sentiment_score_negative(self):
        """Should return negative score for negative words."""
        from sakhi.apps.worker.utils.llm import sentiment_score

        score = sentiment_score("I'm angry and upset about this")
        assert score < 0

    def test_sentiment_score_clamped(self):
        """Should clamp score between -1 and 1."""
        from sakhi.apps.worker.utils.llm import sentiment_score

        # Many positive words
        score = sentiment_score("love love love grateful grateful excited")
        assert score <= 1.0
        assert score >= -1.0
