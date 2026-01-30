"""
Longitudinal Testing - Pytest Integration

Tests for the longitudinal testing framework itself, plus
actual longitudinal simulations that can be run.

Run with:
    pytest sakhi/tests/longitudinal/test_longitudinal.py -v

For full simulations (slow):
    pytest sakhi/tests/longitudinal/test_longitudinal.py -v -m "simulation"
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pathlib import Path


# ============================================================================
# Unit Tests - Persona Spec
# ============================================================================

class TestPersonaSpec:
    """Test persona specification loading and validation."""

    def test_load_anxious_achiever(self, persona_anxious_achiever):
        """Test loading the anxious_achiever persona."""
        assert persona_anxious_achiever.id == "anxious_achiever"
        assert persona_anxious_achiever.name == "Maya"
        assert len(persona_anxious_achiever.traits) >= 3
        assert persona_anxious_achiever.arc.total_days > 0

    def test_load_stuck_creative(self, persona_stuck_creative):
        """Test loading the stuck_creative persona."""
        assert persona_stuck_creative.id == "stuck_creative"
        assert persona_stuck_creative.name == "Alex"
        assert persona_stuck_creative.dosha_baseline.kapha > 0.4  # Kapha-dominant

    def test_persona_dosha_normalization(self, persona_anxious_achiever):
        """Test that doshas sum to 1.0."""
        baseline = persona_anxious_achiever.dosha_baseline
        total = baseline.vata + baseline.pitta + baseline.kapha
        assert abs(total - 1.0) < 0.01

    def test_arc_phase_at_day(self, persona_anxious_achiever):
        """Test getting the correct phase for a given day."""
        arc = persona_anxious_achiever.arc

        # Day 1 should be first phase
        phase_1 = arc.get_phase_at_day(1)
        assert phase_1.name == "Pushing Through"

        # Day 14 should still be first phase (14 days)
        phase_14 = arc.get_phase_at_day(14)
        assert phase_14.name == "Pushing Through"

        # Day 15 should be second phase
        phase_15 = arc.get_phase_at_day(15)
        assert phase_15.name == "Cracks Showing"

    def test_checkpoints_defined(self, persona_anxious_achiever):
        """Test that checkpoints are properly defined."""
        assert len(persona_anxious_achiever.checkpoints) > 0

        # Check first checkpoint
        cp = persona_anxious_achiever.checkpoints[0]
        assert cp.day > 0
        assert len(cp.assertions) > 0

    def test_list_available_personas(self):
        """Test listing available personas."""
        from sakhi.tests.longitudinal.persona_spec import list_available_personas

        personas = list_available_personas()
        assert "anxious_achiever" in personas
        assert "stuck_creative" in personas


# ============================================================================
# Unit Tests - Entry Generator
# ============================================================================

class TestEntryGenerator:
    """Test journal entry generation."""

    def test_get_generation_context(self, persona_anxious_achiever):
        """Test getting generation context for a day."""
        context = persona_anxious_achiever.get_generation_context(day=10)

        assert context["persona_id"] == "anxious_achiever"
        assert context["day"] == 10
        assert context["phase"] is not None
        assert "vata" in context["current_dosha"]

    def test_entry_timestamp_generation(self):
        """Test timestamp generation for entries."""
        from sakhi.tests.longitudinal.entry_generator import get_entry_timestamp

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)

        # Day 1 morning
        ts = get_entry_timestamp(start, day=1, time_of_day="morning")
        assert ts.date() == start.date()
        assert 7 <= ts.hour <= 10  # Morning with variance

        # Day 5 evening
        ts = get_entry_timestamp(start, day=5, time_of_day="evening")
        assert ts.day == 5
        assert 19 <= ts.hour <= 22  # Evening with variance

    @pytest.mark.asyncio
    async def test_fallback_entry_generation(self, persona_anxious_achiever):
        """Test fallback entry generation without LLM."""
        from sakhi.tests.longitudinal.entry_generator import _generate_fallback_entry

        phase = persona_anxious_achiever.arc.get_phase_at_day(5)
        entry = _generate_fallback_entry(
            persona=persona_anxious_achiever,
            day=5,
            phase=phase.model_dump(),
            time_of_day="evening",
        )

        assert len(entry) > 20
        assert isinstance(entry, str)


# ============================================================================
# Unit Tests - Assertions
# ============================================================================

class TestAssertions:
    """Test assertion functions."""

    @pytest.mark.asyncio
    async def test_friction_state_assertion_structure(
        self, db_query, test_user_for_simulation
    ):
        """Test friction state assertion returns proper structure."""
        from sakhi.tests.longitudinal.assertions import assert_friction_state

        result = await assert_friction_state(
            db_query=db_query,
            person_id=test_user_for_simulation,
            expected="balanced",
            min_confidence=0.1,
        )

        assert hasattr(result, "passed")
        assert hasattr(result, "assertion_type")
        assert hasattr(result, "expected")
        assert hasattr(result, "actual")
        assert result.assertion_type == "friction_state"

    @pytest.mark.asyncio
    async def test_theme_assertion_structure(
        self, db_query, test_user_for_simulation
    ):
        """Test theme assertion returns proper structure."""
        from sakhi.tests.longitudinal.assertions import assert_theme_emerged

        result = await assert_theme_emerged(
            db_query=db_query,
            person_id=test_user_for_simulation,
            keywords=["work", "stress"],
            min_occurrences=1,
        )

        assert hasattr(result, "passed")
        assert result.assertion_type == "theme_emerged"


# ============================================================================
# Integration Tests - Simulation Harness
# ============================================================================

class TestSimulationHarness:
    """Test the simulation harness."""

    @pytest.mark.asyncio
    async def test_harness_setup(self, simulation_harness):
        """Test harness creates user correctly."""
        assert simulation_harness.user_id is not None
        assert len(simulation_harness.user_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_harness_creates_entry(self, simulation_harness):
        """Test harness can create journal entries."""
        entry_id = await simulation_harness._create_entry(
            day=1,
            time_of_day="evening",
            content="Test entry for simulation.",
        )

        assert entry_id is not None
        assert len(entry_id) == 36

    @pytest.mark.asyncio
    async def test_harness_captures_snapshot(self, simulation_harness):
        """Test harness can capture state snapshots."""
        snapshot = await simulation_harness._capture_snapshot(day=1)

        assert snapshot.day == 1
        assert snapshot.timestamp is not None
        assert isinstance(snapshot.memory_count, int)


# ============================================================================
# Full Simulation Tests (Slow)
# ============================================================================

@pytest.mark.simulation
@pytest.mark.slow
class TestFullSimulations:
    """
    Full longitudinal simulations.

    These are slow tests that actually run multi-day simulations.
    Run with: pytest -m simulation
    """

    @pytest.mark.asyncio
    async def test_short_simulation_anxious_achiever(
        self, db_query, db_exec, persona_anxious_achiever
    ):
        """Run a short simulation for anxious_achiever."""
        from sakhi.tests.longitudinal.simulation_harness import SimulationHarness

        harness = SimulationHarness(
            persona=persona_anxious_achiever,
            db_query=db_query,
            db_exec=db_exec,
            run_workers=False,  # Skip workers for speed
        )

        try:
            await harness.setup()
            result = await harness.run(max_days=7)

            assert result.total_days == 7
            assert result.total_entries > 0
            assert len(result.errors) == 0

        finally:
            await harness.cleanup()

    @pytest.mark.asyncio
    async def test_checkpoint_verification(
        self, db_query, db_exec, persona_anxious_achiever
    ):
        """Test that checkpoints are properly verified during simulation."""
        from sakhi.tests.longitudinal.simulation_harness import SimulationHarness

        harness = SimulationHarness(
            persona=persona_anxious_achiever,
            db_query=db_query,
            db_exec=db_exec,
            run_workers=False,
        )

        try:
            await harness.setup()

            # Run just past first checkpoint (day 7)
            result = await harness.run(max_days=8)

            # Should have run the day 7 checkpoint
            assert 7 in result.checkpoint_results or len(result.checkpoint_results) > 0

        finally:
            await harness.cleanup()


# ============================================================================
# Test Runner Tests
# ============================================================================

class TestRunner:
    """Test the test runner and checkpoint manager."""

    def test_checkpoint_manager_save_load(self, tmp_path):
        """Test checkpoint save and load."""
        from sakhi.tests.longitudinal.runner import CheckpointManager

        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Save checkpoint
        manager.save_checkpoint(
            persona_id="test_persona",
            user_id="test-user-123",
            day=10,
            data={"entries": 25},
        )

        # Load checkpoint
        loaded = manager.load_checkpoint("test_persona")

        assert loaded is not None
        assert loaded["persona_id"] == "test_persona"
        assert loaded["day"] == 10
        assert loaded["data"]["entries"] == 25

        # Clear checkpoint
        manager.clear_checkpoint("test_persona")
        assert manager.load_checkpoint("test_persona") is None

    def test_simulation_result_serialization(self):
        """Test simulation result can be serialized."""
        from sakhi.tests.longitudinal.simulation_harness import SimulationResult

        result = SimulationResult(
            persona_id="test",
            user_id="user-123",
            start_time=datetime.now(timezone.utc),
            total_days=30,
            total_entries=45,
        )

        data = result.to_dict()

        assert data["persona_id"] == "test"
        assert data["total_days"] == 30
        assert data["all_checkpoints_passed"] is True  # No checkpoints = pass


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "simulation: marks tests as full simulation tests (slow)",
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow-running",
    )
