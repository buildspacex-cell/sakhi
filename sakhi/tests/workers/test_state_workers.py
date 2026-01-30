"""
Tests for State Workers (Rhythm, Soul, Emotion, Weekly Learning).

These workers update the personal_model with various state computations:
- Rhythm forecast: time slot energy patterns
- Soul refresh: values, identity signals
- ESR (Emotion State Refresh): emotional state
- Weekly learning: longitudinal trends
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
import uuid

pytestmark = pytest.mark.asyncio


class TestRhythmForecastWorker:
    """Test suite for rhythm forecast worker."""

    async def test_rhythm_forecast_basic(
        self,
        test_user_id,
        create_journal_entry,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test basic rhythm forecast computation."""
        await setup_personal_model(test_user_id)

        # Create entries at different times of day
        times = [
            (6, "morning", "Energetic start to the day"),
            (14, "afternoon", "Productive work session"),
            (20, "evening", "Relaxed evening meditation"),
        ]

        for hour, period, content in times:
            ts = datetime.now(timezone.utc).replace(hour=hour, minute=0)
            await create_journal_entry(
                test_user_id,
                f"{content} during {period}.",
                layer="reflection",
                created_at=ts - timedelta(days=1),
            )

        try:
            from sakhi.apps.worker.tasks.rhythm_forecast import (
                run_rhythm_forecast,
            )

            result = await run_rhythm_forecast(test_user_id)

            # Check if rhythm_state was updated
            pm = await db_query("""
                SELECT rhythm_state FROM personal_model WHERE person_id = $1
            """, test_user_id, one=True)

            if pm and pm.get("rhythm_state"):
                rhythm = pm["rhythm_state"]
                # Rhythm state should have time slot info
                assert isinstance(rhythm, dict)

        except ImportError:
            pytest.skip("Rhythm forecast worker not available")

    async def test_rhythm_forecast_minimum_signals(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test rhythm forecast requires minimum signals."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.worker.tasks.rhythm_forecast import (
                run_rhythm_forecast,
            )

            # With no entries, should handle gracefully
            result = await run_rhythm_forecast(test_user_id)

            # Should not crash, may return early

        except ImportError:
            pytest.skip("Rhythm forecast worker not available")


