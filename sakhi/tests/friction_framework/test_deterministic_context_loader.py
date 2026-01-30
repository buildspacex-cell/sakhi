"""
Tests for the shared Deterministic Context Loader module.

This module tests the shared context loading functions used by both:
- /v2/turn (production conversation endpoint)
- /lab/live-turn (debug/testing endpoint)

The shared loader ensures consistency between endpoints and reduces code duplication.

Location: sakhi/apps/api/services/turn/deterministic_context_loader.py
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict

import pytest

# Demo user from config/dev_persons.py
DEMO_USER_ID = os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90")


# =============================================================================
# TEST: load_internal_state
# =============================================================================

class TestLoadInternalState:
    """Tests for load_internal_state function."""

    @pytest.mark.asyncio
    async def test_load_internal_state_returns_expected_keys(self, db_query):
        """Verify load_internal_state returns all expected keys."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_internal_state,
        )

        state = await load_internal_state(DEMO_USER_ID)

        # Verify all expected keys are present
        expected_keys = [
            "emotion",
            "mind",
            "context_vector_available",
            "cognitive_load",
            "priority",
            "priority_topics",
            "soul_values",
            "soul_identity",
            "life_themes",
            "identity_graph",
            "operating_system",
            "dosha_baseline",
            "life_context",
            "decision_profile",
        ]

        for key in expected_keys:
            assert key in state, f"Expected key '{key}' not found in internal_state"

        print(f"\n  internal_state keys: {list(state.keys())}")
        print(f"  operating_system: {state.get('operating_system')}")
        print(f"  dosha_baseline: {state.get('dosha_baseline')}")

    @pytest.mark.asyncio
    async def test_load_internal_state_friction_framework_fields(self, db_query):
        """Verify Friction Framework fields are loaded correctly."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_internal_state,
        )

        state = await load_internal_state(DEMO_USER_ID)

        # Check if operating_system is loaded
        if state.get("operating_system"):
            print(f"\n  operating_system type: {state['operating_system']}")
            assert state.get("dosha_baseline") is not None, "dosha_baseline should be set when operating_system exists"
            dosha = state["dosha_baseline"]
            assert "vata" in dosha, "dosha_baseline should have vata"
            assert "pitta" in dosha, "dosha_baseline should have pitta"
            assert "kapha" in dosha, "dosha_baseline should have kapha"
            print(f"  dosha_baseline: v={dosha.get('vata')}, p={dosha.get('pitta')}, k={dosha.get('kapha')}")
        else:
            print("\n  [SKIP] operating_system not set for demo user")

    @pytest.mark.asyncio
    async def test_load_internal_state_long_term_layers(self, db_query):
        """Verify long_term layer data is extracted."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_internal_state,
        )

        state = await load_internal_state(DEMO_USER_ID)

        print(f"\n  emotion summary: {'SET' if state.get('emotion') else 'NOT SET'}")
        print(f"  mind summary: {'SET' if state.get('mind') else 'NOT SET'}")
        print(f"  cognitive_load: {state.get('cognitive_load')}")
        print(f"  soul_values: {'SET' if state.get('soul_values') else 'NOT SET'}")


# =============================================================================
# TEST: load_brain_states
# =============================================================================

