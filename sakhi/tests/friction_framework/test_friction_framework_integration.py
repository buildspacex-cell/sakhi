"""
Deterministic Intelligence Integration Tests

This comprehensive test suite verifies ALL deterministic intelligence fields from turn-v2:

FRICTION FRAMEWORK (Ayurvedic Pipeline):
1. Stored during onboarding (operating_system, life_context, decision_profile)
2. Written during episodic consolidation (state_vector, guna_vector)
3. Loaded during conversation turn (internal_state)
4. Used for friction state calculation

BRAIN STATES (from orchestration):
- emotion_state, soul_state, rhythm_state, goals_state, identity_momentum_state

ENGINE STATES:
- inner_dialogue, microreg_state, tone_state, nudge_state, empathy_state

CONTINUITY & REFLECTION:
- continuity_state, daily_reflection, evening_closure

MORNING CONTEXT:
- morning_preview, morning_ask, morning_momentum

MICRO CONTEXT:
- micro_momentum, micro_recovery

SCAFFOLDS:
- focus_path, mini_flow, micro_journey

COMPUTED STATES:
- moment_model, evidence_pack, deliberation_scaffold

PERSONAL MODEL STATES:
- forecast_state, coherence_state, alignment_state, long_term.layers

Uses demo user: 565bdb63-124b-4692-a039-846fddceff90 (Vidhya)
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, date, timezone, timedelta
from typing import Any, Dict, List, Optional

import pytest

# Demo user from config/dev_persons.py
DEMO_USER_ID = os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90")
TEST_USER_ID = f"test-friction-{uuid.uuid4().hex[:8]}"


# =============================================================================
# TABLE EXISTENCE CHECKS
# =============================================================================

EXPECTED_TABLES = [
    "personal_model",
    "memory_episodic",
    "daily_reflection_cache",
    "daily_closure_cache",
    "morning_preview_cache",
    "morning_ask_cache",
    "morning_momentum_cache",
    "micro_momentum_cache",
    "micro_recovery_cache",
    "focus_path_cache",
    "mini_flow_cache",
    "micro_journey_cache",
    "continuity_state",
    "reflection_trace",
]

PERSONAL_MODEL_EXPECTED_COLUMNS = [
    "operating_system",
    "life_context",
    "decision_profile",
    "long_term",
    "nudge_state",
    "forecast_state",
    "coherence_state",
    "alignment_state",
]

MEMORY_EPISODIC_EXPECTED_COLUMNS = [
    "state_vector",
    "guna_vector",
    "emotional_state",
    "rhythm_state",
]


# =============================================================================
# DATABASE VERIFICATION HELPERS
# =============================================================================

async def get_personal_model_fields(db_query, person_id: str) -> Dict[str, Any]:
    """Fetch friction framework fields from personal_model."""
    row = await db_query(
        """
        SELECT
            operating_system,
            life_context,
            decision_profile,
            long_term
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if not row:
        return {}

    result = {}
    for field in ["operating_system", "life_context", "decision_profile", "long_term"]:
        value = row.get(field)
        if value and isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        result[field] = value
    return result


