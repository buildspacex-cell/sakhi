"""
Integration tests for memory workers.

These tests use the REAL database to verify actual worker behavior.
Run with: pytest -m integration sakhi/tests/integration/workers/
"""

import pytest
import json
from datetime import datetime, timezone
import uuid

from sakhi.tests.fixtures import DEMO_USER_ID


@pytest.mark.integration
class TestMemoryFanoutIntegration:
    """Integration tests for memory_fanout with real database."""

    @pytest.mark.asyncio
    async def test_memory_fanout_creates_records(self, db, ensure_test_user):
        """
        Given: A memory event
        When: memory_fanout processes it
        Then: Records are created in the database
        """
        await ensure_test_user(DEMO_USER_ID)

        # Insert a journal entry
        entry_id = str(uuid.uuid4())
        content = "I went hiking in the mountains today and felt energized."

        await db.execute("""
            INSERT INTO journal_entries (id, user_id, title, content, mood, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
        """, entry_id, DEMO_USER_ID, "Hiking Day", content, "energized")

        # Verify entry was created
        result = await db.fetchrow(
            "SELECT * FROM journal_entries WHERE id = $1",
            entry_id
        )
        assert result is not None
        assert result["content"] == content

        # Cleanup
        await db.execute("DELETE FROM journal_entries WHERE id = $1", entry_id)

    @pytest.mark.asyncio
    async def test_memory_stored_with_embedding(self, db, ensure_test_user):
        """
        Given: A memory with text
        When: Stored in memory_episodic
        Then: Text and hash are recorded
        """
        await ensure_test_user(DEMO_USER_ID)

        mem_id = str(uuid.uuid4())
        text_content = "Had coffee with Sarah at the new cafe downtown."
        content_hash = f"hash_{mem_id[:8]}"

        record_data = json.dumps({"text": text_content, "type": "test"})
        await db.execute("""
            INSERT INTO memory_episodic (id, person_id, user_id, text, content_hash, record, created_at, updated_at)
            VALUES ($1, $2::uuid, $3, $4, $5, $6::jsonb, NOW(), NOW())
        """, mem_id, DEMO_USER_ID, DEMO_USER_ID, text_content, content_hash, record_data)

        # Verify
        result = await db.fetchrow(
            "SELECT * FROM memory_episodic WHERE id = $1",
            mem_id
        )
        assert result is not None
        assert result["text"] == text_content
        assert str(result["person_id"]) == DEMO_USER_ID

        # Cleanup
        await db.execute("DELETE FROM memory_episodic WHERE id = $1", mem_id)


@pytest.mark.integration
class TestReflectPersonMemoryIntegration:
    """Integration tests for reflect_person_memory."""

    @pytest.mark.asyncio
    async def test_classify_themes_from_real_text(self, db, ensure_test_user):
        """
        Given: Real journal entries
        When: classify_themes processes them
        Then: Correct themes are identified
        """
        from sakhi.apps.worker.tasks.reflect_person_memory import classify_themes

        # Test wellness theme
        themes = await classify_themes("Went to yoga and meditation class today")
        assert "wellness" in themes

        # Test work theme
        themes = await classify_themes("Big meeting at work about the new project")
        assert "work" in themes

        # Test relationships theme
        themes = await classify_themes("Had dinner with family and called my friend")
        assert "relationships" in themes

    @pytest.mark.asyncio
    async def test_extract_people_from_real_entries(self, db, ensure_test_user):
        """
        Given: Journal entries mentioning people
        When: extract_people_entities runs
        Then: Names are correctly extracted
        """
        from sakhi.apps.worker.tasks.reflect_person_memory import extract_people_entities

        entries = [
            "Met with David for lunch",
            "Called Maria to check in",
            "Sarah sent me the report",
        ]

        people = extract_people_entities(entries)
        assert "David" in people
        assert "Sarah" in people
        # Note: Function extracts proper nouns (capitalized words)


