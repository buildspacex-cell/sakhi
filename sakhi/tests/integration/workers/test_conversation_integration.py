"""
Integration tests for conversation workers.

Tests actual database operations for:
- Conversation turns
- Conversation sessions
- User choices
- Recommendation feedback
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
import uuid

from sakhi.tests.fixtures import DEMO_USER_ID


@pytest.mark.integration
class TestConversationTurnsIntegration:
    """Integration tests for conversation turn storage."""

    @pytest.mark.asyncio
    async def test_turn_stored(self, db, ensure_test_user):
        """
        Given: User sends a message
        When: Turn stored
        Then: Turn with metadata persisted
        """
        await ensure_test_user(DEMO_USER_ID)

        turn_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        queued_jobs = json.dumps([])
        metadata = json.dumps({"source": "web"})

        # First create a session for the turn (FK constraint)
        await db.execute("""
            INSERT INTO conversation_sessions
            (id, user_id, slug, status, created_at, last_active_at, turn_count)
            VALUES ($1, $2, $3, $4, NOW(), NOW(), 0)
        """, session_id, DEMO_USER_ID, f"session-{session_id[:8]}", "active")

        await db.execute("""
            INSERT INTO conversation_turns
            (id, user_id, session_id, person_id, role, text, tone, created_at, context_version, queued_jobs, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8, $9::jsonb, $10::jsonb)
        """, turn_id, DEMO_USER_ID, session_id, DEMO_USER_ID, "user",
            "I'm feeling tired today", "neutral", 1, queued_jobs, metadata)

        result = await db.fetchrow(
            "SELECT * FROM conversation_turns WHERE id = $1",
            turn_id
        )
        assert result is not None
        assert result["text"] == "I'm feeling tired today"
        assert result["role"] == "user"

        # Cleanup
        await db.execute("DELETE FROM conversation_turns WHERE id = $1", turn_id)
        await db.execute("DELETE FROM conversation_sessions WHERE id = $1", session_id)

    @pytest.mark.asyncio
    async def test_turn_with_reply(self, db, ensure_test_user):
        """
        Given: User message
        When: Assistant replies
        Then: Reply stored with turn
        """
        await ensure_test_user(DEMO_USER_ID)

        turn_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        queued_jobs = json.dumps(["reflect_memory"])
        metadata = json.dumps({})

        # First create a session
        await db.execute("""
            INSERT INTO conversation_sessions
            (id, user_id, slug, status, created_at, last_active_at, turn_count)
            VALUES ($1, $2, $3, $4, NOW(), NOW(), 0)
        """, session_id, DEMO_USER_ID, f"session-{session_id[:8]}", "active")

        await db.execute("""
            INSERT INTO conversation_turns
            (id, user_id, session_id, person_id, role, text, reply, archetype, created_at, context_version, queued_jobs, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9, $10::jsonb, $11::jsonb)
        """, turn_id, DEMO_USER_ID, session_id, DEMO_USER_ID, "user",
            "How can I improve my energy?",
            "Based on your patterns, morning exercise and earlier sleep might help.",
            "advisor", 1, queued_jobs, metadata)

        result = await db.fetchrow(
            "SELECT text, reply, archetype FROM conversation_turns WHERE id = $1",
            turn_id
        )
        assert result is not None
        assert result["reply"] is not None
        assert result["archetype"] == "advisor"

        # Cleanup
        await db.execute("DELETE FROM conversation_turns WHERE id = $1", turn_id)
        await db.execute("DELETE FROM conversation_sessions WHERE id = $1", session_id)

    @pytest.mark.asyncio
    async def test_conversation_session_turns(self, db, ensure_test_user):
        """
        Given: Multiple turns in session
        When: Queried by session
        Then: All turns returned in order
        """
        await ensure_test_user(DEMO_USER_ID)

        session_id = str(uuid.uuid4())
        turn_ids = [str(uuid.uuid4()) for _ in range(3)]
        messages = [
            "Hello Sakhi",
            "I need help with my goals",
            "What should I focus on today?"
        ]
        metadata = json.dumps({})

        # First create a session
        await db.execute("""
            INSERT INTO conversation_sessions
            (id, user_id, slug, status, created_at, last_active_at, turn_count)
            VALUES ($1, $2, $3, $4, NOW(), NOW(), 0)
        """, session_id, DEMO_USER_ID, f"session-{session_id[:8]}", "active")

        for i, (turn_id, text) in enumerate(zip(turn_ids, messages)):
            await db.execute("""
                INSERT INTO conversation_turns
                (id, user_id, session_id, person_id, role, text, created_at, context_version, queued_jobs, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, NOW() + ($7 || ' minutes')::interval, $8, '[]'::jsonb, $9::jsonb)
            """, turn_id, DEMO_USER_ID, session_id, DEMO_USER_ID, "user", text, str(i), 1, metadata)

        results = await db.fetch("""
            SELECT text FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at
        """, session_id)

        assert len(results) == 3
        assert results[0]["text"] == "Hello Sakhi"
        assert results[2]["text"] == "What should I focus on today?"

        # Cleanup
        for turn_id in turn_ids:
            await db.execute("DELETE FROM conversation_turns WHERE id = $1", turn_id)
        await db.execute("DELETE FROM conversation_sessions WHERE id = $1", session_id)


@pytest.mark.integration
class TestConversationSessionsIntegration:
    """Integration tests for conversation sessions."""

    @pytest.mark.asyncio
    async def test_session_created(self, db, ensure_test_user):
        """
        Given: New conversation starts
        When: Session created
        Then: Session metadata stored
        """
        await ensure_test_user(DEMO_USER_ID)

        session_id = str(uuid.uuid4())
        slug = f"morning-checkin-{session_id[:8]}"

        await db.execute("""
            INSERT INTO conversation_sessions
            (id, user_id, slug, title, status, created_at, last_active_at, turn_count)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW(), 0)
        """, session_id, DEMO_USER_ID, slug, "Morning Check-in", "active")

        result = await db.fetchrow(
            "SELECT * FROM conversation_sessions WHERE id = $1",
            session_id
        )
        assert result is not None
        assert result["slug"] == slug
        assert result["status"] == "active"

        # Cleanup
        await db.execute("DELETE FROM conversation_sessions WHERE id = $1", session_id)

    @pytest.mark.asyncio
    async def test_session_updated(self, db, ensure_test_user):
        """
        Given: Active session
        When: Turn added
        Then: last_active_at and turn_count updated
        """
        await ensure_test_user(DEMO_USER_ID)

        session_id = str(uuid.uuid4())
        slug = f"session-{session_id[:8]}"

        # Create session
        await db.execute("""
            INSERT INTO conversation_sessions
            (id, user_id, slug, status, created_at, last_active_at, turn_count)
            VALUES ($1, $2, $3, $4, NOW() - INTERVAL '10 minutes', NOW() - INTERVAL '10 minutes', 0)
        """, session_id, DEMO_USER_ID, slug, "active")

        # Update on new turn
        await db.execute("""
            UPDATE conversation_sessions
            SET last_active_at = NOW(), turn_count = turn_count + 1
            WHERE id = $1
        """, session_id)

        result = await db.fetchrow(
            "SELECT created_at, last_active_at, turn_count FROM conversation_sessions WHERE id = $1",
            session_id
        )
        assert result is not None
        assert result["last_active_at"] > result["created_at"]
        assert result["turn_count"] == 1

        # Cleanup
        await db.execute("DELETE FROM conversation_sessions WHERE id = $1", session_id)


@pytest.mark.integration
class TestUserChoicesIntegration:
    """Integration tests for user choice tracking."""

    @pytest.mark.asyncio
    async def test_choice_recorded(self, db, ensure_test_user):
        """
        Given: User presented with options
        When: User makes choice
        Then: Choice with context stored
        """
        await ensure_test_user(DEMO_USER_ID)

        choice_id = str(uuid.uuid4())
        options = json.dumps([
            {"id": 1, "text": "Morning yoga"},
            {"id": 2, "text": "Evening walk"},
            {"id": 3, "text": "Meditation"}
        ])
        chosen = json.dumps({"id": 1, "text": "Morning yoga"})

        await db.execute("""
            INSERT INTO user_choices
            (id, person_id, choice_context, options_presented, option_count, chosen_option, chosen_index, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7, NOW())
        """, choice_id, DEMO_USER_ID, "activity_recommendation", options, 3, chosen, 0)

        result = await db.fetchrow(
            "SELECT * FROM user_choices WHERE id = $1",
            choice_id
        )
        assert result is not None
        assert result["choice_context"] == "activity_recommendation"
        assert result["option_count"] == 3
        assert result["chosen_index"] == 0

        # Cleanup
        await db.execute("DELETE FROM user_choices WHERE id = $1", choice_id)

    @pytest.mark.asyncio
    async def test_choice_with_inferred_reasons(self, db, ensure_test_user):
        """
        Given: User makes choice
        When: System infers reasons
        Then: Reasons stored for learning
        """
        await ensure_test_user(DEMO_USER_ID)

        choice_id = str(uuid.uuid4())
        options = json.dumps([
            {"id": 1, "text": "Quick 5-min break"},
            {"id": 2, "text": "30-min lunch walk"}
        ])
        chosen = json.dumps({"id": 1, "text": "Quick 5-min break"})
        reasons = json.dumps({
            "time_preference": "short_duration",
            "current_schedule": "busy",
            "historical_pattern": "prefers_quick_activities"
        })

        await db.execute("""
            INSERT INTO user_choices
            (id, person_id, choice_context, options_presented, option_count, chosen_option, chosen_index, inferred_reasons, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7, $8::jsonb, NOW())
        """, choice_id, DEMO_USER_ID, "break_type", options, 2, chosen, 0, reasons)

        result = await db.fetchrow(
            "SELECT inferred_reasons FROM user_choices WHERE id = $1",
            choice_id
        )
        assert result is not None
        reasons_data = result["inferred_reasons"] if isinstance(result["inferred_reasons"], dict) else json.loads(result["inferred_reasons"])
        assert reasons_data["time_preference"] == "short_duration"

        # Cleanup
        await db.execute("DELETE FROM user_choices WHERE id = $1", choice_id)


@pytest.mark.integration
class TestRecommendationFeedbackIntegration:
    """Integration tests for recommendation feedback."""

    @pytest.mark.asyncio
    async def test_feedback_recorded(self, db, ensure_test_user):
        """
        Given: Recommendation shown
        When: User gives feedback
        Then: Feedback stored for learning
        """
        await ensure_test_user(DEMO_USER_ID)

        feedback_id = str(uuid.uuid4())
        rec_content = json.dumps({
            "text": "Try drinking warm water with lemon in the morning",
            "reason": "supports digestion and vata balance"
        })

        await db.execute("""
            INSERT INTO recommendation_feedback
            (id, person_id, recommendation_type, recommendation_domain, recommendation_content,
             feedback_type, rating, was_followed, created_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, NOW())
        """, feedback_id, DEMO_USER_ID, "wellness", "morning_routine", rec_content,
            "thumbs_up", 0.8, True)

        result = await db.fetchrow(
            "SELECT * FROM recommendation_feedback WHERE id = $1",
            feedback_id
        )
        assert result is not None
        assert result["feedback_type"] == "thumbs_up"
        assert result["was_followed"] == True
        assert float(result["rating"]) == 0.8

        # Cleanup
        await db.execute("DELETE FROM recommendation_feedback WHERE id = $1", feedback_id)

    @pytest.mark.asyncio
    async def test_negative_feedback_with_text(self, db, ensure_test_user):
        """
        Given: Recommendation shown
        When: User rejects with reason
        Then: Feedback text captured
        """
        await ensure_test_user(DEMO_USER_ID)

        feedback_id = str(uuid.uuid4())
        rec_content = json.dumps({"text": "Try hot yoga"})

        await db.execute("""
            INSERT INTO recommendation_feedback
            (id, person_id, recommendation_type, recommendation_content,
             feedback_type, feedback_text, was_followed, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, NOW())
        """, feedback_id, DEMO_USER_ID, "activity", rec_content,
            "thumbs_down", "I don't enjoy hot environments for exercise", False)

        result = await db.fetchrow(
            "SELECT feedback_type, feedback_text FROM recommendation_feedback WHERE id = $1",
            feedback_id
        )
        assert result is not None
        assert result["feedback_type"] == "thumbs_down"
        assert "hot environments" in result["feedback_text"]

        # Cleanup
        await db.execute("DELETE FROM recommendation_feedback WHERE id = $1", feedback_id)

    @pytest.mark.asyncio
    async def test_time_to_action_tracked(self, db, ensure_test_user):
        """
        Given: Recommendation made
        When: User acts on it
        Then: Time to action recorded
        """
        await ensure_test_user(DEMO_USER_ID)

        feedback_id = str(uuid.uuid4())
        rec_content = json.dumps({"text": "Take a 5-minute breathing break"})

        await db.execute("""
            INSERT INTO recommendation_feedback
            (id, person_id, recommendation_type, recommendation_content,
             feedback_type, was_followed, time_to_action_seconds, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, NOW())
        """, feedback_id, DEMO_USER_ID, "mindfulness", rec_content,
            "follow", True, 120)  # 2 minutes to act

        result = await db.fetchrow(
            "SELECT time_to_action_seconds FROM recommendation_feedback WHERE id = $1",
            feedback_id
        )
        assert result is not None
        assert result["time_to_action_seconds"] == 120

        # Cleanup
        await db.execute("DELETE FROM recommendation_feedback WHERE id = $1", feedback_id)


@pytest.mark.integration
class TestConversationStateIntegration:
    """Integration tests for conversation state."""

    @pytest.mark.asyncio
    async def test_state_stored(self, db, ensure_test_user):
        """
        Given: Conversation context
        When: State saved
        Then: State retrievable
        """
        await ensure_test_user(DEMO_USER_ID)

        state_id = str(uuid.uuid4())

        # Delete any existing state first
        await db.execute("DELETE FROM conversation_state WHERE person_id = $1", DEMO_USER_ID)

        await db.execute("""
            INSERT INTO conversation_state
            (id, person_id, last_emotion, dominant_theme, last_tone, clarity_level, energy_level, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, state_id, DEMO_USER_ID, "calm", "sleep_quality", "reflective", 0.7, 0.6)

        result = await db.fetchrow(
            "SELECT * FROM conversation_state WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result is not None
        assert result["dominant_theme"] == "sleep_quality"
        assert float(result["clarity_level"]) == 0.7

        # Cleanup
        await db.execute("DELETE FROM conversation_state WHERE id = $1", state_id)

    @pytest.mark.asyncio
    async def test_state_updated_between_turns(self, db, ensure_test_user):
        """
        Given: Existing state
        When: New turn processed
        Then: State evolves
        """
        await ensure_test_user(DEMO_USER_ID)

        state_id = str(uuid.uuid4())

        # Delete any existing state first
        await db.execute("DELETE FROM conversation_state WHERE person_id = $1", DEMO_USER_ID)

        # Initial state
        await db.execute("""
            INSERT INTO conversation_state
            (id, person_id, last_emotion, dominant_theme, energy_level, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
        """, state_id, DEMO_USER_ID, "tired", "greeting", 0.4)

        # Update state after conversation
        await db.execute("""
            UPDATE conversation_state
            SET last_emotion = $2, dominant_theme = $3, energy_level = $4, updated_at = NOW()
            WHERE person_id = $1
        """, DEMO_USER_ID, "hopeful", "goals", 0.6)

        result = await db.fetchrow(
            "SELECT last_emotion, dominant_theme, energy_level FROM conversation_state WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result["last_emotion"] == "hopeful"
        assert result["dominant_theme"] == "goals"
        assert float(result["energy_level"]) == 0.6

        # Cleanup
        await db.execute("DELETE FROM conversation_state WHERE id = $1", state_id)