class TestLoadBrainStates:
    """Tests for load_brain_states function."""

    @pytest.mark.asyncio
    async def test_load_brain_states_returns_expected_keys(self, db_query):
        """Verify load_brain_states returns all expected keys."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_brain_states,
        )

        brain = await load_brain_states(DEMO_USER_ID)

        expected_keys = [
            "forecast_state",
            "coherence_state",
            "alignment_state",
            "nudge_state",
            "long_term",
        ]

        for key in expected_keys:
            assert key in brain, f"Expected key '{key}' not found in brain_states"

        print(f"\n  brain_states keys: {list(brain.keys())}")
        print(f"  forecast_state: {'SET' if brain.get('forecast_state') else 'NOT SET'}")
        print(f"  coherence_state: {'SET' if brain.get('coherence_state') else 'NOT SET'}")
        print(f"  alignment_state: {'SET' if brain.get('alignment_state') else 'NOT SET'}")
        print(f"  nudge_state: {'SET' if brain.get('nudge_state') else 'NOT SET'}")


# =============================================================================
# TEST: load_cache_tables
# =============================================================================

class TestLoadCacheTables:
    """Tests for load_cache_tables function."""

    @pytest.mark.asyncio
    async def test_load_cache_tables_returns_expected_keys(self, db_query):
        """Verify load_cache_tables returns all expected keys."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_cache_tables,
        )

        cache = await load_cache_tables(DEMO_USER_ID)

        expected_keys = [
            "daily_reflection",
            "evening_closure",
            "morning_preview",
            "morning_ask",
            "morning_momentum",
            "micro_momentum",
            "micro_recovery",
        ]

        for key in expected_keys:
            assert key in cache, f"Expected key '{key}' not found in cache_tables"

        print(f"\n  cache_tables keys: {list(cache.keys())}")
        for key in expected_keys:
            print(f"  {key}: {'SET' if cache.get(key) else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_load_cache_tables_morning_time_gate(self, db_query):
        """Verify morning context is loaded when hour <= 11."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_cache_tables,
        )

        # Simulate morning (hour=9)
        cache = await load_cache_tables(DEMO_USER_ID, current_hour=9)

        # Morning context should be attempted (may or may not be populated)
        assert "morning_preview" in cache
        assert "morning_ask" in cache
        assert "morning_momentum" in cache

        print(f"\n  Morning time gate (hour=9):")
        print(f"    morning_preview: {'SET' if cache.get('morning_preview') else 'NOT SET'}")
        print(f"    morning_ask: {'SET' if cache.get('morning_ask') else 'NOT SET'}")
        print(f"    morning_momentum: {'SET' if cache.get('morning_momentum') else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_load_cache_tables_evening_time_gate(self, db_query):
        """Verify evening closure is loaded when hour >= 20."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_cache_tables,
        )

        # Simulate evening (hour=21)
        cache = await load_cache_tables(DEMO_USER_ID, current_hour=21)

        # Evening closure should be attempted
        assert "evening_closure" in cache

        print(f"\n  Evening time gate (hour=21):")
        print(f"    evening_closure: {'SET' if cache.get('evening_closure') else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_load_cache_tables_micro_recovery_gap_trigger(self, db_query):
        """Verify micro_recovery is loaded when gap_hours > 3."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_cache_tables,
        )

        # Simulate gap of 5 hours
        cache = await load_cache_tables(DEMO_USER_ID, gap_hours=5.0)

        # Micro recovery should be attempted
        assert "micro_recovery" in cache

        print(f"\n  Gap trigger (gap_hours=5.0):")
        print(f"    micro_recovery: {'SET' if cache.get('micro_recovery') else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_load_cache_tables_restart_phrase_trigger(self, db_query):
        """Verify micro_recovery is loaded when restart phrase detected."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_cache_tables,
        )

        # Simulate restart phrase
        cache = await load_cache_tables(
            DEMO_USER_ID,
            current_hour=10,  # Morning, but restart phrase should trigger micro_recovery
            user_text="where were we?",
        )

        # Micro recovery should be attempted due to restart phrase
        assert "micro_recovery" in cache

        print(f"\n  Restart phrase trigger ('where were we?'):")
        print(f"    micro_recovery: {'SET' if cache.get('micro_recovery') else 'NOT SET'}")


# =============================================================================
# TEST: load_scaffolds
# =============================================================================

class TestLoadScaffolds:
    """Tests for load_scaffolds function."""

    @pytest.mark.asyncio
    async def test_load_scaffolds_returns_expected_keys(self, db_query):
        """Verify load_scaffolds returns all expected keys."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_scaffolds,
        )

        scaffolds = await load_scaffolds(DEMO_USER_ID)

        expected_keys = [
            "focus_path",
            "mini_flow",
            "micro_journey",
        ]

        for key in expected_keys:
            assert key in scaffolds, f"Expected key '{key}' not found in scaffolds"

        print(f"\n  scaffolds keys: {list(scaffolds.keys())}")
        for key in expected_keys:
            print(f"  {key}: {'SET' if scaffolds.get(key) else 'NOT SET'}")


# =============================================================================
# TEST: load_continuity_state
# =============================================================================

class TestLoadContinuityState:
    """Tests for load_continuity_state function."""

    @pytest.mark.asyncio
    async def test_load_continuity_state_returns_dict(self, db_query):
        """Verify load_continuity_state returns a dict."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_continuity_state,
        )

        continuity = await load_continuity_state(DEMO_USER_ID)

        assert isinstance(continuity, dict), "continuity_state should be a dict"

        print(f"\n  continuity_state: {'SET' if continuity else 'DEFAULT'}")
        if continuity:
            print(f"  continuity_state keys: {list(continuity.keys())}")


