"""
Longitudinal Testing Framework for Sakhi

Tests how Sakhi's understanding of a person evolves over simulated time.

Key components:
- persona_spec.py: Schema for defining test personas with traits and arcs
- entry_generator.py: LLM-powered journal entry generation
- simulation_harness.py: Time-aware simulation runner
- assertions.py: Assertion library for understanding evolution
- runner.py: Test runner with checkpointing

Usage:
    # Run unit tests
    pytest sakhi/tests/longitudinal/ -v

    # Run full simulations (slow)
    pytest sakhi/tests/longitudinal/ -v -m "simulation"

    # Run via CLI
    python -m sakhi.tests.longitudinal.runner --persona anxious_achiever --days 60

    # Export real simulation data for demo page
    python -m sakhi.tests.longitudinal.export_real_simulation --persona anxious_achiever

    # List available personas
    python -m sakhi.tests.longitudinal.runner --list

Available personas:
- anxious_achiever: High-achiever going through burnout and recovery
- stuck_creative: Creative person dealing with stagnation
"""

from .persona_spec import (
    PersonaSpec,
    PersonaTrait,
    PersonaArc,
    ArcPhase,
    Checkpoint,
    DoshaProfile,
    RhythmProfile,
    LifeContext,
    EnergySlot,
    load_persona,
    list_available_personas,
)

from .assertions import (
    AssertionResult,
    AssertionError,
    assert_friction_state,
    assert_pattern_crystallized,
    assert_theme_emerged,
    assert_rhythm_learned,
    assert_dosha_drift,
    run_checkpoint_assertions,
)

from .entry_generator import (
    generate_entry,
    generate_day_entries,
    get_entry_timestamp,
)

from .simulation_harness import (
    SimulationHarness,
    SimulationResult,
    StateSnapshot,
    run_simulation,
)

from .runner import (
    TestRunner,
    CheckpointManager,
)

from .export_real_simulation import run_and_export

__all__ = [
    # Persona spec
    "PersonaSpec",
    "PersonaTrait",
    "PersonaArc",
    "ArcPhase",
    "Checkpoint",
    "DoshaProfile",
    "RhythmProfile",
    "LifeContext",
    "EnergySlot",
    "load_persona",
    "list_available_personas",
    # Assertions
    "AssertionResult",
    "AssertionError",
    "assert_friction_state",
    "assert_pattern_crystallized",
    "assert_theme_emerged",
    "assert_rhythm_learned",
    "assert_dosha_drift",
    "run_checkpoint_assertions",
    # Entry generation
    "generate_entry",
    "generate_day_entries",
    "get_entry_timestamp",
    # Simulation
    "SimulationHarness",
    "SimulationResult",
    "StateSnapshot",
    "run_simulation",
    # Runner
    "TestRunner",
    "CheckpointManager",
    # Export
    "run_and_export",
]
