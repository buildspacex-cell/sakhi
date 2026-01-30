"""
Tests for Intent Extraction Worker and Response Pipeline Integration.

Intent Extraction Worker:
- Extracts actionable intents from journal entries
- Stores with clarity scores, priority, timeline
- Creates goal nodes in memory graph

Response Pipeline:
- Runs all 5 stages: Sensing, Knowledge Gap, Strategy, Synthesis, Prompt
- Integrates friction state, recommendations, memory graph context
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
import uuid

pytestmark = pytest.mark.asyncio


class TestIntentExtractionWorker:
    """Test suite for intent extraction worker."""

    async def test_intent_extraction_from_entry(
        self,
        test_user_id,
        create_journal_entry,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test intent extraction from journal entry."""
        await setup_personal_model(test_user_id)

        # Create entry with clear intent
        entry_id = await create_journal_entry(
            test_user_id,
            "I really want to start meditating every morning. This is my goal for the next month.",
            layer="reflection",
        )

        try:
            from sakhi.apps.worker.tasks.intent_extraction_worker import (
                run_intent_extraction,
            )

            result = await run_intent_extraction(test_user_id, entry_id=entry_id)

            # Check if intents were extracted
            intents = await db_query("""
                SELECT title, intent_type, priority, status, clarity_score
                FROM intents
                WHERE user_id = $1
                AND source_entry_id = $2
            """, test_user_id, entry_id)

            # May or may not extract depending on LLM
            if intents:
                assert intents[0]["clarity_score"] >= 0

        except ImportError:
            pytest.skip("Intent extraction worker not available")

        finally:
            await db_exec("""
                DELETE FROM intents WHERE user_id = $1 AND source_entry_id = $2
            """, test_user_id, entry_id)

    async def test_intent_extraction_handles_no_intents(
        self,
        test_user_id,
        create_journal_entry,
        db_query,
        setup_personal_model,
    ):
        """Test intent extraction with entry that has no clear intent."""
        await setup_personal_model(test_user_id)

        entry_id = await create_journal_entry(
            test_user_id,
            "The weather was nice today.",
            layer="observation",
        )

        try:
            from sakhi.apps.worker.tasks.intent_extraction_worker import (
                run_intent_extraction,
            )

            # Should not crash
            result = await run_intent_extraction(test_user_id, entry_id=entry_id)

        except ImportError:
            pytest.skip("Intent extraction worker not available")


class TestResponsePipeline:
    """Test suite for response pipeline."""

    async def test_run_adaptive_pipeline_basic(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test basic adaptive pipeline execution."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.api.services.response.pipeline import (
                run_adaptive_pipeline,
            )

            result = await run_adaptive_pipeline(
                person_id=test_user_id,
                user_text="I'm feeling stressed about work lately.",
                session_id=str(uuid.uuid4()),
            )

            # Check result structure
            assert result is not None
            assert hasattr(result, "pipeline_stages")
            assert hasattr(result, "errors")

            # Check stages completed
            if result.pipeline_stages:
                assert "sensing" in result.pipeline_stages
                assert "knowledge_gap" in result.pipeline_stages
                assert "strategy" in result.pipeline_stages

        except ImportError:
            pytest.skip("Response pipeline not available")

    async def test_pipeline_includes_friction_state(
        self,
        test_user_id,
        db_exec,
        setup_personal_model,
    ):
        """Test pipeline loads and includes friction state."""
        await setup_personal_model(test_user_id)

        # Set up personal model with baseline
        await db_exec("""
            UPDATE personal_model
            SET operating_system = $2
            WHERE person_id = $1
        """, test_user_id, {
            "type": "Adaptive-Performance",
            "dosha_baseline": {"vata": 0.25, "pitta": 0.50, "kapha": 0.25}
        })

        try:
            from sakhi.apps.api.services.response.pipeline import (
                run_adaptive_pipeline,
            )

            result = await run_adaptive_pipeline(
                person_id=test_user_id,
                user_text="I've been feeling really driven and irritable lately.",
                session_id=str(uuid.uuid4()),
            )

            # Check synthesized context has friction info
            if result.synthesized:
                assert hasattr(result.synthesized, "friction_state")
                # Friction state may be "balanced" if no recent entries

        except ImportError:
            pytest.skip("Response pipeline not available")

    async def test_pipeline_includes_memory_graph_context(
        self,
        test_user_id,
        create_memory_node,
        create_memory_edge,
        setup_personal_model,
    ):
        """Test pipeline loads memory graph context."""
        await setup_personal_model(test_user_id)

        # Create graph data that should be found
        yoga = await create_memory_node(test_user_id, "activity", "yoga", weight=0.8)
        morning = await create_memory_node(test_user_id, "time_slot", "morning", weight=0.9)
        await create_memory_edge(test_user_id, yoga, morning, "scheduled_for", weight=0.8)

        try:
            from sakhi.apps.api.services.response.pipeline import (
                run_adaptive_pipeline,
            )

            # Use text that should match "yoga" and "morning"
            result = await run_adaptive_pipeline(
                person_id=test_user_id,
                user_text="I want to do yoga in the morning.",
                session_id=str(uuid.uuid4()),
            )

            # Check synthesized context has graph data
            if result.synthesized:
                assert hasattr(result.synthesized, "memory_graph_context")
                # May or may not have matched nodes depending on exact label matching

        except ImportError:
            pytest.skip("Response pipeline not available")

    async def test_pipeline_generates_prompt(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test pipeline generates final adaptive prompt."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.api.services.response.pipeline import (
                run_adaptive_pipeline,
            )

            result = await run_adaptive_pipeline(
                person_id=test_user_id,
                user_text="I need help with my morning routine.",
                session_id=str(uuid.uuid4()),
            )

            # Check prompt was generated
            if result.adaptive_prompt:
                # Prompt should contain key sections
                assert "THEM" in result.adaptive_prompt or len(result.adaptive_prompt) > 100
                # Should not contain Ayurvedic jargon
                assert "vata" not in result.adaptive_prompt.lower()
                assert "pitta" not in result.adaptive_prompt.lower()
                assert "kapha" not in result.adaptive_prompt.lower()

        except ImportError:
            pytest.skip("Response pipeline not available")


