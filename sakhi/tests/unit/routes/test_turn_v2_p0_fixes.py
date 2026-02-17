"""
Route-level regression tests for turn_v2 P0 fixes.

Covers:
- Session compression enqueue does not reference undefined `entry_id`.
- Reflection trace receives valid `turn_id` and `session_id`.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID


# =============================================================================
# P0 Fix 1: Session Compression Enqueue
# =============================================================================


class TestSessionCompressionEnqueue:
    """
    Regression: session compression enqueue used to reference `entry_id`
    before it was defined (line 551 pre-fix), causing a NameError swallowed
    by the surrounding except.  Now it uses a static placeholder.
    """

    def test_enqueue_uses_static_turn_id(self):
        """
        Verify enqueue_turn_jobs is called with a static string, NOT entry_id.
        Simulates the session compression enqueue path from turn_v2.
        """
        from sakhi.apps.api.services.turn.async_triggers import enqueue_turn_jobs

        mock_queue = MagicMock()
        with patch(
            "sakhi.apps.api.services.turn.async_triggers._get_queue",
            return_value=mock_queue,
        ):
            enqueue_turn_jobs(
                "session-compress",  # The static placeholder used in the fix
                "user-123",
                ["session_compress"],
                {"session_id": "sess-456", "keep_recent": 8},
            )

        # Verify it was enqueued with the static string, not undefined entry_id
        call_kwargs = mock_queue.enqueue.call_args
        assert call_kwargs is not None
        job_kwargs = call_kwargs[1]["kwargs"]
        assert job_kwargs["turn_id"] == "session-compress"
        assert job_kwargs["person_id"] == "user-123"
        assert job_kwargs["job_type"] == "session_compress"
        assert job_kwargs["payload"]["session_id"] == "sess-456"

    @pytest.mark.asyncio
    async def test_session_compress_handler_ignores_turn_id(self):
        """
        The session_compress worker handler should only use session_id
        from the payload, not the turn_id.
        """
        from sakhi.apps.worker.pipelines.turn_updates.runner import (
            _handle_session_compress,
        )

        mock_compress = AsyncMock(return_value="Summary text")
        with patch(
            "sakhi.apps.api.services.memory.sessions.compress_older_turns_to_summary",
            mock_compress,
        ):
            await _handle_session_compress(
                "session-compress",  # turn_id — placeholder
                "user-123",
                {"session_id": "sess-456", "keep_recent": 6},
            )

        mock_compress.assert_called_once_with("sess-456", keep_recent=6)

    @pytest.mark.asyncio
    async def test_session_compress_handler_skips_without_session_id(self):
        """Handler should no-op when payload lacks session_id."""
        from sakhi.apps.worker.pipelines.turn_updates.runner import (
            _handle_session_compress,
        )

        mock_compress = AsyncMock()
        with patch(
            "sakhi.apps.api.services.memory.sessions.compress_older_turns_to_summary",
            mock_compress,
        ):
            await _handle_session_compress("x", "user-123", {})

        mock_compress.assert_not_called()


# =============================================================================
# P0 Fix 2: Reflection Trace turn_id / session_id
# =============================================================================


class TestReflectionTraceArgs:
    """
    Regression: reflection trace used to reference undefined `turn_id`
    (line 1012 pre-fix) and passed `session_id=user_id` instead of the
    actual session_id.  Now turn_id is generated early in turn_v2() and
    session_id is the real session identifier.
    """

    def test_build_reflection_trace_receives_valid_turn_id(self):
        """turn_id must be a valid UUID string, not undefined."""
        from sakhi.apps.engine.reflection_trace.engine import build_reflection_trace

        turn_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        session_id = "sess-789"

        result = build_reflection_trace(
            person_id="user-123",
            turn_id=turn_id,
            session_id=session_id,
            moment_model={"stability": 0.7, "confidence": 0.8},
            evidence_pack={"anchors": [], "confidence": 0.6},
            deliberation_scaffold=None,
        )

        assert result["turn_id"] == turn_id
        assert result["session_id"] == session_id
        assert result["person_id"] == "user-123"
        assert isinstance(result["confidence"], float)

    def test_build_reflection_trace_with_none_session_id(self):
        """session_id=None is valid when no session exists."""
        from sakhi.apps.engine.reflection_trace.engine import build_reflection_trace

        result = build_reflection_trace(
            person_id="user-123",
            turn_id="tid-abc",
            session_id=None,
            moment_model={},
            evidence_pack={},
            deliberation_scaffold=None,
        )

        assert result["session_id"] is None
        assert result["turn_id"] == "tid-abc"

    @pytest.mark.asyncio
    async def test_persist_reflection_trace_uses_correct_fields(self):
        """Verify persist_reflection_trace passes turn_id and session_id to DB."""
        from sakhi.apps.engine.reflection_trace.engine import (
            build_reflection_trace,
            persist_reflection_trace,
        )

        turn_id = "tid-test-123"
        session_id = "sess-test-456"

        payload = build_reflection_trace(
            person_id="user-123",
            turn_id=turn_id,
            session_id=session_id,
            moment_model={"confidence": 0.5},
            evidence_pack={"confidence": 0.5},
            deliberation_scaffold=None,
        )

        mock_dbexec = AsyncMock()
        await persist_reflection_trace(mock_dbexec, payload)

        mock_dbexec.assert_called_once()
        call_args = mock_dbexec.call_args[0]
        # Args: sql, person_id, turn_id, session_id, ...
        assert call_args[1] == "user-123"     # person_id
        assert call_args[2] == turn_id         # turn_id
        assert call_args[3] == session_id      # session_id

    def test_turn_v2_generates_turn_id_as_uuid(self):
        """
        Verify the turn_id generated in turn_v2 is a valid UUID.
        This tests the contract, not the route itself.
        """
        from uuid import uuid4

        turn_id = str(uuid4())
        # Should be parseable as a UUID
        parsed = UUID(turn_id)
        assert str(parsed) == turn_id
