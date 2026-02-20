"""Tests for kala.constraints — data-driven constraint evaluation engine."""

from __future__ import annotations

import pytest

from kala.constraints.core import (
    PRIORITY_HARD,
    PRIORITY_MEDIUM,
    PRIORITY_SOFT,
    Constraint,
    ConstraintSet,
    Verdict,
    Violation,
)
from kala.constraints.evaluator import evaluate, evaluate_single
from kala.constraints.operators import (
    _MISSING,
    VALID_OPERATORS,
    check,
    extract_field,
    is_missing,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_constraint(
    *,
    id: str = "c1",
    constraint_type: str = "custom",
    field: str = "score",
    operator: str = "gt",
    value: object = 50,
    description: str = "test constraint",
    source: str = "test",
    priority: int = PRIORITY_SOFT,
    active: bool = True,
    metadata: dict | None = None,
) -> Constraint:
    return Constraint(
        id=id,
        constraint_type=constraint_type,
        field=field,
        operator=operator,
        value=value,
        description=description,
        source=source,
        priority=priority,
        active=active,
        metadata=metadata or {},
    )


# ===========================================================================
# extract_field
# ===========================================================================


class TestExtractField:
    def test_simple_key(self) -> None:
        assert extract_field({"name": "Alice"}, "name") == "Alice"

    def test_nested_key(self) -> None:
        assert extract_field({"drift": {"drift_percentage": 35.0}}, "drift.drift_percentage") == 35.0

    def test_deeply_nested(self) -> None:
        data = {"a": {"b": {"c": 42}}}
        assert extract_field(data, "a.b.c") == 42

    def test_missing_key(self) -> None:
        assert is_missing(extract_field({"name": "Alice"}, "age"))

    def test_missing_nested(self) -> None:
        assert is_missing(extract_field({"a": {"b": 1}}, "a.c.d"))

    def test_non_dict_input(self) -> None:
        assert is_missing(extract_field("not a dict", "key"))  # type: ignore[arg-type]

    def test_list_index(self) -> None:
        data = {"items": [{"title": "first"}, {"title": "second"}]}
        assert extract_field(data, "items.1.title") == "second"

    def test_list_index_out_of_range(self) -> None:
        data = {"items": [1, 2]}
        assert is_missing(extract_field(data, "items.5"))

    def test_none_intermediate(self) -> None:
        data = {"a": None}
        assert is_missing(extract_field(data, "a.b"))


# ===========================================================================
# _MISSING sentinel
# ===========================================================================


class TestMissingSentinel:
    def test_is_falsy(self) -> None:
        assert not _MISSING

    def test_is_singleton(self) -> None:
        from kala.constraints.operators import _MissingSentinel

        assert _MissingSentinel() is _MissingSentinel()

    def test_repr(self) -> None:
        assert repr(_MISSING) == "<MISSING>"


# ===========================================================================
# check (operator evaluation)
# ===========================================================================


class TestOperatorCheck:
    def test_eq_true(self) -> None:
        assert check("eq", 5, 5) is True

    def test_eq_false(self) -> None:
        assert check("eq", 5, 6) is False

    def test_neq(self) -> None:
        assert check("neq", 5, 6) is True
        assert check("neq", 5, 5) is False

    def test_lt(self) -> None:
        assert check("lt", 3, 5) is True
        assert check("lt", 5, 3) is False

    def test_gt(self) -> None:
        assert check("gt", 5, 3) is True
        assert check("gt", 3, 5) is False

    def test_lte(self) -> None:
        assert check("lte", 3, 5) is True
        assert check("lte", 5, 5) is True
        assert check("lte", 6, 5) is False

    def test_gte(self) -> None:
        assert check("gte", 5, 3) is True
        assert check("gte", 5, 5) is True
        assert check("gte", 3, 5) is False

    def test_in(self) -> None:
        assert check("in", "a", ["a", "b", "c"]) is True
        assert check("in", "d", ["a", "b", "c"]) is False

    def test_not_in(self) -> None:
        assert check("not_in", "d", ["a", "b", "c"]) is True
        assert check("not_in", "a", ["a", "b", "c"]) is False

    def test_between(self) -> None:
        assert check("between", 5, [1, 10]) is True
        assert check("between", 1, [1, 10]) is True
        assert check("between", 10, [1, 10]) is True
        assert check("between", 11, [1, 10]) is False

    def test_contains(self) -> None:
        assert check("contains", "hello world", "world") is True
        assert check("contains", "hello world", "xyz") is False
        assert check("contains", [1, 2, 3], 2) is True

    def test_not_contains(self) -> None:
        assert check("not_contains", "hello", "xyz") is True
        assert check("not_contains", "hello", "ell") is False

    def test_numeric_coercion(self) -> None:
        assert check("gt", "10", "5") is True
        assert check("lt", "3", 5) is True

    def test_numeric_coercion_failure(self) -> None:
        assert check("gt", "not_a_number", 5) is False

    def test_between_bad_input(self) -> None:
        assert check("between", "x", [1, 10]) is False
        assert check("between", 5, []) is False

    def test_contains_non_iterable(self) -> None:
        assert check("contains", 42, "x") is False

    def test_not_contains_non_iterable(self) -> None:
        assert check("not_contains", 42, "x") is True

    def test_invalid_operator_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown operator"):
            check("invalid_op", 1, 2)

    def test_all_valid_operators_in_frozenset(self) -> None:
        expected = {"lt", "gt", "lte", "gte", "eq", "neq", "in", "not_in", "between", "contains", "not_contains"}
        assert VALID_OPERATORS == expected


# ===========================================================================
# Constraint dataclass
# ===========================================================================


class TestConstraintDataclass:
    def test_creation(self) -> None:
        c = _make_constraint()
        assert c.id == "c1"
        assert c.constraint_type == "custom"
        assert c.active is True

    def test_frozen(self) -> None:
        c = _make_constraint()
        with pytest.raises(AttributeError):
            c.active = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        c = _make_constraint()
        assert c.priority == PRIORITY_SOFT
        assert c.active is True
        assert c.metadata == {}

    def test_metadata_isolation(self) -> None:
        c1 = _make_constraint(id="a")
        c2 = _make_constraint(id="b")
        assert c1.metadata is not c2.metadata

    def test_all_fields(self) -> None:
        c = _make_constraint(
            id="x",
            constraint_type="time_boundary",
            field="proposed_time",
            operator="lte",
            value=22,
            description="Sleep by 10pm",
            source="onboarding",
            priority=PRIORITY_HARD,
            active=True,
            metadata={"origin": "user"},
        )
        assert c.field == "proposed_time"
        assert c.priority == PRIORITY_HARD
        assert c.metadata == {"origin": "user"}


# ===========================================================================
# Violation
# ===========================================================================


class TestViolation:
    def test_creation(self) -> None:
        c = _make_constraint()
        v = Violation(constraint=c, actual_value=30, message="too low")
        assert v.actual_value == 30
        assert v.message == "too low"

    def test_frozen(self) -> None:
        c = _make_constraint()
        v = Violation(constraint=c, actual_value=30, message="too low")
        with pytest.raises(AttributeError):
            v.message = "changed"  # type: ignore[misc]


# ===========================================================================
# Verdict
# ===========================================================================


class TestVerdict:
    def test_allow(self) -> None:
        v = Verdict.allow()
        assert v.action == "allow"
        assert v.violations == ()

    def test_block(self) -> None:
        c = _make_constraint()
        viol = Violation(constraint=c, actual_value=30, message="fail")
        v = Verdict.block([viol])
        assert v.action == "block"
        assert len(v.violations) == 1

    def test_confirm(self) -> None:
        c = _make_constraint()
        viol = Violation(constraint=c, actual_value=30, message="fail")
        v = Verdict.confirm([viol])
        assert v.action == "confirm"
        assert len(v.violations) == 1

    def test_frozen(self) -> None:
        v = Verdict.allow()
        with pytest.raises(AttributeError):
            v.action = "block"  # type: ignore[misc]

    def test_violations_are_tuple(self) -> None:
        c = _make_constraint()
        viol = Violation(constraint=c, actual_value=30, message="fail")
        v = Verdict.block([viol])
        assert isinstance(v.violations, tuple)


# ===========================================================================
# ConstraintSet
# ===========================================================================


class TestConstraintSet:
    def test_add_and_len(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a"))
        cs.add(_make_constraint(id="b"))
        assert len(cs) == 2

    def test_add_replaces_by_id(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", description="v1"))
        cs.add(_make_constraint(id="a", description="v2"))
        assert len(cs) == 1
        assert cs.get("a").description == "v2"

    def test_remove_existing(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a"))
        assert cs.remove("a") is True
        assert len(cs) == 0

    def test_remove_nonexistent(self) -> None:
        cs = ConstraintSet()
        assert cs.remove("nope") is False

    def test_get(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a"))
        assert cs.get("a") is not None
        assert cs.get("b") is None

    def test_active_filters(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", active=True))
        cs.add(_make_constraint(id="b", active=False))
        assert len(cs.active()) == 1

    def test_by_type(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", constraint_type="time_boundary"))
        cs.add(_make_constraint(id="b", constraint_type="custom"))
        assert len(cs.by_type("time_boundary")) == 1

    def test_by_priority(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", priority=PRIORITY_HARD))
        cs.add(_make_constraint(id="b", priority=PRIORITY_SOFT))
        assert len(cs.by_priority(PRIORITY_HARD)) == 1

    def test_iter(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a"))
        cs.add(_make_constraint(id="b"))
        assert len(list(cs)) == 2

    def test_bool(self) -> None:
        cs = ConstraintSet()
        assert not cs
        cs.add(_make_constraint(id="a"))
        assert cs


# ===========================================================================
# evaluate_single
# ===========================================================================


class TestEvaluateSingle:
    def test_satisfied(self) -> None:
        c = _make_constraint(field="score", operator="gt", value=50)
        result = evaluate_single({"score": 80}, c)
        assert result is None

    def test_violated(self) -> None:
        c = _make_constraint(field="score", operator="gt", value=50)
        result = evaluate_single({"score": 30}, c)
        assert result is not None
        assert result.actual_value == 30

    def test_inactive_skipped(self) -> None:
        c = _make_constraint(active=False, field="score", operator="gt", value=50)
        result = evaluate_single({"score": 30}, c)
        assert result is None

    def test_missing_field_hard_violates(self) -> None:
        c = _make_constraint(field="required_field", priority=PRIORITY_HARD)
        result = evaluate_single({}, c)
        assert result is not None
        assert "missing" in result.message.lower()

    def test_missing_field_soft_skips(self) -> None:
        c = _make_constraint(field="optional_field", priority=PRIORITY_SOFT)
        result = evaluate_single({}, c)
        assert result is None

    def test_nested_field(self) -> None:
        c = _make_constraint(field="drift.drift_percentage", operator="lt", value=30)
        result = evaluate_single({"drift": {"drift_percentage": 15.0}}, c)
        assert result is None

    def test_nested_field_violated(self) -> None:
        c = _make_constraint(field="drift.drift_percentage", operator="lt", value=30)
        result = evaluate_single({"drift": {"drift_percentage": 45.0}}, c)
        assert result is not None
        assert result.actual_value == 45.0


# ===========================================================================
# evaluate (full engine)
# ===========================================================================


class TestEvaluate:
    def test_all_pass(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", field="score", operator="gt", value=50))
        result = evaluate({"score": 80}, cs)
        assert result.action == "allow"
        assert result.violations == ()

    def test_soft_violation_confirms(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", field="score", operator="gt", value=50, priority=PRIORITY_SOFT))
        result = evaluate({"score": 30}, cs)
        assert result.action == "confirm"
        assert len(result.violations) == 1

    def test_hard_violation_blocks(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", field="score", operator="gt", value=50, priority=PRIORITY_HARD))
        result = evaluate({"score": 30}, cs)
        assert result.action == "block"

    def test_mixed_hard_wins(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="soft", field="a", operator="gt", value=50, priority=PRIORITY_SOFT))
        cs.add(_make_constraint(id="hard", field="b", operator="gt", value=50, priority=PRIORITY_HARD))
        result = evaluate({"a": 30, "b": 30}, cs)
        assert result.action == "block"
        assert len(result.violations) == 2

    def test_empty_constraints(self) -> None:
        result = evaluate({"score": 80}, ConstraintSet())
        assert result.action == "allow"

    def test_with_list_of_constraints(self) -> None:
        constraints = [
            _make_constraint(id="a", field="score", operator="gt", value=50),
        ]
        result = evaluate({"score": 80}, constraints)
        assert result.action == "allow"

    def test_inactive_filtered_out(self) -> None:
        cs = ConstraintSet()
        cs.add(_make_constraint(id="a", field="score", operator="gt", value=50, active=False))
        result = evaluate({"score": 30}, cs)
        assert result.action == "allow"


# ===========================================================================
# Real-world scenarios
# ===========================================================================


class TestRealWorldScenarios:
    def test_sleep_boundary(self) -> None:
        """User committed to sleeping by 10pm (hour 22)."""
        cs = ConstraintSet()
        cs.add(Constraint(
            id="sleep-boundary",
            constraint_type="time_boundary",
            field="proposed_hour",
            operator="lte",
            value=22,
            description="Sleep by 10pm",
            source="onboarding",
            priority=PRIORITY_HARD,
        ))
        # Proposing activity at 23:00 → block
        result = evaluate({"proposed_hour": 23}, cs)
        assert result.action == "block"

        # Proposing activity at 21:00 → allow
        result = evaluate({"proposed_hour": 21}, cs)
        assert result.action == "allow"

    def test_drift_threshold(self) -> None:
        """Block proactive suggestions when drift > 40%."""
        cs = ConstraintSet()
        cs.add(Constraint(
            id="drift-gate",
            constraint_type="drift_threshold",
            field="drift.drift_percentage",
            operator="lt",
            value=40.0,
            description="Drift below 40% for proactive",
            source="system",
            priority=PRIORITY_HARD,
        ))
        result = evaluate({"drift": {"drift_percentage": 45.0}}, cs)
        assert result.action == "block"

        result = evaluate({"drift": {"drift_percentage": 20.0}}, cs)
        assert result.action == "allow"

    def test_value_alignment(self) -> None:
        """Suggestion should align with user's core values."""
        cs = ConstraintSet()
        cs.add(Constraint(
            id="value-check",
            constraint_type="value_alignment",
            field="aligned_values",
            operator="contains",
            value="health",
            description="Must align with health value",
            source="personal_model",
            priority=PRIORITY_MEDIUM,
        ))
        # Aligned → allow
        result = evaluate({"aligned_values": ["health", "growth"]}, cs)
        assert result.action == "allow"

        # Not aligned → confirm (medium priority)
        result = evaluate({"aligned_values": ["productivity"]}, cs)
        assert result.action == "confirm"

    def test_capacity_limit(self) -> None:
        """Don't suggest more than 3 active tasks."""
        cs = ConstraintSet()
        cs.add(Constraint(
            id="capacity",
            constraint_type="capacity",
            field="active_task_count",
            operator="lt",
            value=4,
            description="Max 3 active tasks",
            source="system",
            priority=PRIORITY_SOFT,
        ))
        result = evaluate({"active_task_count": 5}, cs)
        assert result.action == "confirm"

        result = evaluate({"active_task_count": 2}, cs)
        assert result.action == "allow"