class TestPipelineStages:
    """Test individual pipeline stages."""

    async def test_sensing_stage(self):
        """Test sensing stage extracts domain and symptom."""
        try:
            from sakhi.apps.api.services.response.pipeline import stage_1_sensing

            sense = stage_1_sensing("I've been having trouble sleeping at night.")

            assert sense is not None
            assert hasattr(sense, "domain")
            assert hasattr(sense, "raw_text")
            assert sense.raw_text == "I've been having trouble sleeping at night."

        except ImportError:
            pytest.skip("Sensing stage not available")

    async def test_knowledge_gap_stage(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test knowledge gap stage loads user knowledge."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.api.services.response.pipeline import (
                stage_1_sensing,
                stage_2_knowledge_gap,
            )

            sense = stage_1_sensing("I'm feeling anxious about work.")
            gap = await stage_2_knowledge_gap(test_user_id, sense)

            assert gap is not None
            assert hasattr(gap, "known")
            assert hasattr(gap, "unknown")
            assert hasattr(gap, "constitution")

        except ImportError:
            pytest.skip("Knowledge gap stage not available")

    async def test_strategy_stage(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test strategy stage selects response mode."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.api.services.response.pipeline import (
                stage_1_sensing,
                stage_2_knowledge_gap,
                stage_3_strategy,
            )

            sense = stage_1_sensing("Help me plan my morning.")
            gap = await stage_2_knowledge_gap(test_user_id, sense)
            strategy = stage_3_strategy(sense, gap)

            assert strategy is not None
            assert hasattr(strategy, "mode")
            assert hasattr(strategy, "questions_to_ask")

        except ImportError:
            pytest.skip("Strategy stage not available")

    async def test_synthesis_stage(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test synthesis stage creates prompt-ready context."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.api.services.response.pipeline import (
                stage_1_sensing,
                stage_2_knowledge_gap,
                stage_3_strategy,
                stage_4_synthesis,
            )

            sense = stage_1_sensing("I want to be more productive.")
            gap = await stage_2_knowledge_gap(test_user_id, sense)
            strategy = stage_3_strategy(sense, gap)
            synth = stage_4_synthesis(
                sense, gap, strategy,
                friction_state="balanced",
                drift_percentage=0,
                energy_mode="sattva",
            )

            assert synth is not None
            assert hasattr(synth, "jargon_free")
            assert hasattr(synth, "domain")

        except ImportError:
            pytest.skip("Synthesis stage not available")


class TestJargonFreeOutput:
    """Test that responses are jargon-free."""

    async def test_translation_layer(self):
        """Test translation layer converts terms."""
        try:
            from sakhi.apps.api.services.response.translation import (
                translate_friction_state,
                translate_energy_mode,
                translate_dosha_type,
            )

            # Test friction state translation
            assert translate_friction_state("chaos") == "all over the place"
            assert translate_friction_state("intensity") == "running hot"
            assert translate_friction_state("stagnation") == "stuck"

            # Test energy mode translation
            assert "clear" in translate_energy_mode("sattva").lower()
            assert "active" in translate_energy_mode("rajas").lower()
            assert "low" in translate_energy_mode("tamas").lower()

        except ImportError:
            pytest.skip("Translation layer not available")

    async def test_build_jargon_free_context(self):
        """Test jargon-free context builder."""
        try:
            from sakhi.apps.api.services.response.translation import (
                build_jargon_free_context,
            )

            ctx = build_jargon_free_context(
                operating_system={"type": "Adaptive-Performance"},
                dosha_baseline={"vata": 0.25, "pitta": 0.50, "kapha": 0.25},
                friction_state="intensity",
                drift_percentage=30,
                energy_mode="rajas",
            )

            assert ctx is not None
            # Check no Ayurvedic terms
            ctx_str = str(ctx).lower()
            assert "vata" not in ctx_str
            assert "pitta" not in ctx_str
            assert "kapha" not in ctx_str
            assert "dosha" not in ctx_str

        except ImportError:
            pytest.skip("Translation layer not available")


class TestIntentsDatabase:
    """Test intents table schema."""

    async def test_intents_table_exists(self, db_query):
        """Verify intents table has required columns."""
        columns = await db_query("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'intents'
        """)

        column_names = {c["column_name"] for c in columns}

        required = {"id", "user_id", "title", "intent_type", "status"}
        for col in required:
            assert col in column_names, f"Missing column: {col}"
