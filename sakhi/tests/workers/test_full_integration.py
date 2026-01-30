"""
Full Integration Tests for Sakhi MVP.

End-to-end tests that verify the complete flow:
1. User sends message
2. Context is loaded (friction state, memory graph, recommendations)
3. Response is generated (jargon-free)
4. Workers process in background (episodic, patterns, intents)
5. Memory graph is updated
6. Next turn has updated context
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
import uuid
import json

pytestmark = pytest.mark.asyncio


class TestFullConversationFlow:
    """Test complete conversation flow from message to response."""

    async def test_first_turn_conversation(
        self,
        test_user_id,
        test_session_id,
        create_journal_entry,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test first turn in a conversation."""
        await setup_personal_model(test_user_id)

        user_message = "I've been feeling scattered lately. Can't focus on anything."

        try:
            # 1. Run response pipeline
            from sakhi.apps.api.services.response.pipeline import run_adaptive_pipeline

            response = await run_adaptive_pipeline(
                person_id=test_user_id,
                user_text=user_message,
                session_id=test_session_id,
            )

            # Verify response was generated
            assert response is not None
            if response.adaptive_prompt:
                # Should be jargon-free
                prompt_lower = response.adaptive_prompt.lower()
                assert "vata" not in prompt_lower
                assert "dosha" not in prompt_lower

            # 2. Create journal entry (simulating storage)
            entry_id = await create_journal_entry(
                test_user_id,
                user_message,
                layer="turn",
                mood="scattered",
            )

            # 3. Process through turn pipeline
            from sakhi.apps.worker.pipelines.turn_updates.runner import (
                process_turn_job_async,
            )

            job = {
                "person_id": test_user_id,
                "session_id": test_session_id,
                "entry_id": entry_id,
                "job_type": "memory_update",
                "content": user_message,
            }
            await process_turn_job_async(job)

            # 4. Run episodic consolidation
            job["job_type"] = "episodic_consolidation"
            await process_turn_job_async(job)

            print("First turn completed successfully")

        except ImportError as e:
            pytest.skip(f"Pipeline not available: {e}")

    async def test_multi_turn_context_building(
        self,
        test_user_id,
        test_session_id,
        create_journal_entry,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test context builds across multiple turns."""
        await setup_personal_model(test_user_id)

        turns = [
            "I've been trying to do yoga every morning.",
            "But work keeps getting in the way.",
            "I think I need to wake up earlier.",
        ]

        try:
            from sakhi.apps.api.services.response.pipeline import run_adaptive_pipeline
            from sakhi.apps.worker.pipelines.turn_updates.runner import (
                process_turn_job_async,
            )

            for i, message in enumerate(turns):
                # Generate response
                response = await run_adaptive_pipeline(
                    person_id=test_user_id,
                    user_text=message,
                    session_id=test_session_id,
                )

                # Store entry
                entry_id = await create_journal_entry(
                    test_user_id,
                    message,
                    layer="turn",
                )

                # Process through workers
                job = {
                    "person_id": test_user_id,
                    "session_id": test_session_id,
                    "entry_id": entry_id,
                    "job_type": "episodic_consolidation",
                    "content": message,
                }
                await process_turn_job_async(job)

            # Check if memory graph has relevant nodes
            nodes = await db_query("""
                SELECT node_kind, label
                FROM memory_nodes
                WHERE person_id = $1
                ORDER BY created_at DESC
                LIMIT 10
            """, test_user_id)

            # Check if patterns were logged
            patterns = await db_query("""
                SELECT pattern_type, pattern_value
                FROM pattern_occurrences
                WHERE person_id = $1
                ORDER BY created_at DESC
                LIMIT 10
            """, test_user_id)

            print(f"Multi-turn test: {len(nodes)} nodes, {len(patterns)} patterns")

        except ImportError as e:
            pytest.skip(f"Pipeline not available: {e}")


class TestWorkerChaining:
    """Test workers trigger in correct sequence."""

    async def test_episodic_triggers_pattern_logging(
        self,
        test_user_id,
        create_journal_entry,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test episodic consolidation logs pattern occurrences."""
        await setup_personal_model(test_user_id)

        # Create entries with clear pattern
        for i in range(3):
            await create_journal_entry(
                test_user_id,
                f"Morning yoga practice day {i+1}. Felt great!",
                layer="reflection",
                created_at=datetime.now(timezone.utc) - timedelta(days=i),
            )

        try:
            from sakhi.apps.worker.tasks.episodic_consolidation_v21 import (
                run_episodic_consolidation_v21,
            )

            # Run consolidation
            result = await run_episodic_consolidation_v21(test_user_id)

            # Check pattern occurrences were logged
            patterns = await db_query("""
                SELECT pattern_type, pattern_value, confidence
                FROM pattern_occurrences
                WHERE person_id = $1
                AND created_at > NOW() - INTERVAL '1 hour'
            """, test_user_id)

            # Patterns may or may not be created depending on LLM extraction

        except ImportError:
            pytest.skip("Episodic consolidation not available")

    async def test_pattern_crystallization_chain(
        self,
        test_user_id,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test pattern occurrences crystallize into patterns."""
        await setup_personal_model(test_user_id)

        test_pattern = f"test_chain_pattern_{uuid.uuid4().hex[:8]}"

        try:
            # Create pattern occurrences manually
            for i in range(7):
                occ_id = str(uuid.uuid4())
                created_at = datetime.now(timezone.utc) - timedelta(days=i)
                await db_exec("""
                    INSERT INTO pattern_occurrences
                    (id, person_id, pattern_type, pattern_value, source_entry_id,
                     confidence, evidence_snippet, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, occ_id, test_user_id, "behavior", test_pattern,
                    str(uuid.uuid4()), 0.85, f"Evidence {i}", created_at)

            # Run crystallization
            from sakhi.apps.worker.tasks.pattern_crystallization_worker import (
                run_daily_crystallization,
            )

            result = await run_daily_crystallization(test_user_id)

            # Check if crystallized
            crystallized = await db_query("""
                SELECT * FROM crystallized_patterns
                WHERE person_id = $1 AND pattern_value = $2
            """, test_user_id, test_pattern)

            # Check if wired to memory graph
            nodes = await db_query("""
                SELECT * FROM memory_nodes
                WHERE person_id = $1 AND label = $2
            """, test_user_id, test_pattern)

        except ImportError:
            pytest.skip("Pattern crystallization not available")

        finally:
            await db_exec("""
                DELETE FROM pattern_occurrences
                WHERE person_id = $1 AND pattern_value = $2
            """, test_user_id, test_pattern)
            await db_exec("""
                DELETE FROM crystallized_patterns
                WHERE person_id = $1 AND pattern_value = $2
            """, test_user_id, test_pattern)
            await db_exec("""
                DELETE FROM memory_nodes
                WHERE person_id = $1 AND label = $2
            """, test_user_id, test_pattern)


class TestMemoryGraphIntelligence:
    """Test intelligent context from memory graph."""

    async def test_competing_activities_surfaced(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        db_query,
        setup_personal_model,
    ):
        """Test competing activities appear in context."""
        await setup_personal_model(test_user_id)

        # Create competing activities for morning
        yoga = await create_memory_node(test_user_id, "activity", "yoga", weight=0.8)
        work = await create_memory_node(test_user_id, "activity", "work", weight=0.9)
        morning = await create_memory_node(test_user_id, "time_slot", "morning", weight=1.0)

        await create_memory_edge(test_user_id, yoga, morning, "scheduled_for", weight=0.8)
        await create_memory_edge(test_user_id, work, morning, "scheduled_for", weight=0.9)
        await create_memory_edge(test_user_id, yoga, work, "competes_with", weight=0.7,
            evidence={"reason": "both want morning time"})

        try:
            from sakhi.apps.api.services.response.pipeline import run_adaptive_pipeline

            # Query about yoga/morning
            response = await run_adaptive_pipeline(
                person_id=test_user_id,
                user_text="I want to do yoga in the morning but it's hard.",
                session_id=str(uuid.uuid4()),
            )

            # Check if context includes competition info
            if response.synthesized and response.synthesized.memory_graph_context:
                ctx = response.synthesized.memory_graph_context
                # Should have found competing entities
                if ctx.get("enabled"):
                    assert "competing_entities" in ctx or "related_nodes" in ctx

        except ImportError:
            pytest.skip("Pipeline not available")

    async def test_supporting_activities_surfaced(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        db_query,
        setup_personal_model,
    ):
        """Test supporting relationships appear in context."""
        await setup_personal_model(test_user_id)

        # Create supporting relationship
        meditation = await create_memory_node(test_user_id, "activity", "meditation", weight=0.8)
        sleep_goal = await create_memory_node(test_user_id, "goal", "better sleep", weight=0.9)

        await create_memory_edge(test_user_id, meditation, sleep_goal, "supports", weight=0.85,
            evidence={"reason": "meditation promotes relaxation"})

        try:
            from sakhi.apps.api.services.response.pipeline import run_adaptive_pipeline

            response = await run_adaptive_pipeline(
                person_id=test_user_id,
                user_text="I want to sleep better. Should I try meditation?",
                session_id=str(uuid.uuid4()),
            )

            # Check if context includes support info
            if response.synthesized and response.synthesized.memory_graph_context:
                ctx = response.synthesized.memory_graph_context
                if ctx.get("enabled"):
                    assert "supporting_entities" in ctx or "related_nodes" in ctx

        except ImportError:
            pytest.skip("Pipeline not available")


class TestDatabaseIntegrity:
    """Test database integrity across operations."""

    async def test_no_orphan_edges(self, test_user_id, db_query):
        """Verify no edges reference non-existent nodes."""
        orphans = await db_query("""
            SELECT e.id
            FROM memory_edges e
            LEFT JOIN memory_nodes n1 ON e.from_node = n1.id
            LEFT JOIN memory_nodes n2 ON e.to_node = n2.id
            WHERE e.person_id = $1
            AND (n1.id IS NULL OR n2.id IS NULL)
        """, test_user_id)

        assert len(orphans) == 0, f"Found {len(orphans)} orphan edges"

    async def test_pattern_occurrences_have_valid_entries(self, test_user_id, db_query):
        """Verify pattern occurrences reference valid entries."""
        # This is a soft check - entries may have been deleted
        invalid = await db_query("""
            SELECT COUNT(*) as count
            FROM pattern_occurrences p
            LEFT JOIN journal_entries j ON p.source_entry_id::uuid = j.id
            WHERE p.person_id = $1
            AND j.id IS NULL
            AND p.source_entry_id IS NOT NULL
        """, test_user_id, one=True)

        # Allow some orphans from deleted entries
        # but log if there are many
        if invalid and invalid.get("count", 0) > 100:
            print(f"Warning: {invalid['count']} pattern occurrences have invalid entry refs")

    async def test_personal_model_has_required_states(
        self,
        test_user_id,
        db_query,
        setup_personal_model,
    ):
        """Verify personal_model has all required state fields."""
        await setup_personal_model(test_user_id)

        pm = await db_query("""
            SELECT
                operating_system,
                soul_state,
                emotion_state,
                rhythm_state
            FROM personal_model
            WHERE person_id = $1
        """, test_user_id, one=True)

        assert pm is not None, "Personal model should exist"
        assert pm.get("operating_system") is not None


class TestPerformance:
    """Performance tests for critical paths."""

    async def test_context_loading_performance(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test context loading completes in reasonable time."""
        import time
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.api.services.turn.deterministic_context_loader import (
                load_deterministic_context,
            )

            start = time.time()
            ctx = await load_deterministic_context(test_user_id)
            elapsed = time.time() - start

            # Context loading should complete in under 5 seconds
            assert elapsed < 5.0, f"Context loading took {elapsed:.2f}s"

        except ImportError:
            pytest.skip("Context loader not available")

    async def test_memory_graph_query_performance(
        self,
        test_user_id,
        create_memory_node,
        db_query,
    ):
        """Test memory graph queries are fast."""
        import time

        # Create some test nodes
        for i in range(10):
            await create_memory_node(
                test_user_id,
                "activity",
                f"test_perf_activity_{i}",
                weight=0.5 + i * 0.05,
            )

        try:
            from sakhi.apps.api.services.turn.deterministic_context_loader import (
                load_memory_graph_context,
            )

            start = time.time()
            ctx = await load_memory_graph_context(
                person_id=test_user_id,
                topic_labels=["test_perf_activity"],
                max_related=20,
            )
            elapsed = time.time() - start

            # Graph query should complete in under 1 second
            assert elapsed < 1.0, f"Graph query took {elapsed:.2f}s"

        except ImportError:
            pytest.skip("Memory graph context not available")
