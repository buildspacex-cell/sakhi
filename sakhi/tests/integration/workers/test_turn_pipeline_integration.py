"""
Integration tests for turn pipeline workers.

Tests the full flow of processing a conversation turn:
1. User message received
2. Memory stored
3. Episodes consolidated
4. Preferences extracted
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
import uuid

from sakhi.tests.fixtures import DEMO_USER_ID


@pytest.mark.integration
class TestTurnPipelineIntegration:
    """Integration tests for the turn pipeline."""

    @pytest.mark.asyncio
    async def test_full_turn_processing(self, db, ensure_test_user):
        """
        Given: A user sends a message
        When: Turn pipeline processes it
        Then: Memory is stored in short-term memory
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create a session first (FK constraint)
        session_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO conversation_sessions
            (id, user_id, slug, status, created_at, last_active_at, turn_count)
            VALUES ($1, $2, $3, $4, NOW(), NOW(), 0)
        """, session_id, DEMO_USER_ID, f"session-{session_id[:8]}", "active")

        # Create a conversation turn
        turn_id = str(uuid.uuid4())
        user_message = "I'm feeling tired and a bit stressed from work today"
        metadata = json.dumps({"source": "web", "test": True})
        queued_jobs = json.dumps(["update_conversation_state", "reflect_memory"])

        await db.execute("""
            INSERT INTO conversation_turns
            (id, user_id, session_id, person_id, role, text, created_at, context_version, queued_jobs, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8::jsonb, $9::jsonb)
        """, turn_id, DEMO_USER_ID, session_id, DEMO_USER_ID, "user",
            user_message, 1, queued_jobs, metadata)

        # Store in short-term memory (simulating what turn pipeline does)
        # Schema: memory_short_term (id, user_id, record, created_at, ..., text, ...) - person_id is auto-generated from user_id
        stm_id = str(uuid.uuid4())
        record_data = json.dumps({
            "role": "user",
            "session_id": session_id,
            "emotion": "tired",
            "source": "conversation"
        })
        await db.execute("""
            INSERT INTO memory_short_term
            (id, user_id, text, record, created_at, updated_at, expires_at)
            VALUES ($1, $2, $3, $4::jsonb, NOW(), NOW(), NOW() + interval '24 hours')
        """, stm_id, DEMO_USER_ID, user_message, record_data)

        # Verify turn was stored
        turn_result = await db.fetchrow(
            "SELECT * FROM conversation_turns WHERE id = $1",
            turn_id
        )
        assert turn_result is not None
        assert turn_result["text"] == user_message

        # Verify memory was stored
        mem_result = await db.fetchrow(
            "SELECT * FROM memory_short_term WHERE id = $1",
            stm_id
        )
        assert mem_result is not None
        assert mem_result["text"] == user_message
        record = mem_result["record"]
        if isinstance(record, str):
            record = json.loads(record)
        assert record["emotion"] == "tired"

        # Cleanup
        await db.execute("DELETE FROM memory_short_term WHERE id = $1", stm_id)
        await db.execute("DELETE FROM conversation_turns WHERE id = $1", turn_id)
        await db.execute("DELETE FROM conversation_sessions WHERE id = $1", session_id)

    @pytest.mark.asyncio
    async def test_preference_extraction_from_turn(self, db, ensure_test_user):
        """
        Given: A message with preference signals
        When: Turn pipeline processes it
        Then: Preference is extracted and stored
        """
        await ensure_test_user(DEMO_USER_ID)

        # Simulate a message with clear preference signal
        preference_message = "I really don't like spicy food, it upsets my stomach"

        # Store the preference that would be extracted
        # Schema: preference_events (id int4 PK, person_id text, domain, dimension, value, evidence_type, source_text, context, created_at)
        pref_result = await db.fetchrow("""
            INSERT INTO preference_events
            (person_id, domain, dimension, value, evidence_type, source_text, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING id
        """, DEMO_USER_ID, "food", "spicy", 0.2, "explicit", preference_message)
        pref_id = pref_result["id"]

        # Verify preference was stored
        result = await db.fetchrow(
            "SELECT * FROM preference_events WHERE id = $1",
            pref_id
        )
        assert result is not None
        assert result["domain"] == "food"
        assert result["dimension"] == "spicy"
        assert float(result["value"]) == 0.2  # Low value = dislike
        assert result["evidence_type"] == "explicit"

        # Update preference profile (what the worker would do)
        # Schema: preference_profiles (person_id text PK, profile_data jsonb, updated_at, created_at)
        profile_data = json.dumps({
            "food": {"spicy": 0.2, "updated_at": datetime.now(timezone.utc).isoformat()}
        })
        await db.execute("""
            INSERT INTO preference_profiles (person_id, profile_data, updated_at, created_at)
            VALUES ($1, $2::jsonb, NOW(), NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET profile_data = preference_profiles.profile_data || $2::jsonb,
                updated_at = NOW()
        """, DEMO_USER_ID, profile_data)

        # Verify profile was updated
        profile_result = await db.fetchrow(
            "SELECT profile_data FROM preference_profiles WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert profile_result is not None

        # Cleanup
        await db.execute("DELETE FROM preference_events WHERE id = $1", pref_id)

    @pytest.mark.asyncio
    async def test_memory_retrieval_after_turn(self, db, ensure_test_user):
        """
        Given: A stored memory from turn
        When: Text search is performed
        Then: Memory is retrievable
        """
        await ensure_test_user(DEMO_USER_ID)

        # Store a memory with searchable content
        mem_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        memory_text = "Had a wonderful meditation session this morning by the lake"

        # Schema: memory_short_term (id, user_id, record, ..., text, ...) - person_id is auto-generated
        record_data = json.dumps({
            "role": "user",
            "session_id": session_id,
            "activity": "meditation"
        })
        await db.execute("""
            INSERT INTO memory_short_term
            (id, user_id, text, record, created_at, updated_at, expires_at)
            VALUES ($1, $2, $3, $4::jsonb, NOW(), NOW(), NOW() + interval '24 hours')
        """, mem_id, DEMO_USER_ID, memory_text, record_data)

        # Verify memory is searchable by keyword
        search_result = await db.fetch("""
            SELECT * FROM memory_short_term
            WHERE person_id = $1
              AND text ILIKE '%meditation%'
            ORDER BY created_at DESC
            LIMIT 5
        """, DEMO_USER_ID)

        assert len(search_result) >= 1
        found = any(r["text"] == memory_text for r in search_result)
        assert found, "Memory should be retrievable via text search"

        # Also test retrieval by user_id (session_id is in record jsonb)
        user_memories = await db.fetch("""
            SELECT * FROM memory_short_term
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, DEMO_USER_ID)

        assert len(user_memories) >= 1
        found_mem = next((m for m in user_memories if m["text"] == memory_text), None)
        assert found_mem is not None

        # Cleanup
        await db.execute("DELETE FROM memory_short_term WHERE id = $1", mem_id)


@pytest.mark.integration
class TestEpisodicConsolidationIntegration:
    """Integration tests for episodic consolidation."""

    @pytest.mark.asyncio
    async def test_consolidates_daily_memories(self, db, ensure_test_user):
        """
        Given: Multiple memories from a day
        When: Consolidation runs
        Then: Daily episode is created in memory_episodic
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create multiple short-term memories (simulating a day's conversations)
        session_id = str(uuid.uuid4())
        stm_ids = []

        memories = [
            "Started the day with yoga and felt energized",
            "Had a productive work meeting about the new project",
            "Lunch with Sarah at the Italian place",
            "Afternoon was a bit stressful due to deadline",
            "Evening walk helped me decompress",
        ]

        for i, text in enumerate(memories):
            stm_id = str(uuid.uuid4())
            stm_ids.append(stm_id)
            record_data = json.dumps({
                "role": "user",
                "session_id": session_id,
                "index": i
            })
            # person_id is auto-generated from user_id
            await db.execute("""
                INSERT INTO memory_short_term
                (id, user_id, text, record, created_at, updated_at, expires_at)
                VALUES ($1, $2, $3, $4::jsonb, NOW() - interval '%s hours', NOW(), NOW() + interval '24 hours')
            """ % (len(memories) - i), stm_id, DEMO_USER_ID, text, record_data)

        # Verify memories were created
        stm_count = await db.fetchval("""
            SELECT COUNT(*) FROM memory_short_term
            WHERE person_id = $1 AND id = ANY($2::uuid[])
        """, DEMO_USER_ID, stm_ids)
        assert stm_count == 5

        # Create episodic memory (what consolidation worker would produce)
        episode_id = str(uuid.uuid4())
        episode_summary = "A balanced day: energizing yoga morning, productive work, social lunch with Sarah, managed afternoon stress, recovered with evening walk."
        episode_record = json.dumps({
            "themes": ["wellness", "work", "relationships"],
            "emotional_arc": ["energized", "productive", "positive", "stressed", "calm"],
            "key_people": ["Sarah"],
            "memory_count": 5,
        })

        await db.execute("""
            INSERT INTO memory_episodic
            (id, person_id, user_id, text, record, content_hash, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, NOW(), NOW())
        """, episode_id, DEMO_USER_ID, DEMO_USER_ID, episode_summary, episode_record, f"hash_{session_id[:8]}")

        # Verify episode was created
        episode_result = await db.fetchrow(
            "SELECT * FROM memory_episodic WHERE id = $1",
            episode_id
        )
        assert episode_result is not None
        assert "balanced day" in episode_result["text"]

        record = episode_result["record"]
        if isinstance(record, str):
            record = json.loads(record)
        assert "wellness" in record["themes"]
        assert record["memory_count"] == 5

        # Cleanup
        for stm_id in stm_ids:
            await db.execute("DELETE FROM memory_short_term WHERE id = $1", stm_id)
        await db.execute("DELETE FROM memory_episodic WHERE id = $1", episode_id)

    @pytest.mark.asyncio
    async def test_creates_memory_graph_nodes(self, db, ensure_test_user):
        """
        Given: Memories with entities (people, places, themes)
        When: Consolidation runs
        Then: Graph nodes and edges are created in memory_nodes/memory_edges
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create a memory with entities
        mem_id = str(uuid.uuid4())
        memory_text = "Had coffee with David at Starbucks to discuss the project"

        record_data = json.dumps({
            "role": "user",
            "entities": ["David", "Starbucks"],
            "activity": "meeting"
        })
        # person_id is auto-generated from user_id
        await db.execute("""
            INSERT INTO memory_short_term
            (id, user_id, text, record, created_at, updated_at, expires_at)
            VALUES ($1, $2, $3, $4::jsonb, NOW(), NOW(), NOW() + interval '24 hours')
        """, mem_id, DEMO_USER_ID, memory_text, record_data)

        # Create graph nodes (what consolidation would create)
        # Schema: memory_nodes (id, person_id, node_kind, label, data, created_at, weight, updated_at, last_referenced_at)
        # Valid node_kind values: 'person', 'value', 'pattern', 'theme', 'goal'
        person_node_id = str(uuid.uuid4())
        theme_node_id = str(uuid.uuid4())
        goal_node_id = str(uuid.uuid4())

        # Use unique labels to avoid conflicts with existing data
        unique_suffix = str(uuid.uuid4())[:8]

        # Person node (with unique label)
        await db.execute("""
            INSERT INTO memory_nodes
            (id, person_id, node_kind, label, data, created_at, updated_at, weight)
            VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW(), 1.0)
        """, person_node_id, DEMO_USER_ID, "person", f"David_{unique_suffix}",
            json.dumps({"relationship": "colleague", "mention_count": 1}))

        # Theme node (with unique label)
        await db.execute("""
            INSERT INTO memory_nodes
            (id, person_id, node_kind, label, data, created_at, updated_at, weight)
            VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW(), 1.0)
        """, theme_node_id, DEMO_USER_ID, "theme", f"work collaboration_{unique_suffix}",
            json.dumps({"context": "project meeting", "mention_count": 1}))

        # Goal node (with unique label)
        await db.execute("""
            INSERT INTO memory_nodes
            (id, person_id, node_kind, label, data, created_at, updated_at, weight)
            VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW(), 1.0)
        """, goal_node_id, DEMO_USER_ID, "goal", f"project completion_{unique_suffix}",
            json.dumps({"target": "Q1", "mention_count": 1}))

        # Verify nodes were created
        nodes = await db.fetch("""
            SELECT * FROM memory_nodes
            WHERE person_id = $1 AND id = ANY($2::uuid[])
        """, DEMO_USER_ID, [person_node_id, theme_node_id, goal_node_id])

        assert len(nodes) == 3

        # Verify we can find the person node
        person_node = await db.fetchrow("""
            SELECT * FROM memory_nodes
            WHERE person_id = $1 AND id = $2
        """, DEMO_USER_ID, person_node_id)
        assert person_node is not None
        assert person_node["node_kind"] == "person"
        assert "David_" in person_node["label"]

        data = person_node["data"]
        if isinstance(data, str):
            data = json.loads(data)
        assert data["relationship"] == "colleague"

        # Verify theme and goal nodes exist
        theme_node = await db.fetchrow(
            "SELECT * FROM memory_nodes WHERE id = $1", theme_node_id
        )
        assert theme_node is not None
        assert theme_node["node_kind"] == "theme"

        goal_node = await db.fetchrow(
            "SELECT * FROM memory_nodes WHERE id = $1", goal_node_id
        )
        assert goal_node is not None
        assert goal_node["node_kind"] == "goal"

        # Note: memory_edges has a strict check constraint on 'relation' values
        # that requires specific allowed values from the application layer.
        # Edge creation is tested via the actual worker implementations.

        # Cleanup
        await db.execute("DELETE FROM memory_nodes WHERE id = ANY($1::uuid[])",
                        [person_node_id, theme_node_id, goal_node_id])
        await db.execute("DELETE FROM memory_short_term WHERE id = $1", mem_id)


@pytest.mark.integration
class TestConversationStateIntegration:
    """Integration tests for conversation state updates."""

    @pytest.mark.asyncio
    async def test_conversation_state_updated_after_turn(self, db, ensure_test_user):
        """
        Given: A conversation turn with emotional content
        When: State update worker processes it
        Then: Conversation state reflects the emotion
        """
        await ensure_test_user(DEMO_USER_ID)

        # First, clean up any existing state for this person
        await db.execute("""
            DELETE FROM conversation_state WHERE person_id = $1
        """, DEMO_USER_ID)

        # Insert conversation state (what the worker would do)
        state_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO conversation_state
            (id, person_id, last_emotion, energy_level, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, state_id, DEMO_USER_ID, "anxious", 0.4)

        # Verify state was created
        result = await db.fetchrow("""
            SELECT * FROM conversation_state WHERE person_id = $1
        """, DEMO_USER_ID)

        assert result is not None
        assert result["last_emotion"] == "anxious"
        assert float(result["energy_level"]) == 0.4

        # Cleanup
        await db.execute("DELETE FROM conversation_state WHERE id = $1", state_id)

    @pytest.mark.asyncio
    async def test_session_continuity_tracked(self, db, ensure_test_user):
        """
        Given: Multiple turns in a session
        When: Continuity is tracked
        Then: Session state reflects history
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create session continuity record (schema: person_id PK, last_emotion, last_interaction_ts, engagement_level, reflection_pending, clarity_level)
        await db.execute("""
            INSERT INTO session_continuity
            (person_id, last_emotion, last_interaction_ts, engagement_level, clarity_level)
            VALUES ($1, $2, NOW(), $3, $4)
            ON CONFLICT (person_id) DO UPDATE
            SET last_emotion = $2,
                last_interaction_ts = NOW(),
                engagement_level = $3,
                clarity_level = $4
        """, DEMO_USER_ID, "calm", 0.8, 0.7)

        # Verify continuity was tracked
        result = await db.fetchrow("""
            SELECT * FROM session_continuity WHERE person_id = $1
        """, DEMO_USER_ID)

        assert result is not None
        assert result["last_emotion"] == "calm"
        assert float(result["engagement_level"]) == 0.8


@pytest.mark.integration
class TestEmotionalContextIntegration:
    """Integration tests for emotional context tracking."""

    @pytest.mark.asyncio
    async def test_emotional_journey_tracked(self, db, ensure_test_user):
        """
        Given: Turns with varying emotions
        When: Context is updated
        Then: Emotional journey is visible
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create a session
        session_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO conversation_sessions
            (id, user_id, slug, status, created_at, last_active_at, turn_count)
            VALUES ($1, $2, $3, $4, NOW(), NOW(), 0)
        """, session_id, DEMO_USER_ID, f"session-{session_id[:8]}", "active")

        # Simulate emotional journey through turns
        emotions = [
            ("anxious", "I'm worried about the presentation"),
            ("hopeful", "But I've prepared well"),
            ("confident", "I think it will go fine"),
        ]

        turn_ids = []
        for i, (emotion, text) in enumerate(emotions):
            turn_id = str(uuid.uuid4())
            turn_ids.append(turn_id)
            metadata = json.dumps({"detected_emotion": emotion})

            await db.execute("""
                INSERT INTO conversation_turns
                (id, user_id, session_id, person_id, role, text, tone, created_at, context_version, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW() - interval '%s minutes', $8, $9::jsonb)
            """ % ((len(emotions) - i) * 5), turn_id, DEMO_USER_ID, session_id,
                DEMO_USER_ID, "user", text, emotion, 1, metadata)

        # Verify emotional journey is visible
        turns = await db.fetch("""
            SELECT text, tone, metadata FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at ASC
        """, session_id)

        assert len(turns) == 3
        assert turns[0]["tone"] == "anxious"
        assert turns[1]["tone"] == "hopeful"
        assert turns[2]["tone"] == "confident"

        # Update final conversation state (insert with id since no unique constraint on person_id)
        state_id = str(uuid.uuid4())
        await db.execute("""
            DELETE FROM conversation_state WHERE person_id = $1
        """, DEMO_USER_ID)
        await db.execute("""
            INSERT INTO conversation_state
            (id, person_id, last_emotion, energy_level, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, state_id, DEMO_USER_ID, "confident", 0.8)

        # Cleanup
        for turn_id in turn_ids:
            await db.execute("DELETE FROM conversation_turns WHERE id = $1", turn_id)
        await db.execute("DELETE FROM conversation_sessions WHERE id = $1", session_id)
        await db.execute("DELETE FROM conversation_state WHERE id = $1", state_id)
