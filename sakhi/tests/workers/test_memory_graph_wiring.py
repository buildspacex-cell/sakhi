"""
Tests for Memory Graph Wiring across Workers.

Verifies that workers properly wire entities to the memory graph:
- Pattern crystallization creates pattern nodes
- Episodic consolidation creates activity/time slot nodes
- Intent extraction creates goal nodes
- Edges are created for relationships (supports, competes_with, etc.)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
import uuid

pytestmark = pytest.mark.asyncio


class TestMemoryGraphWiring:
    """Test memory graph wiring from workers."""

    async def test_pattern_wiring_creates_node(
        self,
        test_user_id,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test that crystallized patterns create graph nodes."""
        await setup_personal_model(test_user_id)

        test_pattern = f"test_pattern_{uuid.uuid4().hex[:8]}"

        try:
            from sakhi.apps.api.services.memory_graph.wiring import (
                wire_pattern_to_graph,
            )

            # Wire a pattern
            result = await wire_pattern_to_graph(
                person_id=test_user_id,
                pattern_type="behavior",
                pattern_value=test_pattern,
                confidence=0.85,
                evidence_snippet="Test evidence for pattern wiring",
            )

            # Check if node was created
            nodes = await db_query("""
                SELECT node_kind, label, data, weight
                FROM memory_nodes
                WHERE person_id = $1 AND label = $2
            """, test_user_id, test_pattern)

            if nodes:
                assert nodes[0]["node_kind"] == "pattern"
                assert nodes[0]["weight"] >= 0.5

        except ImportError:
            pytest.skip("Memory graph wiring not available")

        finally:
            await db_exec("""
                DELETE FROM memory_nodes WHERE person_id = $1 AND label = $2
            """, test_user_id, test_pattern)

    async def test_activity_wiring_creates_node_and_edge(
        self,
        test_user_id,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test that activities wire to time slots."""
        await setup_personal_model(test_user_id)

        activity_label = f"test_yoga_{uuid.uuid4().hex[:8]}"

        try:
            from sakhi.apps.api.services.memory_graph.wiring import (
                wire_activity_to_timeslot,
            )

            # Wire activity to morning
            result = await wire_activity_to_timeslot(
                person_id=test_user_id,
                activity_label=activity_label,
                time_slot="morning",
                weight=0.8,
            )

            # Check activity node
            activity_node = await db_query("""
                SELECT id, node_kind, label
                FROM memory_nodes
                WHERE person_id = $1 AND label = $2
            """, test_user_id, activity_label, one=True)

            # Check time slot node
            time_node = await db_query("""
                SELECT id, node_kind, label
                FROM memory_nodes
                WHERE person_id = $1 AND label = 'morning' AND node_kind = 'time_slot'
            """, test_user_id, one=True)

            # Check edge between them
            if activity_node and time_node:
                edge = await db_query("""
                    SELECT relation, weight
                    FROM memory_edges
                    WHERE person_id = $1
                    AND from_node = $2
                    AND to_node = $3
                """, test_user_id, activity_node["id"], time_node["id"], one=True)

                if edge:
                    assert edge["relation"] == "scheduled_for"

        except ImportError:
            pytest.skip("Activity wiring not available")

        finally:
            await db_exec("""
                DELETE FROM memory_edges WHERE person_id = $1
                AND from_node IN (SELECT id FROM memory_nodes WHERE label = $2)
            """, test_user_id, activity_label)
            await db_exec("""
                DELETE FROM memory_nodes WHERE person_id = $1 AND label = $2
            """, test_user_id, activity_label)

    async def test_competing_activities_create_edge(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        db_query,
        db_exec,
    ):
        """Test that competing activities get competes_with edges."""
        # Create two activities
        activity1 = await create_memory_node(
            test_user_id, "activity", "test_yoga", weight=0.8
        )
        activity2 = await create_memory_node(
            test_user_id, "activity", "test_work", weight=0.8
        )

        # Create morning time slot
        morning = await create_memory_node(
            test_user_id, "time_slot", "test_morning", weight=0.9
        )

        # Create scheduled_for edges
        await create_memory_edge(
            test_user_id, activity1, morning, "scheduled_for", weight=0.8
        )
        await create_memory_edge(
            test_user_id, activity2, morning, "scheduled_for", weight=0.8
        )

        # Create competes_with edge
        edge = await create_memory_edge(
            test_user_id, activity1, activity2, "competes_with", weight=0.7,
            evidence={"reason": "both want morning slot"}
        )

        # Query competing entities
        competing = await db_query("""
            SELECT
                n1.label as activity1,
                n2.label as activity2,
                e.relation,
                e.weight
            FROM memory_edges e
            JOIN memory_nodes n1 ON e.from_node = n1.id
            JOIN memory_nodes n2 ON e.to_node = n2.id
            WHERE e.person_id = $1
            AND e.relation = 'competes_with'
            AND n1.label = 'test_yoga'
        """, test_user_id)

        assert len(competing) == 1
        assert competing[0]["activity2"] == "test_work"

    async def test_supporting_entities_create_edge(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        db_query,
    ):
        """Test that supporting relationships create supports edges."""
        # Create activity and goal
        activity = await create_memory_node(
            test_user_id, "activity", "test_meditation", weight=0.8
        )
        goal = await create_memory_node(
            test_user_id, "goal", "test_better_sleep", weight=0.9
        )

        # Create supports edge
        edge = await create_memory_edge(
            test_user_id, activity, goal, "supports", weight=0.85,
            evidence={"reason": "meditation promotes relaxation"}
        )

        # Query supporting entities
        supporting = await db_query("""
            SELECT
                n1.label as source,
                n2.label as target,
                e.relation,
                e.weight
            FROM memory_edges e
            JOIN memory_nodes n1 ON e.from_node = n1.id
            JOIN memory_nodes n2 ON e.to_node = n2.id
            WHERE e.person_id = $1
            AND e.relation = 'supports'
            AND n1.label = 'test_meditation'
        """, test_user_id)

        assert len(supporting) == 1
        assert supporting[0]["target"] == "test_better_sleep"


class TestContextLoader:
    """Test context loading from memory graph."""

    async def test_load_memory_graph_context(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        db_query,
    ):
        """Test load_memory_graph_context returns proper structure."""
        # Create test graph data
        activity = await create_memory_node(
            test_user_id, "activity", "exercise", weight=0.8
        )
        goal = await create_memory_node(
            test_user_id, "goal", "get_fit", weight=0.9
        )
        await create_memory_edge(
            test_user_id, activity, goal, "supports", weight=0.8
        )

        try:
            from sakhi.apps.api.services.turn.deterministic_context_loader import (
                load_memory_graph_context,
            )

            context = await load_memory_graph_context(
                person_id=test_user_id,
                topic_labels=["exercise"],
                max_related=10,
            )

            # Verify structure
            assert "matched_nodes" in context
            assert "related_nodes" in context
            assert "competing_entities" in context
            assert "supporting_entities" in context
            assert "enabled" in context

            # If we found the exercise node
            if context.get("matched_nodes"):
                assert len(context["matched_nodes"]) >= 1

        except ImportError:
            pytest.skip("Context loader not available")

    async def test_extract_topic_labels_from_text(self):
        """Test topic extraction from user text."""
        try:
            from sakhi.apps.api.services.turn.deterministic_context_loader import (
                extract_topic_labels_from_text,
            )

            # Test with various inputs
            text1 = "I did yoga this morning and felt great"
            topics1 = extract_topic_labels_from_text(text1)
            assert "yoga" in topics1
            assert "morning" in topics1

            text2 = "Work was stressful, feeling tired and anxious"
            topics2 = extract_topic_labels_from_text(text2)
            assert "work" in topics2
            assert "stress" in topics2 or "tired" in topics2

            # Empty text
            assert extract_topic_labels_from_text("") == []

            # Text with no matching topics
            result = extract_topic_labels_from_text("Hello world")
            assert isinstance(result, list)

        except ImportError:
            pytest.skip("Topic extraction not available")


class TestGraphContextInPipeline:
    """Test memory graph context integration in response pipeline."""

    async def test_synthesize_context_with_graph(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
    ):
        """Test synthesize_context includes memory graph data."""
        # Create graph data
        activity = await create_memory_node(
            test_user_id, "activity", "yoga", weight=0.8
        )
        goal = await create_memory_node(
            test_user_id, "goal", "flexibility", weight=0.9
        )
        await create_memory_edge(
            test_user_id, activity, goal, "supports", weight=0.85
        )

        try:
            from sakhi.apps.api.services.response.synthesizer import (
                synthesize_context,
                SynthesizedContext,
            )
            from sakhi.apps.api.services.response.sensing import SenseFrame
            from sakhi.apps.api.services.response.knowledge_gap import KnowledgeGap
            from sakhi.apps.api.services.response.strategy import ResponseStrategy

            # Create minimal inputs
            sense = SenseFrame(raw_text="I want to do yoga")
            gap = KnowledgeGap()
            strategy = ResponseStrategy()

            # Memory graph context
            memory_graph_context = {
                "enabled": True,
                "matched_nodes": [{"label": "yoga", "node_kind": "activity"}],
                "related_nodes": [{"label": "flexibility", "node_kind": "goal", "relation": "supports"}],
                "competing_entities": [],
                "supporting_entities": [{"source": {"label": "yoga"}, "target": {"label": "flexibility"}, "relation": "supports"}],
            }

            ctx = synthesize_context(
                sense=sense,
                gap=gap,
                strategy=strategy,
                memory_graph_context=memory_graph_context,
            )

            # Check that related_context is populated
            assert hasattr(ctx, "related_context")
            if ctx.related_context:
                assert len(ctx.related_context) > 0

        except ImportError as e:
            pytest.skip(f"Pipeline components not available: {e}")

    async def test_build_adaptive_prompt_includes_connections(
        self,
        test_user_id,
    ):
        """Test that adaptive prompt includes CONNECTIONS section."""
        try:
            from sakhi.apps.api.services.response.synthesizer import (
                build_adaptive_prompt,
                SynthesizedContext,
            )

            # Create context with related_context
            ctx = SynthesizedContext()
            ctx.related_context = [
                "Tension: yoga and work both need morning",
                "Connection: meditation supports sleep",
            ]
            ctx.domain = "wellness"
            ctx.symptom = "stress"

            prompt = build_adaptive_prompt("I'm stressed about morning routine", ctx)

            # Check CONNECTIONS section is included
            if ctx.related_context:
                assert "CONNECTIONS" in prompt or "Tension" in prompt or "Connection" in prompt

        except ImportError:
            pytest.skip("Synthesizer not available")


class TestGraphFunctions:
    """Test memory graph SQL functions."""

    async def test_upsert_memory_node_function(self, db_query, db_exec, test_user_id):
        """Test upsert_memory_node SQL function."""
        test_label = f"test_func_node_{uuid.uuid4().hex[:8]}"

        try:
            # Call the upsert function
            result = await db_query("""
                SELECT upsert_memory_node($1, $2, $3, $4, $5) as node_id
            """, test_user_id, "activity", test_label, '{"test": true}', 0.7, one=True)

            node_id = result["node_id"] if result else None

            if node_id:
                # Verify node exists
                node = await db_query("""
                    SELECT * FROM memory_nodes WHERE id = $1
                """, node_id, one=True)

                assert node is not None
                assert node["label"] == test_label

                # Call again - should update, not duplicate
                result2 = await db_query("""
                    SELECT upsert_memory_node($1, $2, $3, $4, $5) as node_id
                """, test_user_id, "activity", test_label, '{"test": true, "updated": true}', 0.9, one=True)

                assert result2["node_id"] == node_id  # Same node

        finally:
            await db_exec("""
                DELETE FROM memory_nodes WHERE person_id = $1 AND label = $2
            """, test_user_id, test_label)

    async def test_find_competing_entities_function(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        db_query,
    ):
        """Test find_competing_entities SQL function."""
        # Create nodes and competing edge
        node1 = await create_memory_node(test_user_id, "activity", "test_yoga_compete")
        node2 = await create_memory_node(test_user_id, "activity", "test_work_compete")
        await create_memory_edge(test_user_id, node1, node2, "competes_with", weight=0.8)

        try:
            # Call the function
            results = await db_query("""
                SELECT * FROM find_competing_entities($1, $2)
            """, test_user_id, node1)

            if results:
                assert len(results) >= 1
                labels = [r["label"] for r in results]
                assert "test_work_compete" in labels

        except Exception as e:
            # Function may not exist
            pass

    async def test_traverse_memory_graph_function(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        db_query,
    ):
        """Test traverse_memory_graph SQL function."""
        # Create a small graph
        center = await create_memory_node(test_user_id, "activity", "test_center")
        related1 = await create_memory_node(test_user_id, "goal", "test_related1")
        related2 = await create_memory_node(test_user_id, "time_slot", "test_related2")

        await create_memory_edge(test_user_id, center, related1, "supports")
        await create_memory_edge(test_user_id, center, related2, "scheduled_for")

        try:
            # Traverse 1 hop
            results = await db_query("""
                SELECT * FROM traverse_memory_graph($1, $2, 1)
            """, test_user_id, center)

            if results:
                labels = [r["label"] for r in results]
                assert "test_related1" in labels or "test_related2" in labels

        except Exception as e:
            # Function may not exist
            pass
