"""
Integration tests for personal model workers.

Tests actual database operations for:
- Personal model state
- Personal embeddings
- Facts storage
- Goals tracking
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
import uuid

from sakhi.tests.fixtures import DEMO_USER_ID


@pytest.mark.integration
class TestPersonalModelIntegration:
    """Integration tests for personal model storage."""

    @pytest.mark.asyncio
    async def test_personal_model_created(self, db, ensure_test_user):
        """
        Given: New user
        When: Personal model initialized
        Then: Core states are stored
        """
        await ensure_test_user(DEMO_USER_ID)

        data = json.dumps({"constitutional_type": "vata-pitta"})
        body_state = json.dumps({"energy": 0.7, "digestion": "balanced"})
        mind_state = json.dumps({"focus": 0.8, "clarity": "high"})

        await db.execute("""
            INSERT INTO personal_model (person_id, data, body_state, mind_state, updated_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET data = $2::jsonb, body_state = $3::jsonb, mind_state = $4::jsonb, updated_at = NOW()
        """, DEMO_USER_ID, data, body_state, mind_state)

        result = await db.fetchrow(
            "SELECT * FROM personal_model WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result is not None
        body = result["body_state"] if isinstance(result["body_state"], dict) else json.loads(result["body_state"])
        assert body["energy"] == 0.7

    @pytest.mark.asyncio
    async def test_personal_model_states_update(self, db, ensure_test_user):
        """
        Given: Existing personal model
        When: States are updated
        Then: New values persisted
        """
        await ensure_test_user(DEMO_USER_ID)

        # First ensure model exists
        await db.execute("""
            INSERT INTO personal_model (person_id, data, updated_at)
            VALUES ($1, '{}'::jsonb, NOW())
            ON CONFLICT (person_id) DO NOTHING
        """, DEMO_USER_ID)

        # Update emotion and goals state
        emotion_state = json.dumps({"dominant": "calm", "valence": 0.6})
        goals_state = json.dumps({"active_count": 3, "completion_rate": 0.7})

        await db.execute("""
            UPDATE personal_model
            SET emotion_state = $2::jsonb, goals_state = $3::jsonb, updated_at = NOW()
            WHERE person_id = $1
        """, DEMO_USER_ID, emotion_state, goals_state)

        result = await db.fetchrow(
            "SELECT emotion_state, goals_state FROM personal_model WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result is not None
        emotion = result["emotion_state"] if isinstance(result["emotion_state"], dict) else json.loads(result["emotion_state"])
        assert emotion["dominant"] == "calm"

    @pytest.mark.asyncio
    async def test_rhythm_state_in_personal_model(self, db, ensure_test_user):
        """
        Given: User has rhythm patterns
        When: Stored in personal_model.rhythm_state
        Then: Rhythm data is queryable
        """
        await ensure_test_user(DEMO_USER_ID)

        rhythm_state = json.dumps({
            "current_phase": "active",
            "chronotype": "morning_lark",
            "optimal_hours": [9, 10, 11, 14, 15]
        })

        await db.execute("""
            UPDATE personal_model
            SET rhythm_state = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
        """, DEMO_USER_ID, rhythm_state)

        result = await db.fetchrow(
            "SELECT rhythm_state FROM personal_model WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result is not None
        rhythm = result["rhythm_state"] if isinstance(result["rhythm_state"], dict) else json.loads(result["rhythm_state"])
        assert rhythm["chronotype"] == "morning_lark"


@pytest.mark.integration
class TestPersonalEmbeddingsIntegration:
    """Integration tests for personal embeddings storage."""

    @pytest.mark.asyncio
    async def test_embedding_stored(self, db, ensure_test_user):
        """
        Given: Text content
        When: Embedding stored
        Then: Label and content accessible
        """
        await ensure_test_user(DEMO_USER_ID)

        embed_id = str(uuid.uuid4())
        label = "wellness_summary"
        content = "User prefers morning exercise and meditation."

        # Note: We're not storing actual vector here, just testing the text fields
        await db.execute("""
            INSERT INTO personal_embeddings (id, person_id, label, content, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (person_id, label) DO UPDATE
            SET content = $4, updated_at = NOW()
        """, embed_id, DEMO_USER_ID, label, content)

        result = await db.fetchrow(
            "SELECT * FROM personal_embeddings WHERE person_id = $1 AND label = $2",
            DEMO_USER_ID, label
        )
        assert result is not None
        assert result["content"] == content

        # Cleanup
        await db.execute("DELETE FROM personal_embeddings WHERE id = $1", embed_id)

    @pytest.mark.asyncio
    async def test_multiple_embeddings_per_person(self, db, ensure_test_user):
        """
        Given: Multiple labels
        When: Stored separately
        Then: All retrievable
        """
        await ensure_test_user(DEMO_USER_ID)

        labels = ["body_summary", "mind_summary", "goals_summary"]
        embed_ids = []

        for label in labels:
            embed_id = str(uuid.uuid4())
            embed_ids.append(embed_id)
            content = f"Summary for {label}"

            await db.execute("""
                INSERT INTO personal_embeddings (id, person_id, label, content, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (person_id, label) DO UPDATE
                SET id = $1, content = $4, updated_at = NOW()
            """, embed_id, DEMO_USER_ID, label, content)

        results = await db.fetch(
            "SELECT label FROM personal_embeddings WHERE person_id = $1",
            DEMO_USER_ID
        )

        stored_labels = [r["label"] for r in results]
        for label in labels:
            assert label in stored_labels

        # Cleanup
        for embed_id in embed_ids:
            await db.execute("DELETE FROM personal_embeddings WHERE id = $1", embed_id)


@pytest.mark.integration
class TestFactsIntegration:
    """Integration tests for facts storage."""

    @pytest.mark.asyncio
    async def test_fact_stored(self, db, ensure_test_user):
        """
        Given: User fact detected
        When: Stored in facts table
        Then: Fact is queryable by scope and key
        """
        await ensure_test_user(DEMO_USER_ID)

        fact_id = str(uuid.uuid4())
        scope = "preferences"
        key = "wake_time"
        value = json.dumps({"hour": 6, "minute": 30, "consistency": 0.9})

        await db.execute("""
            INSERT INTO facts (id, person_id, scope, key, value, confidence, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, NOW(), NOW())
            ON CONFLICT (person_id, scope, key) DO UPDATE
            SET value = $5::jsonb, confidence = $6, updated_at = NOW()
        """, fact_id, DEMO_USER_ID, scope, key, value, 0.85)

        result = await db.fetchrow(
            "SELECT * FROM facts WHERE person_id = $1 AND scope = $2 AND key = $3",
            DEMO_USER_ID, scope, key
        )
        assert result is not None
        assert float(result["confidence"]) == 0.85

        # Cleanup
        await db.execute("DELETE FROM facts WHERE id = $1", fact_id)

    @pytest.mark.asyncio
    async def test_multiple_facts_same_scope(self, db, ensure_test_user):
        """
        Given: Multiple facts in same scope
        When: Queried by scope
        Then: All facts returned
        """
        await ensure_test_user(DEMO_USER_ID)

        scope = "dietary"
        facts_data = [
            ("avoids_gluten", {"value": True, "since": "2024-01"}),
            ("prefers_organic", {"value": True, "priority": "high"}),
            ("caffeine_limit", {"cups_per_day": 2}),
        ]
        fact_ids = []

        for key, value in facts_data:
            fact_id = str(uuid.uuid4())
            fact_ids.append(fact_id)

            await db.execute("""
                INSERT INTO facts (id, person_id, scope, key, value, confidence, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, NOW(), NOW())
            """, fact_id, DEMO_USER_ID, scope, key, json.dumps(value), 0.8)

        results = await db.fetch(
            "SELECT key FROM facts WHERE person_id = $1 AND scope = $2",
            DEMO_USER_ID, scope
        )

        stored_keys = [r["key"] for r in results]
        for key, _ in facts_data:
            assert key in stored_keys

        # Cleanup
        for fact_id in fact_ids:
            await db.execute("DELETE FROM facts WHERE id = $1", fact_id)


@pytest.mark.integration
class TestGoalsIntegration:
    """Integration tests for goals tracking."""

    @pytest.mark.asyncio
    async def test_goal_created(self, db, ensure_test_user):
        """
        Given: User sets a goal
        When: Goal stored
        Then: Goal with metadata persisted
        """
        await ensure_test_user(DEMO_USER_ID)

        goal_id = str(uuid.uuid4())

        await db.execute("""
            INSERT INTO goals (id, person_id, title, description, horizon, status, progress, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, goal_id, DEMO_USER_ID, "Improve sleep quality", "Get 7+ hours of restful sleep", "monthly", "active", 0.3)

        result = await db.fetchrow(
            "SELECT * FROM goals WHERE id = $1",
            goal_id
        )
        assert result is not None
        assert result["title"] == "Improve sleep quality"
        assert result["status"] == "active"
        assert float(result["progress"]) == 0.3

        # Cleanup
        await db.execute("DELETE FROM goals WHERE id = $1", goal_id)

    @pytest.mark.asyncio
    async def test_goal_progress_updated(self, db, ensure_test_user):
        """
        Given: Active goal
        When: Progress made
        Then: Progress value updated
        """
        await ensure_test_user(DEMO_USER_ID)

        goal_id = str(uuid.uuid4())

        # Create goal
        await db.execute("""
            INSERT INTO goals (id, person_id, title, horizon, status, progress, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, goal_id, DEMO_USER_ID, "Daily meditation", "weekly", "active", 0.2)

        # Update progress
        await db.execute("""
            UPDATE goals
            SET progress = $2, evolution_score = $3, last_revised = NOW(), updated_at = NOW()
            WHERE id = $1
        """, goal_id, 0.7, 0.85)

        result = await db.fetchrow(
            "SELECT progress, evolution_score FROM goals WHERE id = $1",
            goal_id
        )
        assert result is not None
        assert float(result["progress"]) == 0.7
        assert float(result["evolution_score"]) == 0.85

        # Cleanup
        await db.execute("DELETE FROM goals WHERE id = $1", goal_id)

    @pytest.mark.asyncio
    async def test_hierarchical_goals(self, db, ensure_test_user):
        """
        Given: Parent goal
        When: Child goals created
        Then: Hierarchy maintained
        """
        await ensure_test_user(DEMO_USER_ID)

        parent_id = str(uuid.uuid4())
        child_ids = [str(uuid.uuid4()) for _ in range(2)]

        # Create parent goal
        await db.execute("""
            INSERT INTO goals (id, person_id, title, horizon, status, progress, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, parent_id, DEMO_USER_ID, "Better health", "yearly", "active", 0.0)

        # Create child goals
        child_titles = ["Exercise 3x/week", "Eat more vegetables"]
        for child_id, title in zip(child_ids, child_titles):
            await db.execute("""
                INSERT INTO goals (id, person_id, parent_goal_id, title, horizon, status, progress, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """, child_id, DEMO_USER_ID, parent_id, title, "monthly", "active", 0.0)

        # Query children
        children = await db.fetch(
            "SELECT id, title FROM goals WHERE parent_goal_id = $1",
            parent_id
        )
        assert len(children) == 2

        # Cleanup
        for child_id in child_ids:
            await db.execute("DELETE FROM goals WHERE id = $1", child_id)
        await db.execute("DELETE FROM goals WHERE id = $1", parent_id)


@pytest.mark.integration
class TestInsightsQueueIntegration:
    """Integration tests for insights queue."""

    @pytest.mark.asyncio
    async def test_insight_queued(self, db, ensure_test_user):
        """
        Given: Insight generated
        When: Added to queue
        Then: Insight retrievable with priority
        """
        await ensure_test_user(DEMO_USER_ID)

        insight_id = str(uuid.uuid4())
        insight_data = json.dumps({
            "text": "You've been consistently exercising in the morning this week!",
            "type": "pattern_recognition",
            "confidence": 0.9
        })

        await db.execute("""
            INSERT INTO insights_queue (id, person_id, insight, priority, timing_hint, delivered, created_at)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6, NOW())
        """, insight_id, DEMO_USER_ID, insight_data, "high", "morning", False)

        result = await db.fetchrow(
            "SELECT * FROM insights_queue WHERE id = $1",
            insight_id
        )
        assert result is not None
        assert result["priority"] == "high"
        assert result["delivered"] == False

        # Cleanup
        await db.execute("DELETE FROM insights_queue WHERE id = $1", insight_id)

    @pytest.mark.asyncio
    async def test_insight_delivered(self, db, ensure_test_user):
        """
        Given: Queued insight
        When: Delivered to user
        Then: Marked as delivered
        """
        await ensure_test_user(DEMO_USER_ID)

        insight_id = str(uuid.uuid4())
        insight_data = json.dumps({"text": "Time for your afternoon break!"})

        # Queue insight
        await db.execute("""
            INSERT INTO insights_queue (id, person_id, insight, priority, delivered, created_at)
            VALUES ($1, $2, $3::jsonb, $4, $5, NOW())
        """, insight_id, DEMO_USER_ID, insight_data, "medium", False)

        # Mark as delivered
        await db.execute("""
            UPDATE insights_queue SET delivered = TRUE WHERE id = $1
        """, insight_id)

        result = await db.fetchrow(
            "SELECT delivered FROM insights_queue WHERE id = $1",
            insight_id
        )
        assert result["delivered"] == True

        # Cleanup
        await db.execute("DELETE FROM insights_queue WHERE id = $1", insight_id)
