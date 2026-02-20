"""Governance gate — unified checkpoint for constraints, drift, and contradictions."""

from kala.governance.drift_gate import (
    DEFAULT_DRIFT_THRESHOLDS,
    GateDecision,
    check_drift_gate,
)
from kala.governance.gate import (
    CONTRADICTION_TYPES,
    Contradiction,
    GovernanceGate,
)
from kala.governance.state import StateSnapshot, diff, reduce
from kala.governance.temporal import TemporalContext
from kala.objectives.core import ObjectiveStore, ObjectiveVersion

__all__ = [
    "CONTRADICTION_TYPES",
    "Contradiction",
    "DEFAULT_DRIFT_THRESHOLDS",
    "GateDecision",
    "GovernanceGate",
    "ObjectiveStore",
    "ObjectiveVersion",
    "StateSnapshot",
    "TemporalContext",
    "check_drift_gate",
    "diff",
    "reduce",
]
