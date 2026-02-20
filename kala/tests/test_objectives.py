"""Tests for kala.objectives — versioned objectives, staleness, governance integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kala.constraints.core import (
    PRIORITY_HARD,
    PRIORITY_SOFT,
    Constraint,
    ConstraintSet,
)
from kala.governance.gate import GovernanceGate
from kala.ledger.core import Event, Ledger
from kala.objectives.core import ObjectiveStore, ObjectiveVersion
from kala.objectives.staleness import (
    find_stale_constraints,
    format_source,
    invalidated_by,
    parse_objective_source,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_version(
    *,
    objective_id: str = "sleep-goal",
    version: int = 1,
    timestamp: datetime = _T0,
    title: str = "Sleep by 10pm",
    description: str = "",
    data: dict | None = None,
    source: str = "user_input",
    reason: str = "",
    parent_version: int | None = None,
) -> ObjectiveVersion:
    return ObjectiveVersion(
        objective_id=objective_id,
        version=version,
        timestamp=timestamp,
        title=title,
        description=description,
        data=data or {},
        source=source,
        reason=reason,
        parent_version=parent_version,
    )


def _make_constraint(
    *,
    id: str = "c1",
    field: str = "proposed_hour",
    operator: str = "lte",
    value: object = 22,
    source: str = "objective:sleep-goal:v1",
    priority: int = PRIORITY_SOFT,
) -> Constraint:
    return Constraint(
        id=id,
        constraint_type="time_boundary",
        field=field,
        operator=operator,
        value=value,
        description="test",
        source=source,
        priority=priority,
    )


# ===========================================================================
# ObjectiveVersion
# ===========================================================================


class TestObjectiveVersion:
    def test_creation(self) -> None:
        v = _make_version()
        assert v.objective_id == "sleep-goal"
        assert v.version == 1
        assert v.title == "Sleep by 10pm"

    def test_frozen(self) -> None:
        v = _make_version()
        with pytest.raises(AttributeError):
            v.version = 2  # type: ignore[misc]

    def test_defaults(self) -> None:
        v = _make_version()
        assert v.description == ""
        assert v.data == {}
        assert v.reason == ""
        assert v.parent_version is None

    def test_parent_version(self) -> None:
        v = _make_version(version=2, parent_version=1, reason="Refined after check-in")
        assert v.parent_version == 1
        assert v.reason == "Refined after check-in"


# ===========================================================================
# ObjectiveStore
# ===========================================================================


class TestObjectiveStore:
    def test_add_and_len(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(objective_id="a"))
        store.add(_make_version(objective_id="b"))
        assert len(store) == 2

    def test_current(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        store.add(_make_version(version=2, timestamp=_T0 + timedelta(days=7)))
        current = store.current("sleep-goal")
        assert current is not None
        assert current.version == 2

    def test_current_nonexistent(self) -> None:
        store = ObjectiveStore()
        assert store.current("nope") is None

    def test_get_version(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1, title="v1"))
        store.add(_make_version(version=2, title="v2"))
        v1 = store.get_version("sleep-goal", 1)
        assert v1 is not None
        assert v1.title == "v1"

    def test_get_version_out_of_range(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        assert store.get_version("sleep-goal", 5) is None
        assert store.get_version("sleep-goal", 0) is None

    def test_history(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        store.add(_make_version(version=2))
        history = store.history("sleep-goal")
        assert len(history) == 2
        assert history[0].version == 1
        assert history[1].version == 2

    def test_history_nonexistent(self) -> None:
        store = ObjectiveStore()
        assert store.history("nope") == []

    def test_is_stale(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        store.add(_make_version(version=2))
        assert store.is_stale("sleep-goal", 1) is True
        assert store.is_stale("sleep-goal", 2) is False

    def test_is_stale_nonexistent(self) -> None:
        store = ObjectiveStore()
        assert store.is_stale("nope", 1) is False

    def test_sequential_enforcement(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        with pytest.raises(ValueError, match="Expected version 2"):
            store.add(_make_version(version=3))

    def test_objectives(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(objective_id="a"))
        store.add(_make_version(objective_id="b"))
        assert sorted(store.objectives()) == ["a", "b"]

    def test_bool(self) -> None:
        store = ObjectiveStore()
        assert not store
        store.add(_make_version())
        assert store

    def test_iter(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(objective_id="a"))
        store.add(_make_version(objective_id="b"))
        assert sorted(store) == ["a", "b"]


# ===========================================================================
# parse_objective_source / format_source
# ===========================================================================


class TestParseObjectiveSource:
    def test_valid(self) -> None:
        result = parse_objective_source("objective:sleep-goal:v2")
        assert result == ("sleep-goal", 2)

    def test_no_prefix(self) -> None:
        assert parse_objective_source("onboarding") is None

    def test_missing_version(self) -> None:
        assert parse_objective_source("objective:sleep-goal") is None

    def test_bad_format(self) -> None:
        assert parse_objective_source("objective::v2") is None

    def test_empty(self) -> None:
        assert parse_objective_source("") is None

    def test_format_source(self) -> None:
        assert format_source("sleep-goal", 2) == "objective:sleep-goal:v2"

    def test_roundtrip(self) -> None:
        source = format_source("my-goal", 3)
        parsed = parse_objective_source(source)
        assert parsed == ("my-goal", 3)


# ===========================================================================
# find_stale_constraints
# ===========================================================================


class TestFindStaleConstraints:
    def test_no_stale(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        cs = ConstraintSet()
        cs.add(_make_constraint(source="objective:sleep-goal:v1"))
        assert find_stale_constraints(cs, store) == []

    def test_one_stale(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        store.add(_make_version(version=2))
        cs = ConstraintSet()
        cs.add(_make_constraint(source="objective:sleep-goal:v1"))
        stale = find_stale_constraints(cs, store)
        assert len(stale) == 1
        assert stale[0][0].id == "c1"
        assert stale[0][1].version == 2

    def test_multiple_stale(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        store.add(_make_version(version=2))
        store.add(_make_version(version=3))
        cs = ConstraintSet()
        cs.add(_make_constraint(id="c1", source="objective:sleep-goal:v1"))
        cs.add(_make_constraint(id="c2", source="objective:sleep-goal:v2"))
        stale = find_stale_constraints(cs, store)
        assert len(stale) == 2

    def test_non_objective_skipped(self) -> None:
        store = ObjectiveStore()
        store.add(_make_version(version=1))
        cs = ConstraintSet()
        cs.add(_make_constraint(source="onboarding"))
        assert find_stale_constraints(cs, store) == []

    def test_empty_store(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(source="objective:sleep-goal:v1"))
        assert find_stale_constraints(cs, ObjectiveStore()) == []


# ===========================================================================
# invalidated_by
# ===========================================================================


class TestInvalidatedBy:
    def test_new_version_invalidates_old(self) -> None:
        v2 = _make_version(version=2)
        cs = ConstraintSet()
        cs.add(_make_constraint(id="c1", source="objective:sleep-goal:v1"))
        result = invalidated_by(v2, cs)
        assert len(result) == 1
        assert result[0].id == "c1"

    def test_no_matches(self) -> None:
        v2 = _make_version(version=2)
        cs = ConstraintSet()
        cs.add(_make_constraint(source="objective:sleep-goal:v2"))
        assert invalidated_by(v2, cs) == []

    def test_mixed(self) -> None:
        v3 = _make_version(version=3)
        cs = ConstraintSet()
        cs.add(_make_constraint(id="old", source="objective:sleep-goal:v1"))
        cs.add(_make_constraint(id="current", source="objective:sleep-goal:v3"))
        cs.add(_make_constraint(id="other", source="onboarding"))
        result = invalidated_by(v3, cs)
        assert len(result) == 1
        assert result[0].id == "old"


# ===========================================================================
# GovernanceGate — objective integration
# ===========================================================================


class TestGovernanceGateObjectiveIntegration:
    def test_no_objectives_backward_compat(self) -> None:
        """Gate without objectives still works (backward compatible)."""
        gate = GovernanceGate(ConstraintSet(), Ledger())
        result = gate.evaluate({"score": 80})
        assert result.is_allowed

    def test_stale_constraint_detected(self) -> None:
        """Constraint from v1, objective now at v2 → contradiction."""
        store = ObjectiveStore()
        store.add(_make_version(version=1, timestamp=_T0))
        store.add(_make_version(version=2, timestamp=_T0 + timedelta(days=7)))

        cs = ConstraintSet()
        cs.add(_make_constraint(source="objective:sleep-goal:v1"))

        ledger = Ledger()
        # Need at least one event for entity so detect_contradictions runs
        ledger.append(Event(
            id="e1",
            timestamp=_T0,
            entity_id="user-1",
            event_type="observed",
            action="check_in",
            actor="system",
        ))

        gate = GovernanceGate(cs, ledger, objectives=store)
        result = gate.evaluate({
            "entity_id": "user-1",
            "action": "suggest_routine",
            "proposed_hour": 21,
        })
        assert result.action == "require_reconciliation"
        assert "contradictions" in result.triggers

    def test_fresh_constraint_passes(self) -> None:
        """Constraint from current version → no contradiction."""
        store = ObjectiveStore()
        store.add(_make_version(version=1))

        cs = ConstraintSet()
        cs.add(_make_constraint(source="objective:sleep-goal:v1"))

        ledger = Ledger()
        ledger.append(Event(
            id="e1",
            timestamp=_T0,
            entity_id="user-1",
            event_type="observed",
            action="check_in",
            actor="system",
        ))

        gate = GovernanceGate(cs, ledger, objectives=store)
        result = gate.evaluate({
            "entity_id": "user-1",
            "action": "suggest_routine",
            "proposed_hour": 21,
        })
        assert result.is_allowed

    def test_multiple_objectives(self) -> None:
        """Multiple objectives, one stale → detected."""
        store = ObjectiveStore()
        store.add(_make_version(objective_id="sleep", version=1))
        store.add(_make_version(objective_id="sleep", version=2))
        store.add(_make_version(objective_id="exercise", version=1))

        cs = ConstraintSet()
        cs.add(_make_constraint(id="c-sleep", source="objective:sleep:v1"))
        cs.add(_make_constraint(id="c-exercise", source="objective:exercise:v1"))

        ledger = Ledger()
        ledger.append(Event(
            id="e1", timestamp=_T0, entity_id="user-1",
            event_type="observed", action="check_in", actor="system",
        ))

        gate = GovernanceGate(cs, ledger, objectives=store)
        contradictions = gate.detect_contradictions("user-1", "suggest_routine")
        objective_contras = [c for c in contradictions if c.type == "outdated_objective_version"]
        assert len(objective_contras) == 1
        assert "sleep" in objective_contras[0].message

    def test_full_pipeline(self) -> None:
        """Stale constraint + drift → strictest wins."""
        store = ObjectiveStore()
        store.add(_make_version(version=1, timestamp=_T0))
        store.add(_make_version(version=2, timestamp=_T0 + timedelta(days=7)))

        cs = ConstraintSet()
        cs.add(_make_constraint(source="objective:sleep-goal:v1"))

        ledger = Ledger()
        ledger.append(Event(
            id="e1", timestamp=_T0, entity_id="user-1",
            event_type="observed", action="check_in", actor="system",
        ))

        gate = GovernanceGate(cs, ledger, objectives=store)
        result = gate.evaluate(
            {"entity_id": "user-1", "action": "suggest_routine", "proposed_hour": 21},
            drift_data={"drift_percentage": 50.0, "severity": "significant"},
        )
        # Both contradiction (reconciliation) and drift (block) → block wins
        assert result.is_blocked


# ===========================================================================
# Real-world scenarios
# ===========================================================================


class TestRealWorldScenarios:
    def test_sleep_goal_evolves(self) -> None:
        """User starts with 'sleep by 10pm', refines to 'sleep by 11pm'."""
        store = ObjectiveStore()
        store.add(ObjectiveVersion(
            objective_id="sleep",
            version=1,
            timestamp=_T0,
            title="Sleep by 10pm",
            data={"bedtime_hour": 22},
            source="onboarding",
        ))
        store.add(ObjectiveVersion(
            objective_id="sleep",
            version=2,
            timestamp=_T0 + timedelta(days=14),
            title="Sleep by 11pm",
            data={"bedtime_hour": 23},
            source="user_feedback",
            reason="10pm was unrealistic on weekdays",
            parent_version=1,
        ))

        # Old constraint still says "lte 22"
        cs = ConstraintSet()
        cs.add(Constraint(
            id="bedtime",
            constraint_type="time_boundary",
            field="proposed_hour",
            operator="lte",
            value=22,
            description="Sleep by 10pm",
            source="objective:sleep:v1",
            priority=PRIORITY_HARD,
        ))

        stale = find_stale_constraints(cs, store)
        assert len(stale) == 1
        # The constraint should be reconciled with v2's data
        _, current = stale[0]
        assert current.data["bedtime_hour"] == 23

    def test_weight_goal_refined(self) -> None:
        """Weight goal goes from 'lose 5kg' to 'lose 3kg and build muscle'."""
        store = ObjectiveStore()
        store.add(ObjectiveVersion(
            objective_id="weight",
            version=1,
            timestamp=_T0,
            title="Lose 5kg",
            data={"target_loss_kg": 5},
            source="user_input",
        ))
        store.add(ObjectiveVersion(
            objective_id="weight",
            version=2,
            timestamp=_T0 + timedelta(days=30),
            title="Lose 3kg and build muscle",
            data={"target_loss_kg": 3, "muscle_gain": True},
            source="user_feedback",
            reason="Realized muscle matters more than weight number",
            parent_version=1,
        ))

        # Old constraint references v1
        cs = ConstraintSet()
        cs.add(Constraint(
            id="weight-check",
            constraint_type="value_alignment",
            field="weekly_weight_change",
            operator="lt",
            value=-0.5,
            description="Losing at least 0.5kg/week",
            source="objective:weight:v1",
            priority=PRIORITY_SOFT,
        ))

        invalidated = invalidated_by(store.current("weight"), cs)
        assert len(invalidated) == 1
        assert invalidated[0].id == "weight-check"

    def test_objective_drift_contradiction_combined(self) -> None:
        """All three governance sources fire at once."""
        store = ObjectiveStore()
        store.add(_make_version(version=1, timestamp=_T0))
        store.add(_make_version(version=2, timestamp=_T0 + timedelta(days=7)))

        cs = ConstraintSet()
        cs.add(_make_constraint(
            id="stale",
            source="objective:sleep-goal:v1",
            priority=PRIORITY_HARD,
        ))

        ledger = Ledger()
        ledger.append(Event(
            id="e1", timestamp=_T0, entity_id="user-1",
            event_type="rejected", action="suggest_routine", actor="user",
        ))

        gate = GovernanceGate(cs, ledger, objectives=store)
        result = gate.evaluate(
            {"entity_id": "user-1", "action": "suggest_routine", "proposed_hour": 21},
            drift_data={"drift_percentage": 50.0, "severity": "significant"},
        )
        # Three triggers: constraints (allow since 21<=22), drift (block), contradictions (reconciliation)
        assert result.is_blocked
        assert "drift" in result.triggers
        assert "contradictions" in result.triggers
