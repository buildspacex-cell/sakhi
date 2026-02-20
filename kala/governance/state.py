"""Replayable state reconstruction from events.

Given a sequence of events (or a Ledger), :func:`reduce` replays them
chronologically to reconstruct a deterministic :class:`StateSnapshot`.
This is pure, stateless, and replayable — the same events always produce
the same snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from kala.ledger.core import Event, Ledger

# ---------------------------------------------------------------------------
# StateSnapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateSnapshot:
    """Deterministic state reconstructed from events.

    Represents the "current known state" of an entity at a point in time.
    Can be reconstructed by replaying events through :func:`reduce`.
    """

    entity_id: str
    as_of: datetime
    active_constraints: tuple[str, ...] = ()
    active_commitments: tuple[str, ...] = ()
    last_drift_severity: str = "minimal"
    pending_actions: tuple[str, ...] = ()
    rejected_actions: tuple[str, ...] = ()
    version: int = 0


# ---------------------------------------------------------------------------
# Reducer
# ---------------------------------------------------------------------------

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def reduce(events: list[Event] | Ledger, entity_id: str) -> StateSnapshot:
    """Replay events to reconstruct deterministic state.

    Processes events chronologically:

    - ``"committed"`` → adds to active_commitments
    - ``"rejected"`` → adds to rejected_actions, removes from pending
    - ``"proposed"`` → adds to pending_actions
    - ``"reconciled"`` → clears pending_actions and rejected_actions
    - ``"observed"`` with drift data → updates last_drift_severity

    This is pure, deterministic, replayable.
    """
    if isinstance(events, Ledger):
        event_list = events.query(entity_id=entity_id)
    else:
        event_list = [e for e in events if e.entity_id == entity_id]

    # Sort chronologically for deterministic replay
    event_list = sorted(event_list, key=lambda e: e.timestamp)

    commitments: list[str] = []
    pending: list[str] = []
    rejected: list[str] = []
    constraints: list[str] = []
    drift_severity = "minimal"
    version = 0
    as_of = _EPOCH

    for event in event_list:
        version += 1
        as_of = event.timestamp

        if event.event_type == "committed":
            if event.action not in commitments:
                commitments.append(event.action)
            # Remove from pending if it was there
            if event.action in pending:
                pending.remove(event.action)

        elif event.event_type == "rejected":
            if event.action not in rejected:
                rejected.append(event.action)
            if event.action in pending:
                pending.remove(event.action)

        elif event.event_type == "proposed":
            if event.action not in pending:
                pending.append(event.action)

        elif event.event_type == "reconciled":
            pending.clear()
            rejected.clear()

        elif event.event_type == "observed":
            severity = event.data.get("drift_severity") or event.data.get("severity")
            if severity:
                drift_severity = severity

        # Handle constraint activation/deactivation in data
        constraint_id = event.data.get("constraint_id")
        if constraint_id:
            if event.event_type == "committed" and constraint_id not in constraints:
                constraints.append(constraint_id)
            elif event.event_type == "rejected" and constraint_id in constraints:
                constraints.remove(constraint_id)

    return StateSnapshot(
        entity_id=entity_id,
        as_of=as_of,
        active_constraints=tuple(constraints),
        active_commitments=tuple(commitments),
        last_drift_severity=drift_severity,
        pending_actions=tuple(pending),
        rejected_actions=tuple(rejected),
        version=version,
    )


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def diff(before: StateSnapshot, after: StateSnapshot) -> dict[str, Any]:
    """Compute the difference between two state snapshots.

    Returns a dict with ``added`` and ``removed`` for each tuple field,
    plus scalar field changes.
    """
    changes: dict[str, Any] = {}

    # Tuple fields — set diff
    for field_name in (
        "active_constraints",
        "active_commitments",
        "pending_actions",
        "rejected_actions",
    ):
        before_set = set(getattr(before, field_name))
        after_set = set(getattr(after, field_name))
        added = after_set - before_set
        removed = before_set - after_set
        if added or removed:
            changes[field_name] = {}
            if added:
                changes[field_name]["added"] = sorted(added)
            if removed:
                changes[field_name]["removed"] = sorted(removed)

    # Scalar fields
    if before.last_drift_severity != after.last_drift_severity:
        changes["last_drift_severity"] = {
            "before": before.last_drift_severity,
            "after": after.last_drift_severity,
        }

    if before.version != after.version:
        changes["version"] = {
            "before": before.version,
            "after": after.version,
        }

    return changes
