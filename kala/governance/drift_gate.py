"""Drift as governance gate — convert drift metrics into governance actions.

Input: output from ``kala.state.drift.compute_baseline_drift()``.
Output: a :class:`GateDecision` with action + reasons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kala.constraints.core import Violation

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

DEFAULT_DRIFT_THRESHOLDS: dict[str, float] = {
    "block_proactive": 40.0,
    "require_confirmation": 25.0,
}

# Action severity ordering (lower index = less restrictive)
_ACTION_SEVERITY = ["allow", "require_confirmation", "require_reconciliation", "block"]


# ---------------------------------------------------------------------------
# GateDecision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateDecision:
    """Result of a governance gate check.

    ``action`` is one of: ``allow``, ``block``, ``require_confirmation``,
    ``require_reconciliation``.
    """

    action: str
    reasons: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()
    drift_data: dict[str, Any] | None = field(default=None, repr=False)
    violations: tuple[Violation, ...] | None = None

    @property
    def is_blocked(self) -> bool:
        return self.action == "block"

    @property
    def is_allowed(self) -> bool:
        return self.action == "allow"

    @property
    def requires_confirmation(self) -> bool:
        return self.action in ("require_confirmation", "require_reconciliation")


def strictest_action(*actions: str) -> str:
    """Return the most restrictive action among the given actions."""
    max_idx = -1
    result = "allow"
    for action in actions:
        idx = _ACTION_SEVERITY.index(action) if action in _ACTION_SEVERITY else 0
        if idx > max_idx:
            max_idx = idx
            result = action
    return result


# ---------------------------------------------------------------------------
# Drift gate
# ---------------------------------------------------------------------------


def check_drift_gate(
    drift_data: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> GateDecision:
    """Convert drift metrics into a governance action.

    Args:
        drift_data: Output from ``kala.state.drift.compute_baseline_drift()``.
            Expected keys: ``drift_percentage``, ``severity``.
        thresholds: Override default thresholds. Keys:
            ``block_proactive``, ``require_confirmation``.

    Returns:
        :class:`GateDecision` with appropriate action.
    """
    t = thresholds or DEFAULT_DRIFT_THRESHOLDS
    pct = drift_data.get("drift_percentage", 0.0)
    severity = drift_data.get("severity", "minimal")

    if pct >= t.get("block_proactive", 40.0):
        return GateDecision(
            action="block",
            reasons=(f"Drift at {pct}% exceeds block threshold ({t.get('block_proactive', 40.0)}%)",),
            triggers=("drift",),
            drift_data=drift_data,
        )

    if severity == "significant":
        return GateDecision(
            action="require_reconciliation",
            reasons=(f"Drift severity is significant ({pct}%)",),
            triggers=("drift",),
            drift_data=drift_data,
        )

    if pct >= t.get("require_confirmation", 25.0):
        return GateDecision(
            action="require_confirmation",
            reasons=(f"Drift at {pct}% exceeds confirmation threshold ({t.get('require_confirmation', 25.0)}%)",),
            triggers=("drift",),
            drift_data=drift_data,
        )

    return GateDecision(
        action="allow",
        drift_data=drift_data,
    )
