"""
Integration tests for rhythm and energy workers.

Tests actual database operations for:
- Energy tracking
- Dosha balance
- Behavior logging
- Symptom tracking
- Personal patterns
- Intervention plans
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
import uuid

from sakhi.tests.fixtures import DEMO_USER_ID


@pytest.mark.integration
class TestEnergyTrackingIntegration:
    """Integration tests for energy state tracking."""

    @pytest.mark.asyncio
    async def test_energy_state_stored(self, db, ensure_test_user):
        """
        Given: User reports energy level
        When: Stored in personal_model_energy
        Then: Energy data is persisted
        """
        await ensure_test_user(DEMO_USER_ID)

        baseline = json.dumps({"morning": 0.7, "afternoon": 0.6, "evening": 0.5})
        volatility = json.dumps({"reactivity": 0.3})
        recovery = json.dumps({"half_life": 4})
        circulation = json.dumps({"stability": 0.7})

        await db.execute("""
            INSERT INTO personal_model_energy (person_id, baseline, volatility, recovery_profile, circulation_stability, confidence, updated_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, $6, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET baseline = $2::jsonb, volatility = $3::jsonb, recovery_profile = $4::jsonb,
                circulation_stability = $5::jsonb, confidence = $6, updated_at = NOW()
        """, DEMO_USER_ID, baseline, volatility, recovery, circulation, 0.8)

        result = await db.fetchrow(
            "SELECT * FROM personal_model_energy WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result is not None
        assert float(result["confidence"]) == 0.8

    @pytest.mark.asyncio
    async def test_energy_baseline_with_recovery_profile(self, db, ensure_test_user):
        """
        Given: User has energy data with recovery profile
        When: Updated with new profile
        Then: Both baseline and recovery are stored
        """
        await ensure_test_user(DEMO_USER_ID)

        baseline = json.dumps({"morning": 0.8, "afternoon": 0.7, "evening": 0.6})
        volatility = json.dumps({"reactivity": 0.4})
        recovery = json.dumps({"half_life_hours": 4, "optimal_rest": "afternoon"})
        circulation = json.dumps({"stability": 0.8})

        await db.execute("""
            INSERT INTO personal_model_energy (person_id, baseline, volatility, recovery_profile, circulation_stability, confidence, updated_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, $6, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET baseline = $2::jsonb, volatility = $3::jsonb, recovery_profile = $4::jsonb,
                circulation_stability = $5::jsonb, confidence = $6, updated_at = NOW()
        """, DEMO_USER_ID, baseline, volatility, recovery, circulation, 0.75)

        result = await db.fetchrow(
            "SELECT baseline, recovery_profile FROM personal_model_energy WHERE person_id = $1",
            DEMO_USER_ID
        )
        assert result is not None
        baseline_data = result["baseline"] if isinstance(result["baseline"], dict) else json.loads(result["baseline"])
        assert baseline_data["morning"] == 0.8


@pytest.mark.integration
class TestDoshaBalanceIntegration:
    """Integration tests for Ayurvedic dosha tracking."""

    @pytest.mark.asyncio
    async def test_elemental_summary_created(self, db, ensure_test_user):
        """
        Given: Week of dosha observations
        When: Weekly summary runs
        Then: Elemental summary is stored
        """
        await ensure_test_user(DEMO_USER_ID)

        summary_id = str(uuid.uuid4())
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).date()
        elements = json.dumps({"vata": 0.4, "pitta": 0.35, "kapha": 0.25})
        dosha_balance = json.dumps({"primary": "vata", "secondary": "pitta"})

        await db.execute("""
            INSERT INTO elemental_summary_weekly
            (id, person_id, week_start, elements, dosha_balance, signals_count, confidence, created_at, updated_at)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7, NOW(), NOW())
            ON CONFLICT (person_id, week_start) DO UPDATE
            SET elements = $4::jsonb, dosha_balance = $5::jsonb, signals_count = $6, confidence = $7, updated_at = NOW()
        """, summary_id, DEMO_USER_ID, week_start, elements, dosha_balance, 15, 0.75)

        result = await db.fetchrow("""
            SELECT * FROM elemental_summary_weekly
            WHERE person_id = $1 AND week_start = $2
        """, DEMO_USER_ID, week_start)

        assert result is not None
        assert result["signals_count"] == 15
        elem = result["elements"] if isinstance(result["elements"], dict) else json.loads(result["elements"])
        assert elem["vata"] == 0.4

        # Cleanup
        await db.execute("DELETE FROM elemental_summary_weekly WHERE id = $1", summary_id)

    @pytest.mark.asyncio
    async def test_dosha_balance_update(self, db, ensure_test_user):
        """
        Given: Existing elemental summary
        When: New signals come in
        Then: Summary is updated with new balance
        """
        await ensure_test_user(DEMO_USER_ID)

        summary_id = str(uuid.uuid4())
        week_start = (datetime.now(timezone.utc) - timedelta(days=14)).date()

        # Initial insert
        elements = json.dumps({"vata": 0.3, "pitta": 0.4, "kapha": 0.3})
        await db.execute("""
            INSERT INTO elemental_summary_weekly
            (id, person_id, week_start, elements, signals_count, confidence, created_at, updated_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, NOW(), NOW())
        """, summary_id, DEMO_USER_ID, week_start, elements, 5, 0.5)

        # Update with more signals
        new_elements = json.dumps({"vata": 0.5, "pitta": 0.3, "kapha": 0.2})
        await db.execute("""
            UPDATE elemental_summary_weekly
            SET elements = $3::jsonb, signals_count = $4, confidence = $5, updated_at = NOW()
            WHERE person_id = $1 AND week_start = $2
        """, DEMO_USER_ID, week_start, new_elements, 20, 0.85)

        result = await db.fetchrow("""
            SELECT * FROM elemental_summary_weekly
            WHERE person_id = $1 AND week_start = $2
        """, DEMO_USER_ID, week_start)

        assert result is not None
        assert result["signals_count"] == 20
        assert float(result["confidence"]) == 0.85

        # Cleanup
        await db.execute("DELETE FROM elemental_summary_weekly WHERE id = $1", summary_id)


@pytest.mark.integration
class TestBehaviorLoggingIntegration:
    """Integration tests for behavior tracking."""

    @pytest.mark.asyncio
    async def test_behavior_logged(self, db, ensure_test_user):
        """
        Given: User behavior observed
        When: Logged via worker
        Then: Behavior with dosha effect stored
        """
        await ensure_test_user(DEMO_USER_ID)

        behavior_id = str(uuid.uuid4())

        await db.execute("""
            INSERT INTO behavior_log
            (id, person_id, behavior_type, behavior_name, occurred_at, dosha_effect, effect_direction, intensity, source_type, created_at)
            VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7, $8, NOW())
        """, behavior_id, DEMO_USER_ID, "food", "coffee", "pitta", "aggravates", 0.6, "conversation")

        result = await db.fetchrow(
            "SELECT * FROM behavior_log WHERE id = $1",
            behavior_id
        )

        assert result is not None
        assert result["behavior_name"] == "coffee"
        assert result["dosha_effect"] == "pitta"
        assert result["effect_direction"] == "aggravates"

        # Cleanup
        await db.execute("DELETE FROM behavior_log WHERE id = $1", behavior_id)

    @pytest.mark.asyncio
    async def test_multiple_behaviors_in_day(self, db, ensure_test_user):
        """
        Given: Multiple behaviors in one day
        When: Queried by date
        Then: All behaviors returned
        """
        await ensure_test_user(DEMO_USER_ID)

        behavior_ids = [str(uuid.uuid4()) for _ in range(3)]
        behaviors = [
            ("food", "spicy_meal", "pitta", "aggravates", 0.7),
            ("activity", "yoga", "vata", "balances", 0.5),
            ("sleep", "late_night", "vata", "aggravates", 0.8),
        ]

        for bid, (btype, bname, dosha, effect, intensity) in zip(behavior_ids, behaviors):
            await db.execute("""
                INSERT INTO behavior_log
                (id, person_id, behavior_type, behavior_name, occurred_at, dosha_effect, effect_direction, intensity, source_type, created_at)
                VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7, $8, NOW())
            """, bid, DEMO_USER_ID, btype, bname, dosha, effect, intensity, "observation")

        # Query today's behaviors
        results = await db.fetch("""
            SELECT * FROM behavior_log
            WHERE person_id = $1 AND DATE(occurred_at) = CURRENT_DATE
            ORDER BY created_at
        """, DEMO_USER_ID)

        assert len(results) >= 3

        # Cleanup
        for bid in behavior_ids:
            await db.execute("DELETE FROM behavior_log WHERE id = $1", bid)


@pytest.mark.integration
class TestSymptomTrackingIntegration:
    """Integration tests for symptom logging."""

    @pytest.mark.asyncio
    async def test_symptom_logged(self, db, ensure_test_user):
        """
        Given: User reports a symptom
        When: Logged via worker
        Then: Symptom stored with ayurvedic context
        """
        await ensure_test_user(DEMO_USER_ID)

        symptom_id = str(uuid.uuid4())

        await db.execute("""
            INSERT INTO symptom_log
            (id, person_id, symptom_type, symptom_name, severity, time_of_day, occurred_at, related_dosha, source, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8, NOW())
        """, symptom_id, DEMO_USER_ID, "digestive", "bloating", 0.6, "afternoon", "vata", "conversation")

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
    async def test_symptom_resolution_tracked(self, db, ensure_test_user):
        """
        Given: Symptom reported
        When: Later resolved
        Then: Resolution time and what helped recorded
        """
        await ensure_test_user(DEMO_USER_ID)

        symptom_id = str(uuid.uuid4())
        what_helped = json.dumps(["ginger tea", "rest"])

        # Insert symptom
        await db.execute("""
            INSERT INTO symptom_log
            (id, person_id, symptom_type, symptom_name, severity, occurred_at, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours')
        """, symptom_id, DEMO_USER_ID, "digestive", "nausea", 0.7)

        # Update with resolution
        await db.execute("""
            UPDATE symptom_log
            SET resolution_time = NOW(), what_helped = $2::jsonb, resolution_summary = $3
            WHERE id = $1
        """, symptom_id, what_helped, "Resolved after ginger tea")

        result = await db.fetchrow(
            "SELECT * FROM symptom_log WHERE id = $1",
            symptom_id
        )
        assert result is not None
        assert result["resolution_time"] is not None
        assert result["resolution_summary"] == "Resolved after ginger tea"

        # Cleanup
        await db.execute("DELETE FROM symptom_log WHERE id = $1", symptom_id)


@pytest.mark.integration
class TestPersonalPatternsIntegration:
    """Integration tests for personal pattern detection."""

    @pytest.mark.asyncio
    async def test_pattern_created(self, db, ensure_test_user):
        """
        Given: Correlation detected
        When: Pattern stored
        Then: Pattern with dosha context persisted
        """
        await ensure_test_user(DEMO_USER_ID)

        pattern_id = str(uuid.uuid4())

        await db.execute("""
            INSERT INTO personal_patterns
            (id, person_id, cause_type, cause_value, effect_type, effect_value,
             correlation_strength, confidence, observation_count, related_dosha, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
            ON CONFLICT (person_id, cause_type, cause_value, effect_type, effect_value)
            DO UPDATE SET correlation_strength = $7, confidence = $8, observation_count = $9, updated_at = NOW()
        """, pattern_id, DEMO_USER_ID, "food", "dairy", "symptom", "bloating", 0.75, 0.8, 5, "kapha")

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

    @pytest.mark.asyncio
    async def test_pattern_strengthens_with_observations(self, db, ensure_test_user):
        """
        Given: Existing pattern
        When: More observations confirm it
        Then: Correlation strength increases
        """
        await ensure_test_user(DEMO_USER_ID)

        pattern_id = str(uuid.uuid4())
        # Use unique cause/effect values for this test
        unique_suffix = pattern_id[:8]

        # Initial pattern
        await db.execute("""
            INSERT INTO personal_patterns
            (id, person_id, cause_type, cause_value, effect_type, effect_value,
             correlation_strength, confidence, observation_count, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
        """, pattern_id, DEMO_USER_ID, "activity", f"late_night_screen_{unique_suffix}", "symptom", f"insomnia_{unique_suffix}", 0.5, 0.4, 3)

        # Update with more observations
        await db.execute("""
            UPDATE personal_patterns
            SET correlation_strength = $2, confidence = $3, observation_count = $4, updated_at = NOW()
            WHERE id = $1
        """, pattern_id, 0.85, 0.9, 12)

        result = await db.fetchrow(
            "SELECT * FROM personal_patterns WHERE id = $1",
            pattern_id
        )
        assert result is not None
        assert result["observation_count"] == 12
        assert float(result["correlation_strength"]) == 0.85

        # Cleanup
        await db.execute("DELETE FROM personal_patterns WHERE id = $1", pattern_id)


@pytest.mark.integration
class TestInterventionTrackingIntegration:
    """Integration tests for intervention plans."""

    @pytest.mark.asyncio
    async def test_intervention_plan_created(self, db, ensure_test_user):
        """
        Given: User needs an intervention
        When: Plan created
        Then: Plan with schedule stored
        """
        await ensure_test_user(DEMO_USER_ID)

        plan_id = str(uuid.uuid4())
        start_date = datetime.now(timezone.utc).date()
        end_date = start_date + timedelta(days=30)

        await db.execute("""
            INSERT INTO intervention_plans
            (id, person_id, intervention_type, intervention_name, schedule_type, target_per_day,
             start_date, end_date, target_symptom, target_dosha, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
        """, plan_id, DEMO_USER_ID, "activity", "morning_walk", "daily", 1,
            start_date, end_date, "low_energy", "kapha", "active")

        result = await db.fetchrow(
            "SELECT * FROM intervention_plans WHERE id = $1",
            plan_id
        )

        assert result is not None
        assert result["intervention_name"] == "morning_walk"
        assert result["status"] == "active"
        assert result["target_dosha"] == "kapha"

        # Cleanup
        await db.execute("DELETE FROM intervention_plans WHERE id = $1", plan_id)

    @pytest.mark.asyncio
    async def test_intervention_checkin_recorded(self, db, ensure_test_user):
        """
        Given: Active intervention plan
        When: User checks in
        Then: Checkin with mood recorded
        """
        await ensure_test_user(DEMO_USER_ID)

        plan_id = str(uuid.uuid4())
        checkin_id = str(uuid.uuid4())
        today = datetime.now(timezone.utc).date()

        # Create plan first
        await db.execute("""
            INSERT INTO intervention_plans
            (id, person_id, intervention_type, intervention_name, schedule_type, target_per_day,
             start_date, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
        """, plan_id, DEMO_USER_ID, "mindfulness", "meditation", "daily", 1, today, "active")

        # Record checkin
        await db.execute("""
            INSERT INTO intervention_checkins
            (id, plan_id, scheduled_date, status, completed_count, mood_before, mood_after, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, checkin_id, plan_id, today, "done", 1, 0.5, 0.8)

        result = await db.fetchrow(
            "SELECT * FROM intervention_checkins WHERE id = $1",
            checkin_id
        )

        assert result is not None
        assert result["status"] == "done"
        assert float(result["mood_before"]) == 0.5
        assert float(result["mood_after"]) == 0.8

        # Cleanup
        await db.execute("DELETE FROM intervention_checkins WHERE id = $1", checkin_id)
        await db.execute("DELETE FROM intervention_plans WHERE id = $1", plan_id)

    @pytest.mark.asyncio
    async def test_intervention_streak_tracking(self, db, ensure_test_user):
        """
        Given: Active intervention with checkins
        When: Streak is maintained
        Then: Streak count is updated
        """
        await ensure_test_user(DEMO_USER_ID)

        plan_id = str(uuid.uuid4())
        start_date = datetime.now(timezone.utc).date() - timedelta(days=7)

        # Create plan with streak data
        await db.execute("""
            INSERT INTO intervention_plans
            (id, person_id, intervention_type, intervention_name, schedule_type, target_per_day,
             start_date, status, total_scheduled, total_completed, current_streak, longest_streak,
             created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
        """, plan_id, DEMO_USER_ID, "activity", "yoga", "daily", 1,
            start_date, "active", 7, 6, 5, 5)

        # Update streak
        await db.execute("""
            UPDATE intervention_plans
            SET total_completed = $2, current_streak = $3, longest_streak = $4, updated_at = NOW()
            WHERE id = $1
        """, plan_id, 7, 6, 6)

        result = await db.fetchrow(
            "SELECT * FROM intervention_plans WHERE id = $1",
            plan_id
        )

        assert result is not None
        assert result["current_streak"] == 6
        assert result["longest_streak"] == 6

        # Cleanup
        await db.execute("DELETE FROM intervention_plans WHERE id = $1", plan_id)
