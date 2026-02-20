"""Tests for kala.governance.temporal — Timeline-derived feature extraction."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from kala.constraints.core import PRIORITY_SOFT, Constraint, ConstraintSet
from kala.constraints.evaluator import evaluate
from kala.governance.temporal import TemporalContext
from kala.ledger.core import Event, Ledger
from kala.timeline.core import Snapshot, Timeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = datetime(2024, 6, 1, tzinfo=timezone.utc)


def _dosha_timeline(days: int = 14) -> Timeline[dict[str, Any]]:
    """Create a dosha timeline with *days* daily snapshots."""
    tl: Timeline[dict[str, Any]] = Timeline()
    for i in range(days):
        tl.add(Snapshot(
            timestamp=_BASE + timedelta(days=i),
            value={
                "vata": 0.4 + i * 0.01,
                "pitta": 0.3 - i * 0.005,
                "kapha": 0.3 - i * 0.005,
            },
        ))
    return tl


def _guna_timeline(days: int = 14) -> Timeline[dict[str, Any]]:
    """Create a guna timeline with *days* daily snapshots."""
    tl: Timeline[dict[str, Any]] = Timeline()
    for i in range(days):
        tl.add(Snapshot(
            timestamp=_BASE + timedelta(days=i),
            value={
                "sattva": 0.5 + i * 0.01,
                "rajas": 0.3 - i * 0.005,
                "tamas": 0.2 - i * 0.005,
            },
        ))
    return tl


# ===========================================================================
# TemporalContext basics
# ===========================================================================


class TestTemporalContext:
    def test_empty_build(self) -> None:
        tc = TemporalContext()
        ctx = tc.build()
        assert ctx == {}

    def test_build_with_base_context(self) -> None:
        tc = TemporalContext()
        ctx = tc.build({"proposed_hour": 22})
        assert ctx["proposed_hour"] == 22

    def test_add_timeline(self) -> None:
        tc = TemporalContext()
        tl = _dosha_timeline()
        tc.add_timeline("dosha", tl)
        ctx = tc.build()
        assert "dosha.latest.vata" in ctx

    def test_build_with_multiple_timelines(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        tc.add_timeline("guna", _guna_timeline())
        ctx = tc.build()
        assert "dosha.latest.vata" in ctx
        assert "guna.latest.sattva" in ctx

    def test_empty_timeline_skipped(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("empty", Timeline())
        ctx = tc.build()
        assert ctx == {}


# ===========================================================================
# Temporal features
# ===========================================================================


class TestTemporalFeatures:
    def test_latest_values(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()
        # Last day (day 13): vata = 0.4 + 13*0.01 = 0.53
        assert abs(ctx["dosha.latest.vata"] - 0.53) < 0.001

    def test_moving_avg_7d(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()
        assert "dosha.moving_avg_7d.vata" in ctx
        # The 7d average should be between the min and max values
        avg = ctx["dosha.moving_avg_7d.vata"]
        assert 0.4 < avg < 0.54

    def test_moving_avg_14d(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()
        assert "dosha.moving_avg_14d.vata" in ctx

    def test_trend_7d(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()
        # Vata increases by 0.01/day → rising
        assert ctx.get("dosha.trend_7d.vata") == "rising"

    def test_trend_14d(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()
        assert ctx.get("dosha.trend_14d.vata") == "rising"

    def test_rate_7d(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()
        assert "dosha.rate_7d.vata" in ctx
        # Rate should be ~0.01 per day
        rate = ctx["dosha.rate_7d.vata"]
        assert 0.005 < rate < 0.015

    def test_guna_features(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("guna", _guna_timeline())
        ctx = tc.build()
        assert "guna.latest.sattva" in ctx
        assert "guna.moving_avg_7d.sattva" in ctx
        assert ctx.get("guna.trend_7d.sattva") == "rising"

    def test_ledger_event_count(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())

        ledger = Ledger()
        for i in range(5):
            ledger.append(Event(
                id=f"e{i}",
                timestamp=_BASE + timedelta(days=10 + i),
                entity_id="user-1",
                event_type="observed",
                action="check_in",
                actor="system",
            ))
        tc.set_ledger(ledger)
        ctx = tc.build()
        assert "ledger.event_count_7d" in ctx
        assert ctx["ledger.event_count_7d"] >= 1


# ===========================================================================
# evaluate_feature (ad-hoc queries)
# ===========================================================================


class TestEvaluateFeature:
    def test_latest_feature(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        result = tc.evaluate_feature("dosha.latest.vata")
        assert result is not None
        assert abs(result - 0.53) < 0.001

    def test_moving_avg_feature(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        result = tc.evaluate_feature("dosha.moving_avg_14d.vata")
        assert result is not None

    def test_trend_feature(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        result = tc.evaluate_feature("dosha.trend_7d.vata")
        assert result == "rising"

    def test_missing_timeline(self) -> None:
        tc = TemporalContext()
        result = tc.evaluate_feature("missing.latest.vata")
        assert result is None

    def test_missing_key(self) -> None:
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        result = tc.evaluate_feature("dosha.latest.nonexistent")
        assert result is None

    def test_short_spec(self) -> None:
        tc = TemporalContext()
        result = tc.evaluate_feature("dosha")
        assert result is None


# ===========================================================================
# End-to-end: TemporalContext → evaluate
# ===========================================================================


class TestConstraintWithTemporalContext:
    def test_constraint_on_moving_avg(self) -> None:
        """Constraint: vata 14-day moving average must be < 0.6."""
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()

        cs = ConstraintSet()
        cs.add(Constraint(
            id="vata-avg",
            constraint_type="drift_threshold",
            field="dosha.moving_avg_14d.vata",
            operator="lt",
            value=0.6,
            description="Vata 14d avg below 0.6",
            source="system",
            priority=PRIORITY_SOFT,
        ))
        result = evaluate(ctx, cs)
        assert result.action == "allow"

    def test_constraint_on_trend(self) -> None:
        """Constraint: vata trend should not be rising."""
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())
        ctx = tc.build()

        cs = ConstraintSet()
        cs.add(Constraint(
            id="vata-trend",
            constraint_type="drift_threshold",
            field="dosha.trend_7d.vata",
            operator="neq",
            value="rising",
            description="Vata should not be rising",
            source="system",
            priority=PRIORITY_SOFT,
        ))
        result = evaluate(ctx, cs)
        # Vata IS rising → violation → confirm
        assert result.action == "confirm"

    def test_end_to_end_build_evaluate(self) -> None:
        """Full pipeline: build temporal context, merge base context, evaluate."""
        tc = TemporalContext()
        tc.add_timeline("dosha", _dosha_timeline())

        base = {"proposed_hour": 21, "active_tasks": 2}
        ctx = tc.build(base)

        cs = ConstraintSet()
        cs.add(Constraint(
            id="sleep",
            constraint_type="time_boundary",
            field="proposed_hour",
            operator="lte",
            value=22,
            description="Sleep by 10pm",
            source="onboarding",
        ))
        cs.add(Constraint(
            id="vata-check",
            constraint_type="drift_threshold",
            field="dosha.moving_avg_14d.vata",
            operator="lt",
            value=0.6,
            description="Vata avg below 0.6",
            source="system",
        ))
        result = evaluate(ctx, cs)
        assert result.action == "allow"

    def test_temporal_triggers_block_with_hard_constraint(self) -> None:
        """High vata moving avg with hard constraint → block."""
        tc = TemporalContext()
        # Create timeline with high vata
        tl: Timeline[dict[str, Any]] = Timeline()
        for i in range(14):
            tl.add(Snapshot(
                timestamp=_BASE + timedelta(days=i),
                value={"vata": 0.8 + i * 0.01},
            ))
        tc.add_timeline("dosha", tl)
        ctx = tc.build()

        from kala.constraints.core import PRIORITY_HARD

        cs = ConstraintSet()
        cs.add(Constraint(
            id="vata-hard",
            constraint_type="drift_threshold",
            field="dosha.moving_avg_14d.vata",
            operator="lt",
            value=0.6,
            description="Vata too high for proactive",
            source="system",
            priority=PRIORITY_HARD,
        ))
        result = evaluate(ctx, cs)
        assert result.action == "block"
