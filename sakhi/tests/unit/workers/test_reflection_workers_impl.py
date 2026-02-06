"""
Unit tests for Priority 3 reflection workers.

Workers tested:
- reflect_morning_presence: Morning awareness and task summarization
- reflect_value_alignment: Value-theme alignment scoring
- reflective_loop: Legacy shim/adapter
- reflect_person_memory: Journal summarization and embedding (partial)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import numpy as np

from sakhi.tests.fixtures import DEMO_USER_ID


# =============================================================================
# reflect_morning_presence Tests
# =============================================================================

class TestReflectMorningPresence:
    """Tests for reflect_morning_presence worker."""

    @pytest.mark.asyncio
    async def test_summarizes_open_tasks(self):
        """
        Given: User has open tasks
        When: reflect_morning_presence runs
        Then: Summary reflects task count
        """
        mock_tasks = [
            {"user_id": DEMO_USER_ID, "status": "todo", "title": "Write report"},
            {"user_id": DEMO_USER_ID, "status": "todo", "title": "Call client"},
        ]

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.db_find",
            return_value=mock_tasks,
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.compose_response",
            new_callable=AsyncMock,
            return_value="Good morning!",
        ):
            from sakhi.apps.worker.tasks.reflect_morning_presence import (
                reflect_morning_presence,
            )

            await reflect_morning_presence(DEMO_USER_ID)

            # Check that execute was called with task summary
            call_args = mock_conn.execute.call_args[0]
            assert "2 open tasks" in call_args[2]  # summary_text

    @pytest.mark.asyncio
    async def test_clear_day_when_no_tasks(self):
        """
        Given: User has no open tasks
        When: reflect_morning_presence runs
        Then: Summary says "A clear day ahead"
        """
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.db_find",
            return_value=[],  # No tasks
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.compose_response",
            new_callable=AsyncMock,
            return_value="Good morning!",
        ):
            from sakhi.apps.worker.tasks.reflect_morning_presence import (
                reflect_morning_presence,
            )

            await reflect_morning_presence(DEMO_USER_ID)

            call_args = mock_conn.execute.call_args[0]
            assert "A clear day ahead" in call_args[2]  # summary_text

    @pytest.mark.asyncio
    async def test_sets_mood_to_balanced(self):
        """Should set mood_today to 'balanced'."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.db_find",
            return_value=[],
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.compose_response",
            new_callable=AsyncMock,
            return_value="Good morning!",
        ):
            from sakhi.apps.worker.tasks.reflect_morning_presence import (
                reflect_morning_presence,
            )

            await reflect_morning_presence(DEMO_USER_ID)

            call_args = mock_conn.execute.call_args[0]
            assert call_args[3] == "balanced"  # mood_today

    @pytest.mark.asyncio
    async def test_inserts_when_update_fails(self):
        """Should insert new row when update affects 0 rows."""
        mock_conn = AsyncMock()
        # First call (UPDATE) returns 0 rows affected
        mock_conn.execute = AsyncMock(side_effect=["UPDATE 0", "INSERT 1"])
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.db_find",
            return_value=[],
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.compose_response",
            new_callable=AsyncMock,
            return_value="Good morning!",
        ):
            from sakhi.apps.worker.tasks.reflect_morning_presence import (
                reflect_morning_presence,
            )

            await reflect_morning_presence(DEMO_USER_ID)

            # Should have called execute twice (UPDATE then INSERT)
            assert mock_conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_composes_morning_checkin_response(self):
        """Should call compose_response with morning_checkin intent."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_conn.close = AsyncMock()

        with patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.db_find",
            return_value=[{"title": "Task 1"}],
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.get_db",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ), patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.compose_response",
            new_callable=AsyncMock,
            return_value="Good morning!",
        ) as mock_compose:
            from sakhi.apps.worker.tasks.reflect_morning_presence import (
                reflect_morning_presence,
            )

            await reflect_morning_presence(DEMO_USER_ID)

            mock_compose.assert_called_once()
            call_args = mock_compose.call_args
            assert call_args[1]["intent"] == "morning_checkin"

    def test_send_message_logs(self):
        """send_message should log the message."""
        with patch(
            "sakhi.apps.worker.tasks.reflect_morning_presence.LOGGER"
        ) as mock_logger:
            from sakhi.apps.worker.tasks.reflect_morning_presence import send_message

            send_message(DEMO_USER_ID, "Hello there")

            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args)
            assert "morning_presence" in call_args
            assert "Hello there" in call_args


# =============================================================================
# reflect_value_alignment Tests
# =============================================================================

class TestReflectValueAlignment:
    """Tests for reflect_value_alignment worker."""

    def test_cosine_similarity_identical_vectors(self):
        """Cosine of identical vectors should be 1.0."""
        from sakhi.apps.worker.tasks.reflect_value_alignment import cosine

        vec = [1.0, 2.0, 3.0]
        assert cosine(vec, vec) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal_vectors(self):
        """Cosine of orthogonal vectors should be 0.0."""
        from sakhi.apps.worker.tasks.reflect_value_alignment import cosine

        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        assert cosine(vec_a, vec_b) == pytest.approx(0.0)

    def test_cosine_similarity_opposite_vectors(self):
        """Cosine of opposite vectors should be -1.0."""
        from sakhi.apps.worker.tasks.reflect_value_alignment import cosine

        vec_a = [1.0, 2.0, 3.0]
        vec_b = [-1.0, -2.0, -3.0]
        assert cosine(vec_a, vec_b) == pytest.approx(-1.0)

    def test_cosine_handles_zero_vector(self):
        """Cosine should return 0.0 when one vector is zero."""
        from sakhi.apps.worker.tasks.reflect_value_alignment import cosine

        vec_a = [1.0, 2.0, 3.0]
        vec_b = [0.0, 0.0, 0.0]
        assert cosine(vec_a, vec_b) == 0.0

    @pytest.mark.asyncio
    async def test_skips_when_no_declared_values(self):
        """Should skip when user has no declared values."""
        with patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_fetch",
            return_value={"person_id": DEMO_USER_ID, "declared_values": []},
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.reflect_value_alignment import (
                reflect_value_alignment,
            )

            await reflect_value_alignment(DEMO_USER_ID)

            mock_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_themes(self):
        """Should skip when user has no themes."""
        with patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_fetch",
            side_effect=[
                {"person_id": DEMO_USER_ID, "declared_values": ["growth", "health"]},
                {"themes": []},  # No themes
            ],
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.reflect_value_alignment import (
                reflect_value_alignment,
            )

            await reflect_value_alignment(DEMO_USER_ID)

            mock_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_computes_alignment_score(self):
        """Should compute alignment score between values and themes."""
        mock_embedding = [0.1] * 1536  # Simplified embedding

        with patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_fetch",
            side_effect=[
                {"person_id": DEMO_USER_ID, "declared_values": ["growth", "health"]},
                {"themes": [{"name": "wellness"}, {"name": "productivity"}]},
            ],
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.embed_text",
            new_callable=AsyncMock,
            return_value=mock_embedding,
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.llm_reflect",
            new_callable=AsyncMock,
            return_value="Values align well with themes.",
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.reflect_value_alignment import (
                reflect_value_alignment,
            )

            await reflect_value_alignment(DEMO_USER_ID)

            mock_upsert.assert_called()
            record = mock_upsert.call_args[0][1]
            assert "alignment_score" in record
            # Same embedding = cosine 1.0
            assert record["alignment_score"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_enqueues_insight_when_misaligned(self):
        """Should enqueue insight when alignment score < 0.6."""
        # Create two different embeddings for low score
        val_embedding = [1.0] + [0.0] * 1535
        theme_embedding = [0.0] * 1535 + [1.0]  # Orthogonal

        with patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_fetch",
            side_effect=[
                {"person_id": DEMO_USER_ID, "declared_values": ["growth"]},
                {"themes": [{"name": "relaxation"}]},
            ],
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.embed_text",
            new_callable=AsyncMock,
            side_effect=[val_embedding, theme_embedding],
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.llm_reflect",
            new_callable=AsyncMock,
            return_value="Values diverge from themes.",
        ), patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.reflect_value_alignment import (
                reflect_value_alignment,
            )

            await reflect_value_alignment(DEMO_USER_ID)

            # Should call db_upsert twice: once for value_alignment, once for alignment_insights
            assert mock_upsert.call_count == 2
            # Second call should be to alignment_insights
            second_call = mock_upsert.call_args_list[1]
            assert second_call[0][0] == "alignment_insights"

    def test_enqueue_alignment_insight(self):
        """enqueue_alignment_insight should store insight."""
        with patch(
            "sakhi.apps.worker.tasks.reflect_value_alignment.db_upsert"
        ) as mock_upsert:
            from sakhi.apps.worker.tasks.reflect_value_alignment import (
                enqueue_alignment_insight,
            )

            enqueue_alignment_insight(DEMO_USER_ID, "Values diverge", 0.4)

            mock_upsert.assert_called_once()
            record = mock_upsert.call_args[0][1]
            assert record["person_id"] == DEMO_USER_ID
            assert record["latest_comment"] == "Values diverge"
            assert record["last_score"] == 0.4


# =============================================================================
# reflective_loop Tests
# =============================================================================

class TestReflectiveLoop:
    """Tests for reflective_loop shim module."""

    def test_import_raises_when_legacy_missing(self):
        """Should raise ImportError when legacy module is missing."""
        # The reflective_loop module will try to import from legacy namespace
        # Since that doesn't exist, it should raise ImportError
        with pytest.raises(ImportError) as exc_info:
            # Force re-import to trigger the ImportError
            import importlib
            import sys

            # Remove cached module if present
            if "sakhi.apps.worker.tasks.reflective_loop" in sys.modules:
                del sys.modules["sakhi.apps.worker.tasks.reflective_loop"]

            from sakhi.apps.worker.tasks import reflective_loop

        assert "apps.worker.tasks.reflective_loop" in str(exc_info.value)


# =============================================================================
# Response Composer Tests
# =============================================================================

class TestResponseComposer:
    """Tests for response composer utility."""

    @pytest.mark.asyncio
    async def test_uses_tone_from_profile(self):
        """Should use tone weights from user profile."""
        with patch(
            "sakhi.apps.worker.utils.response_composer.db_fetch",
            side_effect=[
                {"tone_weights": {"warm": 0.8, "direct": 0.2}},  # profile
                {},  # continuity
            ],
        ), patch(
            "sakhi.apps.worker.utils.response_composer.llm_router"
        ) as mock_router:
            mock_router.text = AsyncMock(return_value="Hello!")

            from sakhi.apps.worker.utils.response_composer import compose_response

            await compose_response(DEMO_USER_ID, "morning_checkin", {})

            call_args = mock_router.text.call_args[0][0]
            # Warm > direct should result in "gentle" tone
            assert "gentle" in call_args.lower()

    @pytest.mark.asyncio
    async def test_uses_emotion_context(self):
        """Should include emotion from session continuity."""
        with patch(
            "sakhi.apps.worker.utils.response_composer.db_fetch",
            side_effect=[
                {},  # profile
                {"last_emotion": "anxious"},  # continuity
            ],
        ), patch(
            "sakhi.apps.worker.utils.response_composer.llm_router"
        ) as mock_router:
            mock_router.text = AsyncMock(return_value="Hello!")

            from sakhi.apps.worker.utils.response_composer import compose_response

            await compose_response(DEMO_USER_ID, "reflective_nudge", {})

            call_args = mock_router.text.call_args[0][0]
            assert "anxious" in call_args

    @pytest.mark.asyncio
    async def test_falls_back_to_templates(self):
        """Should fall back to template when LLM fails."""
        with patch(
            "sakhi.apps.worker.utils.response_composer.db_fetch",
            return_value={},
        ), patch(
            "sakhi.apps.worker.utils.response_composer.llm_router"
        ) as mock_router:
            mock_router.text = AsyncMock(side_effect=Exception("LLM failed"))

            from sakhi.apps.worker.utils.response_composer import compose_response

            result = await compose_response(DEMO_USER_ID, "morning_checkin", {})

            # Should return one of the fallback messages
            assert "morning" in result.lower() or "energy" in result.lower()

    @pytest.mark.asyncio
    async def test_default_fallback_for_unknown_intent(self):
        """Should return generic fallback for unknown intents."""
        with patch(
            "sakhi.apps.worker.utils.response_composer.db_fetch",
            return_value={},
        ), patch(
            "sakhi.apps.worker.utils.response_composer.llm_router"
        ) as mock_router:
            mock_router.text = AsyncMock(side_effect=Exception("LLM failed"))

            from sakhi.apps.worker.utils.response_composer import compose_response

            result = await compose_response(DEMO_USER_ID, "unknown_intent_xyz", {})

            # Should return something (generic fallback)
            assert len(result) > 0


# =============================================================================
# reflect_person_memory Tests
# =============================================================================
# Note: reflect_person_memory has complex internal dependencies that make it
# difficult to unit test in isolation. The worker has circular import patterns
# that require integration testing with the full worker infrastructure.
# See sakhi/tests/integration/workers/ for integration tests of this worker.


# =============================================================================
# LLM Utility Tests (Additional)
# =============================================================================

class TestLLMReflect:
    """Tests for llm_reflect utility."""

    @pytest.mark.asyncio
    async def test_llm_reflect_returns_formatted_response(self):
        """llm_reflect should return formatted response."""
        from sakhi.apps.worker.utils.llm import llm_reflect

        result = await llm_reflect("Test reflection", mode="general")

        assert "[general]" in result
        assert "Test reflection" in result

    @pytest.mark.asyncio
    async def test_llm_reflect_with_custom_mode(self):
        """llm_reflect should use custom mode."""
        from sakhi.apps.worker.utils.llm import llm_reflect

        result = await llm_reflect("Alignment check", mode="value_alignment")

        assert "[value_alignment]" in result
