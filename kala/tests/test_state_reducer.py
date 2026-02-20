"""Tests for kala.governance.state — replayable state reconstruction."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kala.governance.state import StateSnapshot, diff, reduce
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


# ===========================================================================
# StateSnapshot
# ===========================================================================


class TestStateSnapshot:
    def test_creation(self) -> None:
        s = StateSnapshot(entity_id="user-1", as_of=_T0)
        assert s.entity_id == "user-1"
        assert s.version == 0

    def test_frozen(self) -> None:
        s = StateSnapshot(entity_id="user-1", as_of=_T0)
        with pytest.raises(AttributeError):
            s.version = 5  # type: ignore[misc]

    def test_defaults(self) -> None:
        s = StateSnapshot(entity_id="user-1", as_of=_T0)
        assert s.active_constraints == ()
        assert s.active_commitments == ()
        assert s.last_drift_severity == "minimal"
        assert s.pending_actions == ()
        assert s.rejected_actions == ()


# ===========================================================================
# reduce
# ===========================================================================


class TestReduce:
    def test_empty_events(self) -> None:
        s = reduce([], "user-1")
        assert s.version == 0
        assert s.active_commitments == ()

    def test_single_commit(self) -> None:
        events = [_make_event(event_type="committed", action="morning_meditation")]
        s = reduce(events, "user-1")
        assert "morning_meditation" in s.active_commitments
        assert s.version == 1

    def test_single_reject(self) -> None:
        events = [_make_event(event_type="rejected", action="late_night_snack")]
        s = reduce(events, "user-1")
        assert "late_night_snack" in s.rejected_actions
        assert s.version == 1

    def test_proposed_then_committed(self) -> None:
        events = [
            _make_event(id="e1", event_type="proposed", action="exercise", timestamp=_T0),
            _make_event(id="e2", event_type="committed", action="exercise", timestamp=_T0 + timedelta(minutes=5)),
        ]
        s = reduce(events, "user-1")
        assert "exercise" in s.active_commitments
        assert "exercise" not in s.pending_actions
        assert s.version == 2

    def test_proposed_then_rejected(self) -> None:
        events = [
            _make_event(id="e1", event_type="proposed", action="skip_meal", timestamp=_T0),
            _make_event(id="e2", event_type="rejected", action="skip_meal", timestamp=_T0 + timedelta(minutes=5)),
        ]
        s = reduce(events, "user-1")
        assert "skip_meal" in s.rejected_actions
        assert "skip_meal" not in s.pending_actions
        assert s.version == 2

    def test_version_increments(self) -> None:
        events = [
            _make_event(id=f"e{i}", timestamp=_T0 + timedelta(minutes=i))
            for i in range(5)
        ]
        s = reduce(events, "user-1")
        assert s.version == 5

    def test_reconciled_clears(self) -> None:
        events = [
            _make_event(id="e1", event_type="proposed", action="x", timestamp=_T0),
            _make_event(id="e2", event_type="rejected", action="y", timestamp=_T0 + timedelta(minutes=1)),
            _make_event(id="e3", event_type="reconciled", action="reconcile", timestamp=_T0 + timedelta(minutes=2)),
        ]
        s = reduce(events, "user-1")
        assert s.pending_actions == ()
        assert s.rejected_actions == ()

    def test_observed_updates_drift(self) -> None:
        events = [
            _make_event(
                id="e1",
                event_type="observed",
                action="drift_check",
                data={"drift_severity": "moderate"},
            ),
        ]
        s = reduce(events, "user-1")
        assert s.last_drift_severity == "moderate"

    def test_observed_with_severity_key(self) -> None:
        """Also supports 'severity' key (from compute_baseline_drift output)."""
        events = [
            _make_event(
                id="e1",
                event_type="observed",
                action="drift_check",
                data={"severity": "significant"},
            ),
        ]
        s = reduce(events, "user-1")
        assert s.last_drift_severity == "significant"


# ===========================================================================
# Replayable determinism
# ===========================================================================


class TestReduceReplayable:
    def test_same_events_same_snapshot(self) -> None:
        events = [
            _make_event(id="e1", event_type="proposed", action="a", timestamp=_T0),
            _make_event(id="e2", event_type="committed", action="a", timestamp=_T0 + timedelta(minutes=1)),
        ]
        s1 = reduce(events, "user-1")
        s2 = reduce(events, "user-1")
        assert s1 == s2

    def test_order_matters(self) -> None:
        events_a = [
            _make_event(id="e1", event_type="proposed", action="x", timestamp=_T0),
            _make_event(id="e2", event_type="committed", action="x", timestamp=_T0 + timedelta(minutes=1)),
        ]
        events_b = [
            _make_event(id="e1", event_type="proposed", action="x", timestamp=_T0),
            _make_event(id="e2", event_type="rejected", action="x", timestamp=_T0 + timedelta(minutes=1)),
        ]
        s_a = reduce(events_a, "user-1")
        s_b = reduce(events_b, "user-1")
        assert s_a != s_b

    def test_subset_replay(self) -> None:
        """Replaying a prefix of events gives an earlier state."""
        events = [
            _make_event(id="e1", event_type="proposed", action="a", timestamp=_T0),
            _make_event(id="e2", event_type="committed", action="a", timestamp=_T0 + timedelta(minutes=1)),
            _make_event(id="e3", event_type="proposed", action="b", timestamp=_T0 + timedelta(minutes=2)),
        ]
        s_full = reduce(events, "user-1")
        s_partial = reduce(events[:2], "user-1")
        assert s_full.version == 3
        assert s_partial.version == 2
        assert "b" not in s_partial.pending_actions

    def test_from_ledger(self) -> None:
        """reduce() can accept a Ledger directly."""
        ledger = Ledger()
        ledger.append(_make_event(id="e1", event_type="committed", action="walk"))
        ledger.append(_make_event(id="e2", entity_id="other-user", event_type="committed", action="run"))
        s = reduce(ledger, "user-1")
        assert s.active_commitments == ("walk",)
        assert s.version == 1


# ===========================================================================
# diff
# ===========================================================================


class TestDiff:
    def test_no_change(self) -> None:
        s = StateSnapshot(entity_id="user-1", as_of=_T0, version=1)
        d = diff(s, s)
        assert d == {}

    def test_added_commitment(self) -> None:
        before = StateSnapshot(entity_id="user-1", as_of=_T0, version=1)
        after = StateSnapshot(
            entity_id="user-1",
            as_of=_T0 + timedelta(hours=1),
            active_commitments=("morning_walk",),
            version=2,
        )
        d = diff(before, after)
        assert "active_commitments" in d
        assert "morning_walk" in d["active_commitments"]["added"]

    def test_removed_commitment(self) -> None:
        before = StateSnapshot(
            entity_id="user-1",
            as_of=_T0,
            active_commitments=("morning_walk",),
            version=1,
        )
        after = StateSnapshot(entity_id="user-1", as_of=_T0 + timedelta(hours=1), version=2)
        d = diff(before, after)
        assert "active_commitments" in d
        assert "morning_walk" in d["active_commitments"]["removed"]

    def test_multiple_changes(self) -> None:
        before = StateSnapshot(
            entity_id="user-1",
            as_of=_T0,
            active_commitments=("walk",),
            last_drift_severity="minimal",
            version=1,
        )
        after = StateSnapshot(
            entity_id="user-1",
            as_of=_T0 + timedelta(hours=1),
            active_commitments=("walk", "meditate"),
            last_drift_severity="moderate",
            version=3,
        )
        d = diff(before, after)
        assert "active_commitments" in d
        assert "meditate" in d["active_commitments"]["added"]
        assert d["last_drift_severity"]["before"] == "minimal"
        assert d["last_drift_severity"]["after"] == "moderate"
        assert d["version"]["before"] == 1
        assert d["version"]["after"] == 3