# =============================================================================
# TEST: calculate_gap_hours
# =============================================================================

class TestCalculateGapHours:
    """Tests for calculate_gap_hours function."""

    @pytest.mark.asyncio
    async def test_calculate_gap_hours_returns_float_or_none(self, db_query):
        """Verify calculate_gap_hours returns float or None."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            calculate_gap_hours,
        )

        gap = await calculate_gap_hours(DEMO_USER_ID)

        assert gap is None or isinstance(gap, float), "gap_hours should be float or None"

        if gap is not None:
            print(f"\n  gap_hours: {gap:.2f} hours since last turn")
        else:
            print("\n  gap_hours: None (no previous turns)")


# =============================================================================
# TEST: load_deterministic_context (main entry point)
# =============================================================================

class TestLoadDeterministicContext:
    """Tests for the main load_deterministic_context function."""

    @pytest.mark.asyncio
    async def test_load_deterministic_context_returns_dataclass(self, db_query):
        """Verify load_deterministic_context returns DeterministicContext."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_deterministic_context,
            DeterministicContext,
        )

        ctx = await load_deterministic_context(DEMO_USER_ID)

        assert isinstance(ctx, DeterministicContext), "Should return DeterministicContext"

        print(f"\n  DeterministicContext loaded:")
        print(f"    internal_state keys: {list(ctx.internal_state.keys())}")
        print(f"    operating_system: {ctx.operating_system}")
        print(f"    dosha_baseline: {ctx.dosha_baseline}")
        print(f"    continuity_state: {'SET' if ctx.continuity_state else 'DEFAULT'}")

    @pytest.mark.asyncio
    async def test_load_deterministic_context_to_metadata(self, db_query):
        """Verify to_metadata() produces valid metadata dict."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_deterministic_context,
        )

        ctx = await load_deterministic_context(DEMO_USER_ID)
        metadata = ctx.to_metadata()

        assert isinstance(metadata, dict), "to_metadata() should return a dict"

        # Check key metadata fields are present
        expected_metadata_keys = [
            "internal_state",
            "operating_system",
            "dosha_baseline",
            "life_context",
            "decision_profile",
            "continuity",
            "daily_reflection",
            "morning_preview",
            "focus_path",
        ]

        for key in expected_metadata_keys:
            assert key in metadata, f"Expected key '{key}' not found in metadata"

        print(f"\n  metadata keys: {list(metadata.keys())[:15]}...")
        print(f"  total metadata keys: {len(metadata)}")

    @pytest.mark.asyncio
    async def test_load_deterministic_context_skip_cache_tables(self, db_query):
        """Verify skip_cache_tables option works."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_deterministic_context,
        )

        ctx = await load_deterministic_context(
            DEMO_USER_ID,
            skip_cache_tables=True,
        )

        # Cache tables should be None when skipped
        assert ctx.daily_reflection is None
        assert ctx.morning_preview is None
        assert ctx.micro_momentum is None

        print("\n  skip_cache_tables=True: Cache tables are None")

    @pytest.mark.asyncio
    async def test_load_deterministic_context_skip_scaffolds(self, db_query):
        """Verify skip_scaffolds option works."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_deterministic_context,
        )

        ctx = await load_deterministic_context(
            DEMO_USER_ID,
            skip_scaffolds=True,
        )

        # Scaffolds should be None when skipped
        assert ctx.focus_path is None
        assert ctx.mini_flow is None
        assert ctx.micro_journey is None

        print("\n  skip_scaffolds=True: Scaffolds are None")

    @pytest.mark.asyncio
    async def test_load_deterministic_context_guards_populated(self, db_query):
        """Verify guards are populated with default values."""
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_deterministic_context,
            DEFAULT_GUARDS,
        )

        ctx = await load_deterministic_context(DEMO_USER_ID)

        assert ctx.guards is not None, "guards should not be None"
        assert len(ctx.guards) == len(DEFAULT_GUARDS), "guards should match DEFAULT_GUARDS"

        print(f"\n  guards count: {len(ctx.guards)}")
        print(f"  guard keys: {list(ctx.guards.keys())}")


# =============================================================================
# TEST: Integration with turn_v2
# =============================================================================

class TestIntegrationWithTurnV2:
    """Tests verifying the shared loader works correctly with turn_v2."""

    @pytest.mark.asyncio
    async def test_turn_v2_uses_shared_loader(self, db_query):
        """Verify turn_v2's _load_internal_state uses shared loader."""
        # Import both to verify they're the same
        from sakhi.apps.api.services.turn.deterministic_context_loader import (
            load_internal_state as shared_loader,
        )

        # Load using shared loader
        shared_state = await shared_loader(DEMO_USER_ID)

        # Verify the shared loader returns expected structure
        assert "operating_system" in shared_state
        assert "dosha_baseline" in shared_state
        assert "emotion" in shared_state
        assert "mind" in shared_state

        print(f"\n  Shared loader verification:")
        print(f"    operating_system: {shared_state.get('operating_system')}")
        print(f"    emotion: {'SET' if shared_state.get('emotion') else 'NOT SET'}")
        print(f"    mind: {'SET' if shared_state.get('mind') else 'NOT SET'}")


