"""Unified governance checkpoint — constraints + drift + contradiction detection.

The :class:`GovernanceGate` is the single entry-point for all governance
checks.  It merges constraint evaluation, drift gating, and ledger-based
contradiction detection into one :class:`GateDecision`.  **Strictest wins.**
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from kala.constraints.core import ConstraintSet, Violation
from kala.constraints.evaluator import evaluate
from kala.governance.drift_gate import GateDecision, check_drift_gate, strictest_action
from kala.ledger.core import Event, Ledger
from kala.objectives.core import ObjectiveStore
from kala.objectives.staleness import find_stale_constraints, parse_objective_source

# ---------------------------------------------------------------------------
# Typed contradiction taxonomy
# ---------------------------------------------------------------------------

CONTRADICTION_TYPES: frozenset[str] = frozenset({
    "previously_rejected",
    "contradicts_commitment",
    "outdated_objective_version",
    "violates_recent_override",
    "repetition_loop",
})


@dataclass(frozen=True)
class Contradiction:
    """A typed contradiction detected against the event ledger."""

    type: str
    event: Event
    message: str


# ---------------------------------------------------------------------------
# Default contradiction window
# ---------------------------------------------------------------------------

_DEFAULT_WINDOW = timedelta(hours=24)


# ---------------------------------------------------------------------------
# GovernanceGate
# ---------------------------------------------------------------------------


class GovernanceGate:
    """Combined gate: constraints + drift + ledger audit.

    The single governance checkpoint.  Strictest action wins::

        block > require_reconciliation > require_confirmation > allow
    """

    def __init__(
        self,
        constraints: ConstraintSet,
        ledger: Ledger,
        objectives: ObjectiveStore | None = None,
    ) -> None:
        self._constraints = constraints
        self._ledger = ledger
        self._objectives = objectives

    def evaluate(
        self,
        action_context: dict[str, Any],
        drift_data: dict[str, Any] | None = None,
    ) -> GateDecision:
        """Full governance check.

        1. Evaluate constraints against *action_context*.
        2. If *drift_data* provided, run drift gate.
        3. Check ledger for contradictions.
        4. Merge into single :class:`GateDecision` (strictest wins).
        """
        all_reasons: list[str] = []
        all_triggers: list[str] = []
        all_violations: list[Violation] = []
        actions: list[str] = []

        # --- 1. Constraint evaluation ---
        verdict = evaluate(action_context, self._constraints)
        if verdict.action != "allow":
            actions.append("block" if verdict.action == "block" else "require_confirmation")
            all_violations.extend(verdict.violations)
            all_reasons.extend(v.message for v in verdict.violations)
            all_triggers.append("constraints")

        # --- 2. Drift gate ---
        if drift_data is not None:
            drift_decision = check_drift_gate(drift_data)
            if drift_decision.action != "allow":
                actions.append(drift_decision.action)
                all_reasons.extend(drift_decision.reasons)
                all_triggers.append("drift")

        # --- 3. Contradiction detection ---
        entity_id = action_context.get("entity_id", "")
        proposed_action = action_context.get("action", "")
        if entity_id and proposed_action:
            contradictions = self.detect_contradictions(entity_id, proposed_action)
            if contradictions:
                actions.append("require_reconciliation")
                all_reasons.extend(c.message for c in contradictions)
                all_triggers.append("contradictions")

        # --- Merge: strictest wins ---
        if not actions:
            return GateDecision(
                action="allow",
                drift_data=drift_data,
            )

        final_action = strictest_action(*actions)
        return GateDecision(
            action=final_action,
            reasons=tuple(all_reasons),
            triggers=tuple(all_triggers),
            drift_data=drift_data,
            violations=tuple(all_violations) if all_violations else None,
        )

    def detect_contradictions(
        self,
        entity_id: str,
        proposed_action: str,
        window: timedelta | None = None,
    ) -> list[Contradiction]:
        """Typed contradiction detection against the ledger.

        Checks for:
        - ``previously_rejected``: same action rejected within window.
        - ``contradicts_commitment``: committed event conflicts with proposed.
        - ``repetition_loop``: proposed → rejected → proposed cycle.
        - ``outdated_objective_version``: constraint references stale objective.
        """
        w = window or _DEFAULT_WINDOW
        contradictions: list[Contradiction] = []

        # Get all events for this entity
        entity_events = self._ledger.query(entity_id=entity_id)
        if not entity_events:
            return contradictions

        # Determine time boundary
        latest_ts = entity_events[-1].timestamp
        cutoff = latest_ts - w

        recent = [e for e in entity_events if e.timestamp >= cutoff]

        # --- previously_rejected ---
        rejected = [e for e in recent if e.event_type == "rejected" and e.action == proposed_action]
        for ev in rejected:
            contradictions.append(Contradiction(
                type="previously_rejected",
                event=ev,
                message=f"Action '{proposed_action}' was rejected at {ev.timestamp.isoformat()}",
            ))

        # --- contradicts_commitment ---
        committed = [e for e in recent if e.event_type == "committed" and e.action == proposed_action]
        for ev in committed:
            contradictions.append(Contradiction(
                type="contradicts_commitment",
                event=ev,
                message=f"Action '{proposed_action}' contradicts commitment at {ev.timestamp.isoformat()}",
            ))

        # --- repetition_loop ---
        # Detect: proposed → rejected → proposed (same action) cycle
        action_events = [e for e in recent if e.action == proposed_action]
        if len(action_events) >= 2:
            types_seq = [e.event_type for e in action_events]
            for i in range(len(types_seq) - 1):
                if types_seq[i] == "proposed" and types_seq[i + 1] == "rejected":
                    contradictions.append(Contradiction(
                        type="repetition_loop",
                        event=action_events[i + 1],
                        message=f"Action '{proposed_action}' is in a propose→reject loop",
                    ))
                    break  # One repetition_loop is enough

        # --- outdated_objective_version ---
        if self._objectives is not None:
            stale = find_stale_constraints(self._constraints, self._objectives)
            for constraint, current_ver in stale:
                parsed = parse_objective_source(constraint.source)
                if parsed is None:
                    continue  # pragma: no cover
                _, ref_ver = parsed
                contradictions.append(Contradiction(
                    type="outdated_objective_version",
                    event=Event(
                        id=f"objective-{current_ver.objective_id}-v{current_ver.version}",
                        timestamp=current_ver.timestamp,
                        entity_id=entity_id,
                        event_type="observed",
                        action="objective_updated",
                        actor="system",
                        data={
                            "objective_id": current_ver.objective_id,
                            "version": current_ver.version,
                        },
                    ),
                    message=(
                        f"Constraint '{constraint.id}' references "
                        f"objective '{current_ver.objective_id}' v{ref_ver}, "
                        f"but current is v{current_ver.version}"
                    ),
                ))

        return contradictions
