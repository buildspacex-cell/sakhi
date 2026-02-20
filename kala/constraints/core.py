"""Constraint data types — Constraint, Violation, Verdict, ConstraintSet."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Priority levels
# ---------------------------------------------------------------------------

PRIORITY_SOFT = 1
PRIORITY_MEDIUM = 2
PRIORITY_HARD = 3

# ---------------------------------------------------------------------------
# Valid constraint types
# ---------------------------------------------------------------------------

VALID_CONSTRAINT_TYPES: frozenset[str] = frozenset({
    "time_boundary",
    "value_alignment",
    "drift_threshold",
    "commitment",
    "capacity",
    "custom",
})


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Constraint:
    """A single, serializable constraint.

    Constraints are *data*, not code.  The evaluator applies them
    deterministically against an action context.
    """

    id: str
    constraint_type: str
    field: str
    operator: str
    value: Any
    description: str
    source: str
    priority: int = PRIORITY_SOFT
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Violation:
    """A constraint that was not satisfied."""

    constraint: Constraint
    actual_value: Any
    message: str


@dataclass(frozen=True)
class Verdict:
    """Result of evaluating constraints against an action context.

    ``action`` is one of ``"allow"``, ``"block"``, or ``"confirm"``.
    """

    action: str
    violations: tuple[Violation, ...] = ()

    @staticmethod
    def allow() -> Verdict:
        """No violations — action may proceed."""
        return Verdict(action="allow")

    @staticmethod
    def block(violations: list[Violation]) -> Verdict:
        """Hard violations — action must not proceed."""
        return Verdict(action="block", violations=tuple(violations))

    @staticmethod
    def confirm(violations: list[Violation]) -> Verdict:
        """Soft violations — action needs user confirmation."""
        return Verdict(action="confirm", violations=tuple(violations))


# ---------------------------------------------------------------------------
# ConstraintSet — mutable collection
# ---------------------------------------------------------------------------


class ConstraintSet:
    """Mutable collection of constraints for an entity."""

    def __init__(self) -> None:
        self._constraints: dict[str, Constraint] = {}

    # -- mutators ----------------------------------------------------------

    def add(self, constraint: Constraint) -> None:
        """Add or replace a constraint by id."""
        self._constraints[constraint.id] = constraint

    def remove(self, constraint_id: str) -> bool:
        """Remove a constraint by id. Returns ``True`` if found."""
        return self._constraints.pop(constraint_id, None) is not None

    # -- queries -----------------------------------------------------------

    def get(self, constraint_id: str) -> Constraint | None:
        """Return a constraint by id, or ``None``."""
        return self._constraints.get(constraint_id)

    def active(self) -> list[Constraint]:
        """Return all active constraints."""
        return [c for c in self._constraints.values() if c.active]

    def by_type(self, constraint_type: str) -> list[Constraint]:
        """Return constraints matching the given type."""
        return [c for c in self._constraints.values() if c.constraint_type == constraint_type]

    def by_priority(self, priority: int) -> list[Constraint]:
        """Return constraints matching the given priority."""
        return [c for c in self._constraints.values() if c.priority == priority]

    # -- dunder ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._constraints)

    def __iter__(self) -> Iterator[Constraint]:
        return iter(self._constraints.values())

    def __bool__(self) -> bool:
        return bool(self._constraints)