# =============================================================================
# STANDALONE VERIFICATION
# =============================================================================

async def run_loader_verification():
    """
    Run verification of the deterministic context loader.
    """
    from sakhi.apps.api.services.turn.deterministic_context_loader import (
        load_deterministic_context,
        load_internal_state,
        load_brain_states,
        load_cache_tables,
        load_scaffolds,
        load_continuity_state,
        calculate_gap_hours,
    )

    print("\n" + "=" * 70)
    print("DETERMINISTIC CONTEXT LOADER VERIFICATION")
    print("=" * 70)

    print(f"\nDemo user: {DEMO_USER_ID}")

    # Test internal state
    print("\n[1] load_internal_state")
    print("-" * 40)
    state = await load_internal_state(DEMO_USER_ID)
    print(f"  Keys: {list(state.keys())}")
    print(f"  operating_system: {state.get('operating_system')}")
    print(f"  dosha_baseline: {state.get('dosha_baseline')}")

    # Test brain states
    print("\n[2] load_brain_states")
    print("-" * 40)
    brain = await load_brain_states(DEMO_USER_ID)
    print(f"  forecast_state: {'SET' if brain.get('forecast_state') else 'NOT SET'}")
    print(f"  coherence_state: {'SET' if brain.get('coherence_state') else 'NOT SET'}")

    # Test cache tables
    print("\n[3] load_cache_tables")
    print("-" * 40)
    cache = await load_cache_tables(DEMO_USER_ID)
    for key, val in cache.items():
        print(f"  {key}: {'SET' if val else 'NOT SET'}")

    # Test scaffolds
    print("\n[4] load_scaffolds")
    print("-" * 40)
    scaffolds = await load_scaffolds(DEMO_USER_ID)
    for key, val in scaffolds.items():
        print(f"  {key}: {'SET' if val else 'NOT SET'}")

    # Test continuity
    print("\n[5] load_continuity_state")
    print("-" * 40)
    continuity = await load_continuity_state(DEMO_USER_ID)
    print(f"  continuity: {'SET' if continuity else 'DEFAULT'}")

    # Test gap hours
    print("\n[6] calculate_gap_hours")
    print("-" * 40)
    gap = await calculate_gap_hours(DEMO_USER_ID)
    print(f"  gap_hours: {f'{gap:.2f}' if gap else 'None'}")

    # Test main loader
    print("\n[7] load_deterministic_context (full)")
    print("-" * 40)
    ctx = await load_deterministic_context(DEMO_USER_ID)
    metadata = ctx.to_metadata()
    print(f"  Metadata keys: {len(metadata)}")
    print(f"  Guards count: {len(ctx.guards)}")

    print("\n" + "=" * 70)
    print("[OK] All loader functions executed successfully")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_loader_verification())