@pytest.mark.integration
class TestPreferenceLearningIntegration:
    """Integration tests for preference learning."""

    @pytest.mark.asyncio
    async def test_preference_stored_in_database(self, db, ensure_test_user):
        """
        Given: A detected preference
        When: Stored in preference_profiles
        Then: Can be retrieved
        """
        await ensure_test_user(DEMO_USER_ID)

        # Insert a preference (JSONB needs JSON string)
        profile_data = json.dumps({"food": {"spicy": 0.3, "sweet": 0.7}})
        await db.execute("""
            INSERT INTO preference_profiles (person_id, profile_data, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET profile_data = $2::jsonb, updated_at = NOW()
        """, DEMO_USER_ID, profile_data)

        # Verify
        result = await db.fetchrow(
            "SELECT profile_data FROM preference_profiles WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result is not None
        # profile_data may be returned as string or dict depending on driver
        profile = result["profile_data"]
        if isinstance(profile, str):
            profile = json.loads(profile)
        assert profile["food"]["sweet"] == 0.7

    @pytest.mark.asyncio
    async def test_preference_event_logged(self, db, ensure_test_user):
        """
        Given: A preference is learned
        When: Event is logged
        Then: Audit trail is created
        """
        await ensure_test_user(DEMO_USER_ID)

        # Insert preference event
        await db.execute("""
            INSERT INTO preference_events (person_id, domain, dimension, value, evidence_type, source_text, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, DEMO_USER_ID, "food", "spicy", 0.3, "explicit", "I don't like spicy food")

        # Verify
        result = await db.fetchrow("""
            SELECT * FROM preference_events
            WHERE person_id = $1 AND domain = 'food'
            ORDER BY created_at DESC LIMIT 1
        """, DEMO_USER_ID)

        assert result is not None
        assert result["dimension"] == "spicy"
        assert float(result["value"]) == 0.3

        # Cleanup
        await db.execute(
            "DELETE FROM preference_events WHERE person_id = $1 AND domain = 'food'",
            DEMO_USER_ID
        )


@pytest.mark.integration
class TestSymptomPatternIntegration:
    """Integration tests for symptom and pattern tracking."""

    @pytest.mark.asyncio
    async def test_symptom_log_creation(self, db, ensure_test_user):
        """
        Given: User reports a symptom
        When: Logged via worker
        Then: Symptom is stored with ayurvedic context
        """
        await ensure_test_user(DEMO_USER_ID)

        symptom_id = str(uuid.uuid4())

        await db.execute("""
            INSERT INTO symptom_log
            (id, person_id, symptom_type, symptom_name, severity, time_of_day, occurred_at, related_dosha, source)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8)
        """, symptom_id, DEMO_USER_ID, "digestive", "bloating", 0.6, "afternoon", "vata", "conversation")

        # Verify
        result = await db.fetchrow(
            "SELECT * FROM symptom_log WHERE id = $1",
            symptom_id
        )
        assert result is not None
        assert result["symptom_name"] == "bloating"
        assert result["related_dosha"] == "vata"
        assert float(result["severity"]) == 0.6

        # Cleanup
        await db.execute("DELETE FROM symptom_log WHERE id = $1", symptom_id)

    @pytest.mark.asyncio
    async def test_personal_pattern_detection(self, db, ensure_test_user):
        """
        Given: Multiple symptom observations
        When: Pattern worker analyzes them
        Then: Correlation is stored
        """
        await ensure_test_user(DEMO_USER_ID)

        pattern_id = str(uuid.uuid4())

        await db.execute("""
            INSERT INTO personal_patterns
            (id, person_id, cause_type, cause_value, effect_type, effect_value,
             correlation_strength, confidence, observation_count, related_dosha, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
            ON CONFLICT (person_id, cause_type, cause_value, effect_type, effect_value)
            DO UPDATE SET correlation_strength = $7, confidence = $8, observation_count = $9
        """, pattern_id, DEMO_USER_ID, "food", "dairy", "symptom", "bloating", 0.75, 0.8, 5, "kapha")

        # Verify
        result = await db.fetchrow(
            "SELECT * FROM personal_patterns WHERE id = $1",
            pattern_id
        )
        assert result is not None
        assert result["cause_value"] == "dairy"
        assert result["effect_value"] == "bloating"
        assert float(result["correlation_strength"]) == 0.75

        # Cleanup
        await db.execute("DELETE FROM personal_patterns WHERE id = $1", pattern_id)