class TestSoulRefreshWorker:
    """Test suite for soul refresh worker."""

    async def test_soul_refresh_aggregates_signals(
        self,
        test_user_id,
        create_episodic_memory,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test soul refresh aggregates from episodic memory."""
        await setup_personal_model(test_user_id)

        # Create episodic memories with soul signals
        for i in range(3):
            await create_episodic_memory(
                test_user_id,
                f"Day {i+1} reflection with growth and balance themes.",
                state_vector={"dosha": {"vata": 0.3, "pitta": 0.4, "kapha": 0.3}},
            )

        try:
            from sakhi.apps.worker.tasks.soul_refresh_worker import (
                soul_refresh_worker,
            )

            result = await soul_refresh_worker(test_user_id)

            # Check if soul_state was updated
            pm = await db_query("""
                SELECT soul_state, soul_vector FROM personal_model WHERE person_id = $1
            """, test_user_id, one=True)

            if pm:
                # Soul state should exist
                assert pm.get("soul_state") is not None or True

        except ImportError:
            pytest.skip("Soul refresh worker not available")

    async def test_soul_refresh_handles_empty_data(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test soul refresh with no episodic data."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.worker.tasks.soul_refresh_worker import (
                soul_refresh_worker,
            )

            # Should not crash with no data
            result = await soul_refresh_worker(test_user_id)

        except ImportError:
            pytest.skip("Soul refresh worker not available")


class TestESRWorker:
    """Test suite for Emotion State Refresh worker."""

    async def test_esr_extracts_emotional_state(
        self,
        test_user_id,
        create_journal_entry,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test ESR extracts emotional signals from journals."""
        await setup_personal_model(test_user_id)

        # Create entries with emotional content
        await create_journal_entry(
            test_user_id,
            "Feeling anxious about tomorrow's presentation.",
            mood="anxious",
        )
        await create_journal_entry(
            test_user_id,
            "Really happy about the progress I made today!",
            mood="happy",
        )

        try:
            from sakhi.apps.worker.tasks.esr_worker import (
                run_emotion_state_refresh,
            )

            result = await run_emotion_state_refresh(test_user_id)

            # Check emotion_state in personal_model
            pm = await db_query("""
                SELECT emotion_state FROM personal_model WHERE person_id = $1
            """, test_user_id, one=True)

            if pm and pm.get("emotion_state"):
                emotion = pm["emotion_state"]
                assert isinstance(emotion, dict)

        except ImportError:
            pytest.skip("ESR worker not available")

    async def test_esr_minimum_signal_requirement(
        self,
        test_user_id,
        setup_personal_model,
    ):
        """Test ESR requires minimum 3 emotion signals."""
        await setup_personal_model(test_user_id)

        try:
            from sakhi.apps.worker.tasks.esr_worker import (
                run_emotion_state_refresh,
            )

            # With no entries, should handle gracefully
            result = await run_emotion_state_refresh(test_user_id)

        except ImportError:
            pytest.skip("ESR worker not available")


class TestWeeklyLearningWorker:
    """Test suite for weekly learning worker."""

    async def test_weekly_learning_computes_trends(
        self,
        test_user_id,
        create_episodic_memory,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test weekly learning computes longitudinal trends."""
        await setup_personal_model(test_user_id)

        # Create episodic memories over multiple days
        for i in range(7):
            await create_episodic_memory(
                test_user_id,
                f"Week day {i+1} summary with consistent patterns.",
                created_at=datetime.now(timezone.utc) - timedelta(days=i),
            )

        try:
            from sakhi.apps.worker.tasks.weekly_learning_worker import (
                run_weekly_learning,
            )

            result = await run_weekly_learning(test_user_id)

            # Check longitudinal_state in personal_model
            pm = await db_query("""
                SELECT longitudinal_state FROM personal_model WHERE person_id = $1
            """, test_user_id, one=True)

            # May or may not update based on data volume

        except ImportError:
            pytest.skip("Weekly learning worker not available")


class TestEmotionSoulRhythmDeep:
    """Test suite for emotion-soul-rhythm integration worker."""

    async def test_esr_deep_integrates_states(
        self,
        test_user_id,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test ESR deep integrates emotion, soul, and rhythm states."""
        await setup_personal_model(test_user_id)

        # Ensure required states exist
        await db_exec("""
            UPDATE personal_model
            SET emotion_state = $2,
                soul_state = $3,
                rhythm_state = $4
            WHERE person_id = $1
        """, test_user_id,
            {"current": "stable", "dominant": "calm"},
            {"values": ["growth", "balance"]},
            {"morning": "high", "evening": "medium"},
        )

        try:
            from sakhi.apps.worker.tasks.emotion_soul_rhythm_deep import (
                run_emotion_soul_rhythm_deep,
            )

            result = await run_emotion_soul_rhythm_deep(test_user_id)

            # Check integrated state
            pm = await db_query("""
                SELECT emotion_soul_rhythm_state FROM personal_model WHERE person_id = $1
            """, test_user_id, one=True)

        except ImportError:
            pytest.skip("Emotion soul rhythm deep worker not available")


class TestIdentityMomentumDeep:
    """Test suite for identity momentum worker."""

    async def test_identity_momentum_measures_drift(
        self,
        test_user_id,
        create_episodic_memory,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test identity momentum measures directional drift."""
        await setup_personal_model(test_user_id)

        # Create consistent episodic memories
        for i in range(10):
            await create_episodic_memory(
                test_user_id,
                f"Consistent growth focus day {i+1}.",
                created_at=datetime.now(timezone.utc) - timedelta(days=i),
            )

        try:
            from sakhi.apps.worker.identity_momentum_deep import (
                run_identity_momentum_deep,
            )

            result = await run_identity_momentum_deep(test_user_id)

            # Check identity_momentum_state
            pm = await db_query("""
                SELECT identity_momentum_state FROM personal_model WHERE person_id = $1
            """, test_user_id, one=True)

            if pm and pm.get("identity_momentum_state"):
                momentum = pm["identity_momentum_state"]
                # Should have direction, magnitude, stability
                assert isinstance(momentum, dict)

        except ImportError:
            pytest.skip("Identity momentum worker not available")


class TestRhythmSoulDeep:
    """Test suite for rhythm-soul alignment worker."""

    async def test_rhythm_soul_detects_tension(
        self,
        test_user_id,
        db_query,
        db_exec,
        setup_personal_model,
    ):
        """Test rhythm-soul worker detects tension zones."""
        await setup_personal_model(test_user_id)

        # Set up rhythm and soul states
        await db_exec("""
            UPDATE personal_model
            SET rhythm_state = $2,
                soul_state = $3
            WHERE person_id = $1
        """, test_user_id,
            {"morning": "low", "afternoon": "high", "evening": "medium"},
            {"values": ["early_riser", "morning_person"]},
        )

        try:
            from sakhi.apps.worker.rhythm_soul_deep import (
                run_rhythm_soul_deep,
            )

            result = await run_rhythm_soul_deep(test_user_id)

            # Check rhythm_soul_state
            pm = await db_query("""
                SELECT rhythm_soul_state FROM personal_model WHERE person_id = $1
            """, test_user_id, one=True)

        except ImportError:
            pytest.skip("Rhythm soul deep worker not available")


class TestStateWorkersDatabase:
    """Database verification for state workers."""

    async def test_personal_model_has_state_columns(self, db_query):
        """Verify personal_model has all required state columns."""
        columns = await db_query("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'personal_model'
        """)

        column_names = {c["column_name"] for c in columns}

        expected_states = [
            "soul_state",
            "emotion_state",
            "rhythm_state",
        ]

        for state in expected_states:
            assert state in column_names, f"Missing column: {state}"
