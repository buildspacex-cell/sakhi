"""Deterministic constraint evaluation engine.

Given an action context (dict) and a set of constraints, produces a
:class:`~kala.constraints.core.Verdict` — allow, block, or confirm.
"""

from __future__ import annotations

from typing import Any

from kala.constraints.core import (
    PRIORITY_HARD,
    Constraint,
    ConstraintSet,
    Verdict,
    Violation,
)
from kala.constraints.operators import check, extract_field, is_missing


def evaluate_single(action_context: dict[str, Any], constraint: Constraint) -> Violation | None:
    """Evaluate one constraint against the action context.

    Returns a :class:`Violation` if the constraint is not satisfied, or
    ``None`` if the constraint passes (or is inactive / field missing for
    soft constraints).

    Missing-field behaviour:
    - **Hard** constraint with missing field → Violation (field required)
    - **Soft/medium** constraint with missing field → ``None`` (skip)
    """
    if not constraint.active:
        return None

    actual = extract_field(action_context, constraint.field)

    if is_missing(actual):
        if constraint.priority >= PRIORITY_HARD:
            return Violation(
                constraint=constraint,
                actual_value=None,
                message=f"Required field '{constraint.field}' is missing",
            )
        return None

    if not check(constraint.operator, actual, constraint.value):
        return Violation(
            constraint=constraint,
            actual_value=actual,
            message=(
                f"{constraint.description}: "
                f"expected {constraint.field} {constraint.operator} {constraint.value!r}, "
                f"got {actual!r}"
            ),
        )

    return None


def evaluate(
    action_context: dict[str, Any],
    constraints: ConstraintSet | list[Constraint],
) -> Verdict:
    """Evaluate all active constraints against the action context.

    Priority logic:
    - Any **hard** violation → ``block``
    - Any **soft/medium** violation (no hard) → ``confirm``
    - No violations → ``allow``
    """
    items: list[Constraint]
    if isinstance(constraints, ConstraintSet):
        items = constraints.active()
    else:
        items = [c for c in constraints if c.active]

    violations: list[Violation] = []
    for constraint in items:
        violation = evaluate_single(action_context, constraint)
        if violation is not None:
            violations.append(violation)

    if not violations:
        return Verdict.allow()

    has_hard = any(v.constraint.priority >= PRIORITY_HARD for v in violations)
    if has_hard:
        return Verdict.block(violations)

    return Verdict.confirm(violations)
