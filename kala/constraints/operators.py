"""Atomic comparison predicates and field extraction for constraints."""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Valid operators
# ---------------------------------------------------------------------------

VALID_OPERATORS: frozenset[str] = frozenset({
    "lt", "gt", "lte", "gte",
    "eq", "neq",
    "in", "not_in",
    "between",
    "contains", "not_contains",
})


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------


def extract_field(data: dict[str, Any], path: str) -> Any:
    """Extract a value from *data* using a dotted path.

    Supports:
    - Simple keys: ``"name"``
    - Nested keys: ``"drift.drift_percentage"``
    - Integer list indexing: ``"items.0.title"``
    - Returns ``_MISSING`` sentinel when the path cannot be resolved.
    """
    if not isinstance(data, dict):
        return _MISSING
    # Check for exact key match first (supports flat keys like "dosha.trend_7d.vata")
    if path in data:
        return data[path]
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, _MISSING)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return _MISSING
        else:
            return _MISSING
        if current is _MISSING:
            return _MISSING
    return current


class _MissingSentinel:
    """Sentinel for missing field values (distinct from ``None``)."""

    _instance: _MissingSentinel | None = None

    def __new__(cls) -> _MissingSentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<MISSING>"

    def __bool__(self) -> bool:
        return False


_MISSING = _MissingSentinel()


def is_missing(value: Any) -> bool:
    """Return ``True`` if *value* is the missing-field sentinel."""
    return value is _MISSING


# ---------------------------------------------------------------------------
# Operator evaluation
# ---------------------------------------------------------------------------


def check(operator: str, actual: Any, expected: Any) -> bool:
    """Evaluate a single comparison predicate.

    Raises ``ValueError`` for unknown operators.
    """
    if operator not in VALID_OPERATORS:
        raise ValueError(f"Unknown operator: {operator!r}")

    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected

    # Numeric comparisons — coerce to float
    if operator in ("lt", "gt", "lte", "gte"):
        try:
            a, b = float(actual), float(expected)
        except (TypeError, ValueError):
            return False
        if operator == "lt":
            return a < b
        if operator == "gt":
            return a > b
        if operator == "lte":
            return a <= b
        return a >= b  # gte

    # Collection membership
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected

    # Range check
    if operator == "between":
        try:
            a = float(actual)
            lo, hi = float(expected[0]), float(expected[1])
        except (TypeError, ValueError, IndexError):
            return False
        return lo <= a <= hi

    # String / collection containment
    if operator == "contains":
        try:
            return expected in actual
        except TypeError:
            return False
    if operator == "not_contains":
        try:
            return expected not in actual
        except TypeError:
            return True

    # Unreachable due to guard above, but keeps mypy happy
    raise ValueError(f"Unknown operator: {operator!r}")  # pragma: no cover
