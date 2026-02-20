"""Tests for kala.governance — drift gate, governance gate, contradictions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kala.constraints.core import (
    PRIORITY_HARD,
    PRIORITY_SOFT,
    Constraint,
    ConstraintSet,
)
from kala.governance.drift_gate import (
    DEFAULT_DRIFT_THRESHOLDS,
    GateDecision,
    check_drift_gate,
    strictest_action,
)
from kala.governance.gate import (
    CONTRADICTION_TYPES,
    Contradiction,
    GovernanceGate,
)
from kala.ledger.core import Event, Ledger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)


def _make_event(
    *,
    id: str = "evt-1",
    timestamp: datetime = _T0,
    entity_id: str = "user-1",
    event_type: str = "proposed",
    action: str = "suggest_routine",
    actor: str = "llm",
    data: dict | None = None,
    reason: str = "",
) -> Event:
    return Event(
        id=id,
        timestamp=timestamp,
        entity_id=entity_id,
        event_type=event_type,
        action=action,
        actor=actor,
        data=data or {},
        reason=reason,
    )


def _make_constraint(
    *,
    id: str = "c1",
    field: str = "score",
    operator: str = "gt",
    value: object = 50,
    priority: int = PRIORITY_SOFT,
) -> Constraint:
    return Constraint(
        id=id,
        constraint_type="custom",
        field=field,
        operator=operator,
        value=value,
        description="test",
        source="test",
        priority=priority,
    )


# ===========================================================================
# GateDecision
# ===========================================================================


class TestGateDecision:
    def test_allow_properties(self) -> None:
        gd = GateDecision(action="allow")
        assert gd.is_allowed
        assert not gd.is_blocked
        assert not gd.requires_confirmation

    def test_block_properties(self) -> None:
        gd = GateDecision(action="block")
        assert gd.is_blocked
        assert not gd.is_allowed
        assert not gd.requires_confirmation

    def test_confirmation_properties(self) -> None:
        gd = GateDecision(action="require_confirmation")
        assert gd.requires_confirmation
        assert not gd.is_blocked

    def test_reconciliation_properties(self) -> None:
        gd = GateDecision(action="require_reconciliation")
        assert gd.requires_confirmation
        assert not gd.is_allowed

    def test_frozen(self) -> None:
        gd = GateDecision(action="allow")
        with pytest.raises(AttributeError):
            gd.action = "block"  # type: ignore[misc]


# ===========================================================================
# strictest_action
# ===========================================================================


class TestStrictestAction:
    def test_allow_vs_block(self) -> None:
        assert strictest_action("allow", "block") == "block"

    def test_confirm_vs_reconcile(self) -> None:
        assert strictest_action("require_confirmation", "require_reconciliation") == "require_reconciliation"

    def test_single(self) -> None:
        assert strictest_action("allow") == "allow"

    def test_all_actions(self) -> None:
        assert strictest_action("allow", "require_confirmation", "require_reconciliation", "block") == "block"


# ===========================================================================
# check_drift_gate
# ===========================================================================


class TestCheckDriftGate:
    def test_low_drift_allows(self) -> None:
        result = check_drift_gate({"drift_percentage": 10.0, "severity": "minimal"})
        assert result.is_allowed

    def test_moderate_drift_confirms(self) -> None:
        result = check_drift_gate({"drift_percentage": 30.0, "severity": "moderate"})
        assert result.action == "require_confirmation"

    def test_high_drift_blocks(self) -> None:
        result = check_drift_gate({"drift_percentage": 45.0, "severity": "significant"})
        assert result.is_blocked

    def test_significant_severity_reconciles(self) -> None:
        # 35% drift + significant severity → reconciliation (severity check runs before confirmation)
        result = check_drift_gate({"drift_percentage": 35.0, "severity": "significant"})
        assert result.action == "require_reconciliation"

    def test_custom_thresholds(self) -> None:
        custom = {"block_proactive": 80.0, "require_confirmation": 50.0}
        result = check_drift_gate({"drift_percentage": 45.0, "severity": "moderate"}, thresholds=custom)
        assert result.is_allowed

    def test_exactly_at_threshold(self) -> None:
        result = check_drift_gate({"drift_percentage": 25.0, "severity": "moderate"})
        assert result.action == "require_confirmation"

    def test_drift_data_attached(self) -> None:
        data = {"drift_percentage": 10.0, "severity": "minimal"}
        result = check_drift_gate(data)
        assert result.drift_data == data

    def test_zero_drift(self) -> None:
        result = check_drift_gate({"drift_percentage": 0.0, "severity": "minimal"})
        assert result.is_allowed

    def test_default_thresholds_values(self) -> None:
        assert DEFAULT_DRIFT_THRESHOLDS["block_proactive"] == 40.0
        assert DEFAULT_DRIFT_THRESHOLDS["require_confirmation"] == 25.0


# ===========================================================================
# Contradiction
# ===========================================================================


class TestContradiction:
    def test_creation(self) -> None:
        e = _make_event()
        c = Contradiction(type="previously_rejected", event=e, message="test")
        assert c.type == "previously_rejected"
        assert c.event is e

    def test_frozen(self) -> None:
        e = _make_event()
        c = Contradiction(type="previously_rejected", event=e, message="test")
        with pytest.raises(AttributeError):
            c.type = "changed"  # type: ignore[misc]

    def test_valid_types(self) -> None:
        expected = {
            "previously_rejected",
            "contradicts_commitment",
            "outdated_objective_version",
            "violates_recent_override",
            "repetition_loop",
        }
        assert CONTRADICTION_TYPES == expected


# ===========================================================================
# GovernanceGate.evaluate
# ===========================================================================


class TestGovernanceGateEvaluate:
    def test_all_clear(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(field="score", operator="gt", value=50))
        ledger = Ledger()
        gate = GovernanceGate(cs, ledger)
        result = gate.evaluate({"score": 80})
        assert result.is_allowed

    def test_constraint_blocks(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(field="score", operator="gt", value=50, priority=PRIORITY_HARD))
        ledger = Ledger()
        gate = GovernanceGate(cs, ledger)
        result = gate.evaluate({"score": 30})
        assert result.is_blocked
        assert "constraints" in result.triggers

    def test_drift_blocks(self) -> None:
        cs = ConstraintSet()
        ledger = Ledger()
        gate = GovernanceGate(cs, ledger)
        result = gate.evaluate({}, drift_data={"drift_percentage": 50.0, "severity": "significant"})
        assert result.is_blocked
        assert "drift" in result.triggers

    def test_constraint_confirms(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(field="score", operator="gt", value=50, priority=PRIORITY_SOFT))
        ledger = Ledger()
        gate = GovernanceGate(cs, ledger)
        result = gate.evaluate({"score": 30})
        assert result.action == "require_confirmation"

    def test_combined_strictest_wins(self) -> None:
        """Soft constraint (confirm) + high drift (block) → block."""
        cs = ConstraintSet()
        cs.add(_make_constraint(field="score", operator="gt", value=50, priority=PRIORITY_SOFT))
        ledger = Ledger()
        gate = GovernanceGate(cs, ledger)
        result = gate.evaluate(
            {"score": 30},
            drift_data={"drift_percentage": 50.0, "severity": "significant"},
        )
        assert result.is_blocked

    def test_contradiction_triggers_reconciliation(self) -> None:
        cs = ConstraintSet()
        ledger = Ledger()
        ledger.append(_make_event(
            id="e1",
            entity_id="user-1",
            event_type="rejected",
            action="suggest_routine",
            timestamp=_T0,
        ))
        gate = GovernanceGate(cs, ledger)
        result = gate.evaluate({
            "entity_id": "user-1",
            "action": "suggest_routine",
        })
        assert result.action == "require_reconciliation"
        assert "contradictions" in result.triggers

    def test_empty_constraints_allows(self) -> None:
        gate = GovernanceGate(ConstraintSet(), Ledger())
        result = gate.evaluate({"score": 80})
        assert result.is_allowed

    def test_violations_attached(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(field="score", operator="gt", value=50, priority=PRIORITY_HARD))
        gate = GovernanceGate(cs, Ledger())
        result = gate.evaluate({"score": 30})
        assert result.violations is not None
        assert len(result.violations) == 1


# ===========================================================================
# GovernanceGate.detect_contradictions
# ===========================================================================


class TestDetectContradictions:
    def test_empty_ledger(self) -> None:
        gate = GovernanceGate(ConstraintSet(), Ledger())
        result = gate.detect_contradictions("user-1", "suggest_routine")
        assert result == []

    def test_previously_rejected(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(
            id="e1",
            entity_id="user-1",
            event_type="rejected",
            action="suggest_routine",
            timestamp=_T0,
        ))
        gate = GovernanceGate(ConstraintSet(), ledger)
        result = gate.detect_contradictions("user-1", "suggest_routine")
        assert len(result) >= 1
        assert any(c.type == "previously_rejected" for c in result)

    def test_contradicts_commitment(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(
            id="e1",
            entity_id="user-1",
            event_type="committed",
            action="suggest_routine",
            timestamp=_T0,
        ))
        gate = GovernanceGate(ConstraintSet(), ledger)
        result = gate.detect_contradictions("user-1", "suggest_routine")
        assert any(c.type == "contradicts_commitment" for c in result)

    def test_repetition_loop(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(
            id="e1",
            entity_id="user-1",
            event_type="proposed",
            action="suggest_routine",
            timestamp=_T0,
        ))
        ledger.append(_make_event(
            id="e2",
            entity_id="user-1",
            event_type="rejected",
            action="suggest_routine",
            timestamp=_T0 + timedelta(minutes=5),
        ))
        gate = GovernanceGate(ConstraintSet(), ledger)
        result = gate.detect_contradictions("user-1", "suggest_routine")
        assert any(c.type == "repetition_loop" for c in result)

    def test_old_events_ignored(self) -> None:
        ledger = Ledger()
        # Event 48 hours ago — outside default 24h window
        old_ts = _T0 - timedelta(hours=48)
        ledger.append(_make_event(
            id="e-old",
            entity_id="user-1",
            event_type="rejected",
            action="suggest_routine",
            timestamp=old_ts,
        ))
        # Need a recent event so latest_ts is recent
        ledger.append(_make_event(
            id="e-recent",
            entity_id="user-1",
            event_type="observed",
            action="check_in",
            timestamp=_T0,
        ))
        gate = GovernanceGate(ConstraintSet(), ledger)
        result = gate.detect_contradictions("user-1", "suggest_routine")
        # The old rejection should be outside the window
        assert not any(c.type == "previously_rejected" for c in result)


# ===========================================================================
# Real-world scenarios
# ===========================================================================


class TestRealWorldScenarios:
    def test_chaos_friction_plus_sleep_boundary(self) -> None:
        """High drift (chaos friction) + hard sleep boundary → block."""
        cs = ConstraintSet()
        cs.add(Constraint(
            id="sleep",
            constraint_type="time_boundary",
            field="proposed_hour",
            operator="lte",
            value=22,
            description="Sleep by 10pm",
            source="onboarding",
            priority=PRIORITY_HARD,
        ))
        gate = GovernanceGate(cs, Ledger())
        result = gate.evaluate(
            {"proposed_hour": 23},
            drift_data={"drift_percentage": 45.0, "severity": "significant"},
        )
        assert result.is_blocked
        assert "constraints" in result.triggers
        assert "drift" in result.triggers

    def test_low_drift_aligned_action(self) -> None:
        """Low drift + all constraints satisfied → allow."""
        cs = ConstraintSet()
        cs.add(Constraint(
            id="capacity",
            constraint_type="capacity",
            field="active_tasks",
            operator="lt",
            value=5,
            description="Under task capacity",
            source="system",
            priority=PRIORITY_SOFT,
        ))
        gate = GovernanceGate(cs, Ledger())
        result = gate.evaluate(
            {"active_tasks": 2},
            drift_data={"drift_percentage": 5.0, "severity": "minimal"},
        )
        assert result.is_allowed

    def test_commitment_contradiction(self) -> None:
        """User committed to an action, then it's proposed again → reconciliation."""
        ledger = Ledger()
        ledger.append(_make_event(
            id="commit-1",
            entity_id="user-1",
            event_type="committed",
            action="morning_meditation",
            timestamp=_T0,
        ))
        gate = GovernanceGate(ConstraintSet(), ledger)
        result = gate.evaluate({
            "entity_id": "user-1",
            "action": "morning_meditation",
        })
        assert result.action == "require_reconciliation"