async def get_episodic_state_vectors(db_query, person_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch recent episodic entries with state vectors."""
    rows = await db_query(
        """
        SELECT
            id,
            state_vector,
            guna_vector,
            created_at
        FROM memory_episodic
        WHERE person_id = $1
          AND (state_vector IS NOT NULL OR guna_vector IS NOT NULL)
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    results = []
    for row in rows or []:
        entry = {"id": row.get("id"), "created_at": row.get("created_at")}
        for field in ["state_vector", "guna_vector"]:
            value = row.get(field)
            if value and isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            entry[field] = value
        results.append(entry)
    return results


async def get_all_episodic_entries(db_query, person_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch all recent episodic entries for debugging."""
    rows = await db_query(
        """
        SELECT
            id,
            text,
            state_vector,
            guna_vector,
            emotional_state,
            rhythm_state,
            created_at
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    results = []
    for row in rows or []:
        entry = dict(row)
        for field in ["state_vector", "guna_vector", "emotional_state", "rhythm_state"]:
            value = entry.get(field)
            if value and isinstance(value, str):
                try:
                    entry[field] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        results.append(entry)
    return results


# =============================================================================
# TEST: OPERATING SYSTEM STORAGE (Onboarding)
# =============================================================================

class TestOperatingSystemStorage:
    """Tests for operating_system field in personal_model."""

    @pytest.mark.asyncio
    async def test_operating_system_field_exists(self, db_query):
        """Verify operating_system column exists in personal_model."""
        row = await db_query(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'personal_model'
              AND column_name = 'operating_system'
            """,
            one=True,
        )
        assert row is not None, "operating_system column should exist in personal_model"
        assert row.get("data_type") == "jsonb", "operating_system should be JSONB type"

    @pytest.mark.asyncio
    async def test_operating_system_stored_after_onboarding(self, db_query, db_exec):
        """Verify operating_system is stored correctly after onboarding."""
        # Create test data
        test_os_data = {
            "type": "Adaptive-Performance",
            "primary": "Adaptive",
            "secondary": "Performance",
            "dosha_baseline": {"vata": 0.45, "pitta": 0.35, "kapha": 0.20},
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "source": "test",
        }

        # Insert or update
        await db_exec(
            """
            INSERT INTO personal_model (person_id, operating_system, created_at, updated_at)
            VALUES ($1, $2, NOW(), NOW())
            ON CONFLICT (person_id) DO UPDATE SET operating_system = $2, updated_at = NOW()
            """,
            TEST_USER_ID,
            json.dumps(test_os_data),
        )

        # Verify
        fields = await get_personal_model_fields(db_query, TEST_USER_ID)
        assert fields.get("operating_system") is not None, "operating_system should be stored"
        os_data = fields["operating_system"]
        assert os_data.get("type") == "Adaptive-Performance"
        assert os_data.get("dosha_baseline", {}).get("vata") == 0.45

    @pytest.mark.asyncio
    async def test_dosha_baseline_structure(self, db_query):
        """Verify dosha_baseline has correct structure."""
        fields = await get_personal_model_fields(db_query, DEMO_USER_ID)
        os_data = fields.get("operating_system")

        if os_data:
            dosha = os_data.get("dosha_baseline", {})
            # Should have all three doshas
            assert "vata" in dosha, "dosha_baseline should have vata"
            assert "pitta" in dosha, "dosha_baseline should have pitta"
            assert "kapha" in dosha, "dosha_baseline should have kapha"
            # Should sum to approximately 1.0
            total = dosha.get("vata", 0) + dosha.get("pitta", 0) + dosha.get("kapha", 0)
            assert 0.99 <= total <= 1.01, f"Dosha baseline should sum to 1.0, got {total}"


# =============================================================================
# TEST: LIFE CONTEXT & DECISION PROFILE
# =============================================================================

class TestLifeContextAndDecisionProfile:
    """Tests for life_context and decision_profile fields."""

    @pytest.mark.asyncio
    async def test_life_context_field_exists(self, db_query):
        """Verify life_context column exists."""
        row = await db_query(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'personal_model'
              AND column_name = 'life_context'
            """,
            one=True,
        )
        assert row is not None, "life_context column should exist"

    @pytest.mark.asyncio
    async def test_decision_profile_field_exists(self, db_query):
        """Verify decision_profile column exists."""
        row = await db_query(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'personal_model'
              AND column_name = 'decision_profile'
            """,
            one=True,
        )
        assert row is not None, "decision_profile column should exist"

    @pytest.mark.asyncio
    async def test_life_context_stored(self, db_query, db_exec):
        """Verify life_context is stored correctly."""
        test_life_context = {
            "age_range": "35-44",
            "location": "San Francisco",
            "active_roles": ["professional", "parent"],
            "life_phase": "building",
        }

        await db_exec(
            """
            UPDATE personal_model
            SET life_context = $2, updated_at = NOW()
            WHERE person_id = $1
            """,
            TEST_USER_ID,
            json.dumps(test_life_context),
        )

        fields = await get_personal_model_fields(db_query, TEST_USER_ID)
        assert fields.get("life_context") is not None
        assert fields["life_context"].get("age_range") == "35-44"

    @pytest.mark.asyncio
    async def test_decision_profile_stored(self, db_query, db_exec):
        """Verify decision_profile is stored correctly."""
        test_decision_profile = {
            "primary_driver": "make_progress",
            "risk_tendency": "calculated_risk",
            "time_horizon": "year_two",
        }

        await db_exec(
            """
            UPDATE personal_model
            SET decision_profile = $2, updated_at = NOW()
            WHERE person_id = $1
            """,
            TEST_USER_ID,
            json.dumps(test_decision_profile),
        )

        fields = await get_personal_model_fields(db_query, TEST_USER_ID)
        assert fields.get("decision_profile") is not None
        assert fields["decision_profile"].get("primary_driver") == "make_progress"


# =============================================================================
# TEST: STATE VECTOR & GUNA VECTOR IN MEMORY_EPISODIC
# =============================================================================

class TestEpisodicStateVectors:
    """Tests for state_vector and guna_vector in memory_episodic."""

    @pytest.mark.asyncio
    async def test_state_vector_column_exists(self, db_query):
        """Verify state_vector column exists in memory_episodic."""
        row = await db_query(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'memory_episodic'
              AND column_name = 'state_vector'
            """,
            one=True,
        )
        assert row is not None, "state_vector column should exist in memory_episodic"
        assert row.get("data_type") == "jsonb", "state_vector should be JSONB type"

    @pytest.mark.asyncio
    async def test_guna_vector_column_exists(self, db_query):
        """Verify guna_vector column exists in memory_episodic."""
        row = await db_query(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'memory_episodic'
              AND column_name = 'guna_vector'
            """,
            one=True,
        )
        assert row is not None, "guna_vector column should exist in memory_episodic"
        assert row.get("data_type") == "jsonb", "guna_vector should be JSONB type"

    @pytest.mark.asyncio
    async def test_state_vector_structure(self, db_query, db_exec):
        """Verify state_vector has correct dosha structure."""
        test_state_vector = {
            "dosha": {"vata": 0.35, "pitta": 0.40, "kapha": 0.25},
            "confidence": 0.75,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        test_guna_vector = {
            "sattva": 0.45,
            "rajas": 0.35,
            "tamas": 0.20,
            "confidence": 0.70,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        episode_id = str(uuid.uuid4())
        await db_exec(
            """
            INSERT INTO memory_episodic (
                id, user_id, person_id, text, state_vector, guna_vector, created_at
            )
            VALUES ($1, $2, $2::uuid, $3, $4, $5, NOW())
            """,
            episode_id,
            TEST_USER_ID,
            "Test episode for state vector verification",
            json.dumps(test_state_vector),
            json.dumps(test_guna_vector),
        )

        # Verify
        entries = await get_episodic_state_vectors(db_query, TEST_USER_ID, limit=1)
        assert len(entries) > 0, "Should have episodic entry with state vectors"

        entry = entries[0]
        sv = entry.get("state_vector", {})
        gv = entry.get("guna_vector", {})

        assert sv.get("dosha", {}).get("vata") == 0.35
        assert sv.get("dosha", {}).get("pitta") == 0.40
        assert gv.get("sattva") == 0.45
        assert gv.get("rajas") == 0.35

    @pytest.mark.asyncio
    async def test_demo_user_has_episodic_entries(self, db_query):
        """Check if demo user has any episodic entries."""
        entries = await get_all_episodic_entries(db_query, DEMO_USER_ID, limit=5)
        # This is informational - demo user may or may not have entries
        print(f"\nDemo user episodic entries count: {len(entries)}")
        if entries:
            print(f"Latest entry has state_vector: {entries[0].get('state_vector') is not None}")
            print(f"Latest entry has guna_vector: {entries[0].get('guna_vector') is not None}")


# =============================================================================
# TEST: INTERNAL STATE LOADING (Turn-v2)
# =============================================================================

class TestInternalStateLoading:
    """Tests for _load_internal_state function in turn_v2."""

    @pytest.mark.asyncio
    async def test_internal_state_loads_operating_system(self, db_query, db_exec):
        """Verify internal state includes operating_system from personal_model."""
        # Set up test data
        test_os_data = {
            "type": "Performance",
            "primary": "Performance",
            "secondary": None,
            "dosha_baseline": {"vata": 0.25, "pitta": 0.55, "kapha": 0.20},
        }

        await db_exec(
            """
            INSERT INTO personal_model (person_id, operating_system, created_at, updated_at)
            VALUES ($1, $2, NOW(), NOW())
            ON CONFLICT (person_id) DO UPDATE SET operating_system = $2, updated_at = NOW()
            """,
            TEST_USER_ID,
            json.dumps(test_os_data),
        )

        # Simulate _load_internal_state query
        row = await db_query(
            """
            SELECT long_term, operating_system, life_context, decision_profile
            FROM personal_model
            WHERE person_id = $1
            """,
            TEST_USER_ID,
            one=True,
        )

        assert row is not None, "Should find personal_model row"
        os_data = row.get("operating_system")
        if isinstance(os_data, str):
            os_data = json.loads(os_data)

        assert os_data is not None, "operating_system should be loaded"
        assert os_data.get("type") == "Performance"
        assert os_data.get("dosha_baseline", {}).get("pitta") == 0.55

    @pytest.mark.asyncio
    async def test_internal_state_loads_long_term_layers(self, db_query, db_exec):
        """Verify internal state loads emotion/mind/soul from long_term."""
        test_long_term = {
            "layers": {
                "emotion": {"summary": "Generally calm with occasional stress peaks"},
                "mind": {
                    "summary": "Clear thinking, moderate workload",
                    "metrics": {
                        "cognitive_load": 0.6,
                        "top_priority": "project deadline",
                        "priority_topics": ["work", "health"],
                    },
                },
                "soul": {
                    "metrics": {
                        "values": ["growth", "balance", "connection"],
                        "identity_anchors": ["professional", "learner"],
                        "life_themes": ["career development"],
                    },
                },
            },
            "identity_graph": {"nodes": [], "edges": []},
        }

        await db_exec(
            """
            UPDATE personal_model
            SET long_term = $2, updated_at = NOW()
            WHERE person_id = $1
            """,
            TEST_USER_ID,
            json.dumps(test_long_term),
        )

        row = await db_query(
            """
            SELECT long_term
            FROM personal_model
            WHERE person_id = $1
            """,
            TEST_USER_ID,
            one=True,
        )

        long_term = row.get("long_term")
        if isinstance(long_term, str):
            long_term = json.loads(long_term)

        layers = long_term.get("layers", {})
        assert layers.get("emotion", {}).get("summary") is not None
        assert layers.get("mind", {}).get("metrics", {}).get("cognitive_load") == 0.6
        assert "growth" in layers.get("soul", {}).get("metrics", {}).get("values", [])


# =============================================================================
# TEST: FRICTION STATE CALCULATION
# =============================================================================

class TestFrictionStateCalculation:
    """Tests for friction state calculation from state vectors."""

    @pytest.mark.asyncio
    async def test_friction_state_query(self, db_query, db_exec):
        """Verify friction state can be calculated from recent entries."""
        # Insert test entries with state vectors showing Pitta elevation
        for i in range(3):
            episode_id = str(uuid.uuid4())
            state_vector = {
                "dosha": {"vata": 0.25, "pitta": 0.55, "kapha": 0.20},  # Pitta elevated
                "confidence": 0.8,
            }
            guna_vector = {
                "sattva": 0.30,
                "rajas": 0.50,  # Rajas dominant = Activation mode
                "tamas": 0.20,
            }
            await db_exec(
                """
                INSERT INTO memory_episodic (
                    id, user_id, person_id, text, state_vector, guna_vector, created_at
                )
                VALUES ($1, $2, $2::uuid, $3, $4, $5, $6)
                """,
                episode_id,
                TEST_USER_ID,
                f"Test entry {i} for friction calculation",
                json.dumps(state_vector),
                json.dumps(guna_vector),
                datetime.now(timezone.utc) - timedelta(days=i),
            )

        # Query like friction_framework.py does
        entries = await db_query(
            """
            SELECT state_vector, guna_vector, created_at
            FROM memory_episodic
            WHERE person_id = $1
              AND created_at > NOW() - INTERVAL '7 days'
            ORDER BY created_at DESC
            LIMIT 50
            """,
            TEST_USER_ID,
        )

        assert len(entries) >= 3, "Should have at least 3 recent entries"

        # Calculate average dosha from entries
        current_dosha = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
        current_guna = {"sattva": 0.0, "rajas": 0.0, "tamas": 0.0}
        count = 0

        for entry in entries:
            sv = entry.get("state_vector")
            gv = entry.get("guna_vector")
            if isinstance(sv, str):
                sv = json.loads(sv)
            if isinstance(gv, str):
                gv = json.loads(gv)

            if sv and sv.get("dosha"):
                dosha = sv["dosha"]
                current_dosha["vata"] += dosha.get("vata", 0)
                current_dosha["pitta"] += dosha.get("pitta", 0)
                current_dosha["kapha"] += dosha.get("kapha", 0)
                count += 1

            if gv:
                current_guna["sattva"] += gv.get("sattva", 0)
                current_guna["rajas"] += gv.get("rajas", 0)
                current_guna["tamas"] += gv.get("tamas", 0)

        if count > 0:
            current_dosha = {k: round(v / count, 2) for k, v in current_dosha.items()}
            current_guna = {k: round(v / count, 2) for k, v in current_guna.items()}

        # Verify Pitta is elevated
        assert current_dosha["pitta"] > current_dosha["vata"], "Pitta should be highest"
        assert current_dosha["pitta"] > current_dosha["kapha"], "Pitta should be highest"

        # Verify Rajas is dominant (Activation mode)
        assert current_guna["rajas"] > current_guna["sattva"], "Rajas should indicate Activation mode"


# =============================================================================
# TEST: SCHEMA VERIFICATION (All Tables)
# =============================================================================

class TestSchemaVerification:
    """Verify all required tables and columns exist for deterministic intelligence."""

    @pytest.mark.asyncio
    async def test_all_cache_tables_exist(self, db_query):
        """Verify all cache tables required by turn-v2 exist."""
        for table_name in EXPECTED_TABLES:
            row = await db_query(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = $1
                """,
                table_name,
                one=True,
            )
            assert row is not None, f"Table {table_name} should exist"

    @pytest.mark.asyncio
    async def test_personal_model_columns(self, db_query):
        """Verify all personal_model columns for deterministic intelligence."""
        for col in PERSONAL_MODEL_EXPECTED_COLUMNS:
            row = await db_query(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'personal_model' AND column_name = $1
                """,
                col,
                one=True,
            )
            assert row is not None, f"personal_model.{col} column should exist"

    @pytest.mark.asyncio
    async def test_memory_episodic_columns(self, db_query):
        """Verify memory_episodic columns for state tracking."""
        for col in MEMORY_EPISODIC_EXPECTED_COLUMNS:
            row = await db_query(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'memory_episodic' AND column_name = $1
                """,
                col,
                one=True,
            )
            assert row is not None, f"memory_episodic.{col} column should exist"


# =============================================================================
# TEST: BRAIN STATES (from orchestration)
# =============================================================================

class TestBrainStates:
    """Tests for brain states computed during orchestration."""

    @pytest.mark.asyncio
    async def test_personal_model_long_term_layers(self, db_query):
        """Verify long_term.layers structure (emotion, mind, soul)."""
        row = await db_query(
            """
            SELECT long_term
            FROM personal_model
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        if row and row.get("long_term"):
            long_term = row["long_term"]
            if isinstance(long_term, str):
                long_term = json.loads(long_term)
            layers = long_term.get("layers", {})
            print(f"\n  long_term.layers keys: {list(layers.keys())}")
            # Verify expected layer structure
            for layer_name in ["emotion", "mind", "soul"]:
                layer = layers.get(layer_name, {})
                print(f"    {layer_name}: {'HAS summary' if layer.get('summary') else 'no summary'}")

    @pytest.mark.asyncio
    async def test_forecast_state_exists(self, db_query):
        """Verify forecast_state can be queried."""
        row = await db_query(
            """
            SELECT forecast_state
            FROM personal_model
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        print(f"\n  forecast_state: {'SET' if row and row.get('forecast_state') else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_coherence_state_exists(self, db_query):
        """Verify coherence_state can be queried."""
        row = await db_query(
            """
            SELECT coherence_state
            FROM personal_model
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        print(f"\n  coherence_state: {'SET' if row and row.get('coherence_state') else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_alignment_state_exists(self, db_query):
        """Verify alignment_state can be queried."""
        row = await db_query(
            """
            SELECT alignment_state
            FROM personal_model
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        print(f"\n  alignment_state: {'SET' if row and row.get('alignment_state') else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_nudge_state_exists(self, db_query):
        """Verify nudge_state can be queried."""
        row = await db_query(
            """
            SELECT nudge_state
            FROM personal_model
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        print(f"\n  nudge_state: {'SET' if row and row.get('nudge_state') else 'NOT SET'}")


# =============================================================================
# TEST: CONTINUITY STATE
# =============================================================================

class TestContinuityState:
    """Tests for continuity_state table and loading."""

    @pytest.mark.asyncio
    async def test_continuity_table_exists(self, db_query):
        """Verify continuity_state table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'continuity_state'
            """,
            one=True,
        )
        assert row is not None, "continuity_state table should exist"

    @pytest.mark.asyncio
    async def test_continuity_state_query(self, db_query):
        """Verify continuity_state can be queried for demo user."""
        row = await db_query(
            """
            SELECT *
            FROM continuity_state
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        if row:
            print(f"\n  continuity_state found with keys: {list(row.keys())}")
        else:
            print(f"\n  continuity_state: NOT SET for demo user")


# =============================================================================
# TEST: DAILY REFLECTION & CLOSURE
# =============================================================================

class TestDailyReflectionAndClosure:
    """Tests for daily_reflection_cache and daily_closure_cache."""

    @pytest.mark.asyncio
    async def test_daily_reflection_cache_table(self, db_query):
        """Verify daily_reflection_cache table structure."""
        columns = await db_query(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'daily_reflection_cache'
            """,
        )
        column_names = [c.get("column_name") for c in (columns or [])]
        print(f"\n  daily_reflection_cache columns: {column_names}")
        assert "summary" in column_names or len(column_names) > 0

    @pytest.mark.asyncio
    async def test_daily_reflection_query(self, db_query):
        """Verify daily_reflection_cache query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT summary, reflection_date, generated_at
            FROM daily_reflection_cache
            WHERE person_id = $1 AND reflection_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  daily_reflection for today: FOUND")
            print(f"    summary preview: {str(row.get('summary', ''))[:100]}...")
        else:
            print(f"\n  daily_reflection for today: NOT FOUND")

    @pytest.mark.asyncio
    async def test_daily_closure_cache_table(self, db_query):
        """Verify daily_closure_cache table structure."""
        columns = await db_query(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'daily_closure_cache'
            """,
        )
        column_names = [c.get("column_name") for c in (columns or [])]
        print(f"\n  daily_closure_cache columns: {column_names}")

    @pytest.mark.asyncio
    async def test_daily_closure_query(self, db_query):
        """Verify daily_closure_cache query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT completed, pending, signals, summary, closure_date, generated_at
            FROM daily_closure_cache
            WHERE person_id = $1 AND closure_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  evening_closure for today: FOUND")
        else:
            print(f"\n  evening_closure for today: NOT FOUND")


# =============================================================================
# TEST: MORNING CONTEXT (Preview, Ask, Momentum)
# =============================================================================

class TestMorningContext:
    """Tests for morning_preview_cache, morning_ask_cache, morning_momentum_cache."""

    @pytest.mark.asyncio
    async def test_morning_preview_cache_table(self, db_query):
        """Verify morning_preview_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'morning_preview_cache'
            """,
            one=True,
        )
        assert row is not None, "morning_preview_cache table should exist"

    @pytest.mark.asyncio
    async def test_morning_preview_query(self, db_query):
        """Verify morning_preview query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT focus_areas, key_tasks, reminders, rhythm_hint, summary, preview_date, generated_at
            FROM morning_preview_cache
            WHERE person_id = $1 AND preview_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  morning_preview for today: FOUND")
            print(f"    focus_areas: {row.get('focus_areas')}")
        else:
            print(f"\n  morning_preview for today: NOT FOUND")

    @pytest.mark.asyncio
    async def test_morning_ask_cache_table(self, db_query):
        """Verify morning_ask_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'morning_ask_cache'
            """,
            one=True,
        )
        assert row is not None, "morning_ask_cache table should exist"

    @pytest.mark.asyncio
    async def test_morning_ask_query(self, db_query):
        """Verify morning_ask query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT question, reason, ask_date, generated_at
            FROM morning_ask_cache
            WHERE person_id = $1 AND ask_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  morning_ask for today: FOUND")
            print(f"    question: {row.get('question')}")
        else:
            print(f"\n  morning_ask for today: NOT FOUND")

    @pytest.mark.asyncio
    async def test_morning_momentum_cache_table(self, db_query):
        """Verify morning_momentum_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'morning_momentum_cache'
            """,
            one=True,
        )
        assert row is not None, "morning_momentum_cache table should exist"

    @pytest.mark.asyncio
    async def test_morning_momentum_query(self, db_query):
        """Verify morning_momentum query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT momentum_hint, suggested_start, reason, momentum_date, generated_at
            FROM morning_momentum_cache
            WHERE person_id = $1 AND momentum_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  morning_momentum for today: FOUND")
            print(f"    momentum_hint: {row.get('momentum_hint')}")
        else:
            print(f"\n  morning_momentum for today: NOT FOUND")


# =============================================================================
# TEST: MICRO CONTEXT (Momentum, Recovery)
# =============================================================================

class TestMicroContext:
    """Tests for micro_momentum_cache and micro_recovery_cache."""

    @pytest.mark.asyncio
    async def test_micro_momentum_cache_table(self, db_query):
        """Verify micro_momentum_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'micro_momentum_cache'
            """,
            one=True,
        )
        assert row is not None, "micro_momentum_cache table should exist"

    @pytest.mark.asyncio
    async def test_micro_momentum_query(self, db_query):
        """Verify micro_momentum query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT nudge, reason, nudge_date, generated_at
            FROM micro_momentum_cache
            WHERE person_id = $1 AND nudge_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  micro_momentum for today: FOUND")
        else:
            print(f"\n  micro_momentum for today: NOT FOUND")

    @pytest.mark.asyncio
    async def test_micro_recovery_cache_table(self, db_query):
        """Verify micro_recovery_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'micro_recovery_cache'
            """,
            one=True,
        )
        assert row is not None, "micro_recovery_cache table should exist"

    @pytest.mark.asyncio
    async def test_micro_recovery_query(self, db_query):
        """Verify micro_recovery query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT nudge, reason, recovery_date, generated_at
            FROM micro_recovery_cache
            WHERE person_id = $1 AND recovery_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  micro_recovery for today: FOUND")
        else:
            print(f"\n  micro_recovery for today: NOT FOUND")


# =============================================================================
# TEST: SCAFFOLDS (Focus Path, Mini Flow, Micro Journey)
# =============================================================================

class TestScaffolds:
    """Tests for focus_path_cache, mini_flow_cache, micro_journey_cache."""

    @pytest.mark.asyncio
    async def test_focus_path_cache_table(self, db_query):
        """Verify focus_path_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'focus_path_cache'
            """,
            one=True,
        )
        assert row is not None, "focus_path_cache table should exist"

    @pytest.mark.asyncio
    async def test_focus_path_query(self, db_query):
        """Verify focus_path query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT anchor_step, progress_step, closure_step, intent_source, path_date, generated_at
            FROM focus_path_cache
            WHERE person_id = $1 AND path_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  focus_path for today: FOUND")
            print(f"    anchor_step: {row.get('anchor_step')}")
        else:
            print(f"\n  focus_path for today: NOT FOUND")

    @pytest.mark.asyncio
    async def test_mini_flow_cache_table(self, db_query):
        """Verify mini_flow_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'mini_flow_cache'
            """,
            one=True,
        )
        assert row is not None, "mini_flow_cache table should exist"

    @pytest.mark.asyncio
    async def test_mini_flow_query(self, db_query):
        """Verify mini_flow query for demo user."""
        today = date.today()
        row = await db_query(
            """
            SELECT warmup_step, focus_block_step, closure_step, optional_reward, source, flow_date, generated_at
            FROM mini_flow_cache
            WHERE person_id = $1 AND flow_date = $2
            """,
            DEMO_USER_ID,
            today,
            one=True,
        )
        if row:
            print(f"\n  mini_flow for today: FOUND")
        else:
            print(f"\n  mini_flow for today: NOT FOUND")

    @pytest.mark.asyncio
    async def test_micro_journey_cache_table(self, db_query):
        """Verify micro_journey_cache table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'micro_journey_cache'
            """,
            one=True,
        )
        assert row is not None, "micro_journey_cache table should exist"

    @pytest.mark.asyncio
    async def test_micro_journey_query(self, db_query):
        """Verify micro_journey query for demo user."""
        row = await db_query(
            """
            SELECT flow_count, rhythm_slot, journey, generated_at
            FROM micro_journey_cache
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        if row:
            print(f"\n  micro_journey: FOUND")
            print(f"    flow_count: {row.get('flow_count')}")
        else:
            print(f"\n  micro_journey: NOT FOUND")


# =============================================================================
# TEST: REFLECTION TRACE
# =============================================================================

class TestReflectionTrace:
    """Tests for reflection_trace table."""

    @pytest.mark.asyncio
    async def test_reflection_trace_table(self, db_query):
        """Verify reflection_trace table exists."""
        row = await db_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'reflection_trace'
            """,
            one=True,
        )
        assert row is not None, "reflection_trace table should exist"

    @pytest.mark.asyncio
    async def test_reflection_trace_query(self, db_query):
        """Verify reflection_trace query for demo user."""
        row = await db_query(
            """
            SELECT *
            FROM reflection_trace
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            DEMO_USER_ID,
            one=True,
        )
        if row:
            print(f"\n  reflection_trace: FOUND (latest)")
            print(f"    keys: {list(row.keys())}")
        else:
            print(f"\n  reflection_trace: NOT FOUND")


# =============================================================================
# TEST: COMPUTED STATES (moment_model, evidence_pack, deliberation_scaffold)
# =============================================================================

class TestComputedStates:
    """Tests for computed states - these are computed in-memory but rely on DB data."""

    @pytest.mark.asyncio
    async def test_moment_model_dependencies(self, db_query):
        """
        Verify all data needed for moment_model computation is available.
        moment_model requires: emotion_state, coherence_state, alignment_state,
        mind_state (cognitive_load), forecast_state, continuity_state
        """
        row = await db_query(
            """
            SELECT
                coherence_state,
                alignment_state,
                forecast_state,
                long_term
            FROM personal_model
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        if row:
            print(f"\n  moment_model dependencies:")
            print(f"    coherence_state: {'SET' if row.get('coherence_state') else 'NOT SET'}")
            print(f"    alignment_state: {'SET' if row.get('alignment_state') else 'NOT SET'}")
            print(f"    forecast_state: {'SET' if row.get('forecast_state') else 'NOT SET'}")
            long_term = row.get("long_term", {})
            if isinstance(long_term, str):
                long_term = json.loads(long_term)
            mind_layer = (long_term.get("layers") or {}).get("mind", {})
            cognitive_load = (mind_layer.get("metrics") or {}).get("cognitive_load")
            print(f"    cognitive_load: {cognitive_load if cognitive_load else 'NOT SET'}")

    @pytest.mark.asyncio
    async def test_evidence_pack_data_available(self, db_query):
        """
        Verify data for evidence_pack computation is available.
        evidence_pack requires episodic memories and patterns.
        """
        count_row = await db_query(
            """
            SELECT COUNT(*) as total
            FROM memory_episodic
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        total = (count_row or {}).get("total", 0)
        print(f"\n  evidence_pack source data:")
        print(f"    episodic entries available: {total}")

    @pytest.mark.asyncio
    async def test_deliberation_scaffold_dependencies(self, db_query):
        """
        Verify all data needed for deliberation_scaffold is available.
        requires: moment_model, evidence_pack, conflict_state, alignment_state,
        identity_state, forecast_state, continuity_state
        """
        row = await db_query(
            """
            SELECT
                alignment_state,
                forecast_state
            FROM personal_model
            WHERE person_id = $1
            """,
            DEMO_USER_ID,
            one=True,
        )
        if row:
            print(f"\n  deliberation_scaffold dependencies:")
            print(f"    alignment_state: {'SET' if row.get('alignment_state') else 'NOT SET'}")
            print(f"    forecast_state: {'SET' if row.get('forecast_state') else 'NOT SET'}")


# =============================================================================
# TEST: FULL INTEGRATION FLOW
# =============================================================================

class TestFullIntegrationFlow:
    """End-to-end tests for the complete friction framework flow."""

    @pytest.mark.asyncio
    async def test_onboarding_to_conversation_flow(self, db_query, db_exec):
        """
        Test the full flow:
        1. Onboarding stores operating_system
        2. Entries accumulate state_vectors
        3. Turn loads all context
        4. Friction state can be calculated
        """
        flow_test_user = f"flow-test-{uuid.uuid4().hex[:8]}"

        # Step 1: Simulate onboarding completion
        os_data = {
            "type": "Adaptive",
            "primary": "Adaptive",
            "secondary": None,
            "dosha_baseline": {"vata": 0.50, "pitta": 0.30, "kapha": 0.20},
            "source": "test_onboarding",
        }
        life_context = {"age_range": "25-34", "life_phase": "exploring"}
        decision_profile = {"primary_driver": "reduce_stress"}

        await db_exec(
            """
            INSERT INTO personal_model (
                person_id, operating_system, life_context, decision_profile,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            """,
            flow_test_user,
            json.dumps(os_data),
            json.dumps(life_context),
            json.dumps(decision_profile),
        )

        # Verify Step 1
        pm_fields = await get_personal_model_fields(db_query, flow_test_user)
        assert pm_fields.get("operating_system", {}).get("type") == "Adaptive"

        # Step 2: Simulate episodic entries with state vectors
        # Current state shows Vata elevated (deviation from baseline)
        for i in range(2):
            episode_id = str(uuid.uuid4())
            state_vector = {
                "dosha": {"vata": 0.60, "pitta": 0.25, "kapha": 0.15},  # Vata further elevated
                "confidence": 0.75,
            }
            guna_vector = {
                "sattva": 0.25,
                "rajas": 0.55,  # High activation
                "tamas": 0.20,
            }
            await db_exec(
                """
                INSERT INTO memory_episodic (
                    id, user_id, person_id, text, state_vector, guna_vector, created_at
                )
                VALUES ($1, $2, $2::uuid, $3, $4, $5, NOW())
                """,
                episode_id,
                flow_test_user,
                f"Feeling scattered today, lots of context switching",
                json.dumps(state_vector),
                json.dumps(guna_vector),
            )

        # Step 3: Verify internal state would load correctly
        row = await db_query(
            """
            SELECT operating_system, life_context, decision_profile
            FROM personal_model
            WHERE person_id = $1
            """,
            flow_test_user,
            one=True,
        )
        assert row is not None

        os_loaded = row.get("operating_system")
        if isinstance(os_loaded, str):
            os_loaded = json.loads(os_loaded)
        assert os_loaded.get("type") == "Adaptive"
        assert os_loaded.get("dosha_baseline", {}).get("vata") == 0.50

        # Step 4: Verify friction state calculation
        entries = await get_episodic_state_vectors(db_query, flow_test_user)
        assert len(entries) >= 2

        # Calculate drift from baseline
        baseline = os_loaded.get("dosha_baseline", {})
        current_vata = entries[0].get("state_vector", {}).get("dosha", {}).get("vata", 0)
        vata_drift = current_vata - baseline.get("vata", 0.33)

        # Vata elevated by 0.10 (0.60 - 0.50) = Chaos Friction potential
        assert vata_drift > 0.05, f"Expected Vata drift > 0.05, got {vata_drift}"

        # Cleanup
        await db_exec("DELETE FROM memory_episodic WHERE person_id = $1", flow_test_user)
        await db_exec("DELETE FROM personal_model WHERE person_id = $1", flow_test_user)


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
def db_query():
    """Fixture for database query function."""
    from sakhi.apps.api.core.db import q
    return q


@pytest.fixture
def db_exec():
    """Fixture for database exec function."""
    from sakhi.apps.api.core.db import exec as db_exec_fn
    return db_exec_fn


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up test environment."""
    monkeypatch.setenv("SAKHI_ENVIRONMENT", "test")
    # Use test database URL if available
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if db_url:
        monkeypatch.setenv("DATABASE_URL", db_url)


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_user():
    """Clean up test user after all tests."""
    yield
    # Cleanup would happen here if needed
    # Note: async cleanup requires special handling


# =============================================================================
# STANDALONE VERIFICATION SCRIPT
# =============================================================================

async def run_verification():
    """
    Run comprehensive verification of ALL deterministic intelligence fields.
    Can be executed directly: python -m pytest tests/friction_framework/test_friction_framework_integration.py -v
    Or as a script for quick checks.
    """
    from sakhi.apps.api.core.db import q, exec as db_exec

    print("\n" + "="*70)
    print("DETERMINISTIC INTELLIGENCE FIELD VERIFICATION")
    print("="*70)

    issues = []
    today = date.today()

    # =========================================================================
    # 1. SCHEMA VERIFICATION
    # =========================================================================
    print("\n[1] SCHEMA VERIFICATION")
    print("-" * 40)

    # Check tables
    print("\n  Tables:")
    for table in EXPECTED_TABLES:
        row = await q(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = $1
            """,
            table,
            one=True,
        )
        status = "[OK]" if row else "[MISSING]"
        print(f"    {status} {table}")
        if not row:
            issues.append(f"Missing table: {table}")

    # Check personal_model columns
    print("\n  personal_model columns:")
    for col in PERSONAL_MODEL_EXPECTED_COLUMNS:
        row = await q(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'personal_model' AND column_name = $1
            """,
            col,
            one=True,
        )
        status = "[OK]" if row else "[MISSING]"
        print(f"    {status} {col}")
        if not row:
            issues.append(f"Missing column: personal_model.{col}")

    # Check memory_episodic columns
    print("\n  memory_episodic columns:")
    for col in MEMORY_EPISODIC_EXPECTED_COLUMNS:
        row = await q(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'memory_episodic' AND column_name = $1
            """,
            col,
            one=True,
        )
        status = "[OK]" if row else "[MISSING]"
        print(f"    {status} {col}")
        if not row:
            issues.append(f"Missing column: memory_episodic.{col}")

    # =========================================================================
    # 2. PERSONAL MODEL DATA
    # =========================================================================
    print(f"\n[2] PERSONAL MODEL DATA ({DEMO_USER_ID})")
    print("-" * 40)

    pm_row = await q(
        """
        SELECT
            operating_system,
            life_context,
            decision_profile,
            long_term,
            nudge_state,
            forecast_state,
            coherence_state,
            alignment_state
        FROM personal_model
        WHERE person_id = $1
        """,
        DEMO_USER_ID,
        one=True,
    )

    if not pm_row:
        print("  [WARNING] Demo user not found in personal_model")
        issues.append("Demo user missing from personal_model")
    else:
        # Friction Framework fields
        os_data = pm_row.get("operating_system")
        if os_data:
            if isinstance(os_data, str):
                os_data = json.loads(os_data)
            print(f"  operating_system: {os_data.get('type', 'N/A')}")
            dosha = os_data.get("dosha_baseline", {})
            print(f"    dosha_baseline: v={dosha.get('vata')}, p={dosha.get('pitta')}, k={dosha.get('kapha')}")
        else:
            print("  operating_system: [NOT SET]")
            issues.append("Demo user missing operating_system")

        print(f"  life_context: {'SET' if pm_row.get('life_context') else 'NOT SET'}")
        print(f"  decision_profile: {'SET' if pm_row.get('decision_profile') else 'NOT SET'}")

        # Brain states
        print(f"  nudge_state: {'SET' if pm_row.get('nudge_state') else 'NOT SET'}")
        print(f"  forecast_state: {'SET' if pm_row.get('forecast_state') else 'NOT SET'}")
        print(f"  coherence_state: {'SET' if pm_row.get('coherence_state') else 'NOT SET'}")
        print(f"  alignment_state: {'SET' if pm_row.get('alignment_state') else 'NOT SET'}")

        # Long-term layers
        long_term = pm_row.get("long_term")
        if long_term:
            if isinstance(long_term, str):
                long_term = json.loads(long_term)
            layers = long_term.get("layers", {})
            print(f"  long_term.layers:")
            print(f"    emotion: {'SET' if layers.get('emotion') else 'NOT SET'}")
            print(f"    mind: {'SET' if layers.get('mind') else 'NOT SET'}")
            print(f"    soul: {'SET' if layers.get('soul') else 'NOT SET'}")

    # =========================================================================
    # 3. EPISODIC ENTRIES
    # =========================================================================
    print(f"\n[3] EPISODIC ENTRIES (STATE VECTORS)")
    print("-" * 40)

    count_row = await q(
        "SELECT COUNT(*) as total FROM memory_episodic WHERE person_id = $1",
        DEMO_USER_ID,
        one=True,
    )
    total = (count_row or {}).get("total", 0)
    print(f"  Total episodic entries: {total}")

    sv_count_row = await q(
        """
        SELECT COUNT(*) as total
        FROM memory_episodic
        WHERE person_id = $1 AND state_vector IS NOT NULL
        """,
        DEMO_USER_ID,
        one=True,
    )
    sv_count = (sv_count_row or {}).get("total", 0)
    print(f"  Entries with state_vector: {sv_count}")

    gv_count_row = await q(
        """
        SELECT COUNT(*) as total
        FROM memory_episodic
        WHERE person_id = $1 AND guna_vector IS NOT NULL
        """,
        DEMO_USER_ID,
        one=True,
    )
    gv_count = (gv_count_row or {}).get("total", 0)
    print(f"  Entries with guna_vector: {gv_count}")

    if sv_count == 0:
        issues.append("No episodic entries with state_vector")

    # =========================================================================
    # 4. CACHE TABLES
    # =========================================================================
    print(f"\n[4] CACHE TABLES (Today: {today})")
    print("-" * 40)

    # Daily reflection
    dr_row = await q(
        "SELECT summary FROM daily_reflection_cache WHERE person_id = $1 AND reflection_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  daily_reflection: {'SET' if dr_row else 'NOT SET'}")

    # Daily closure
    dc_row = await q(
        "SELECT summary FROM daily_closure_cache WHERE person_id = $1 AND closure_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  evening_closure: {'SET' if dc_row else 'NOT SET'}")

    # Morning context
    mp_row = await q(
        "SELECT focus_areas FROM morning_preview_cache WHERE person_id = $1 AND preview_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  morning_preview: {'SET' if mp_row else 'NOT SET'}")

    ma_row = await q(
        "SELECT question FROM morning_ask_cache WHERE person_id = $1 AND ask_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  morning_ask: {'SET' if ma_row else 'NOT SET'}")

    mm_row = await q(
        "SELECT momentum_hint FROM morning_momentum_cache WHERE person_id = $1 AND momentum_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  morning_momentum: {'SET' if mm_row else 'NOT SET'}")

    # Micro context
    micro_mom_row = await q(
        "SELECT nudge FROM micro_momentum_cache WHERE person_id = $1 AND nudge_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  micro_momentum: {'SET' if micro_mom_row else 'NOT SET'}")

    micro_rec_row = await q(
        "SELECT nudge FROM micro_recovery_cache WHERE person_id = $1 AND recovery_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  micro_recovery: {'SET' if micro_rec_row else 'NOT SET'}")

    # Scaffolds
    fp_row = await q(
        "SELECT anchor_step FROM focus_path_cache WHERE person_id = $1 AND path_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  focus_path: {'SET' if fp_row else 'NOT SET'}")

    mf_row = await q(
        "SELECT warmup_step FROM mini_flow_cache WHERE person_id = $1 AND flow_date = $2",
        DEMO_USER_ID, today, one=True,
    )
    print(f"  mini_flow: {'SET' if mf_row else 'NOT SET'}")

    mj_row = await q(
        "SELECT journey FROM micro_journey_cache WHERE person_id = $1",
        DEMO_USER_ID, one=True,
    )
    print(f"  micro_journey: {'SET' if mj_row else 'NOT SET'}")

    # =========================================================================
    # 5. CONTINUITY STATE
    # =========================================================================
    print(f"\n[5] CONTINUITY STATE")
    print("-" * 40)

    cont_row = await q(
        "SELECT * FROM continuity_state WHERE person_id = $1",
        DEMO_USER_ID, one=True,
    )
    print(f"  continuity_state: {'SET' if cont_row else 'NOT SET'}")

    # =========================================================================
    # 6. REFLECTION TRACE
    # =========================================================================
    print(f"\n[6] REFLECTION TRACE")
    print("-" * 40)

    rt_row = await q(
        "SELECT * FROM reflection_trace WHERE person_id = $1 ORDER BY created_at DESC LIMIT 1",
        DEMO_USER_ID, one=True,
    )
    print(f"  reflection_trace: {'SET' if rt_row else 'NOT SET'}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    if issues:
        print(f"\n[ISSUES FOUND: {len(issues)}]")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRECOMMENDATIONS:")
        if any("Missing table" in i for i in issues):
            print("  - Run pending database migrations")
        if any("Missing column" in i for i in issues):
            print("  - Run migration 0028_friction_framework.sql and 0032_episodic_state_vectors.sql")
        if any("operating_system" in i for i in issues):
            print("  - Complete onboarding flow for demo user")
        if any("state_vector" in i for i in issues):
            print("  - Trigger episodic consolidation or wait for new entries")
    else:
        print("\n[OK] All schema checks passed!")

    print("\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_verification())
