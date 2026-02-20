"""Tests for kala.timeline.reconcile — multi-source state reconciliation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kala.timeline.core import Snapshot
from kala.timeline.reconcile import detect_conflict, reconcile_snapshots

_T0 = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ts(days: int = 0) -> datetime:
    return _T0 + timedelta(days=days)


def _snap(value: dict, days: int = 0, confidence: float = 1.0, source: str = "") -> Snapshot[dict]:
    return Snapshot(timestamp=_ts(days), value=value, confidence=confidence, source=source)


# ---------------------------------------------------------------------------
# reconcile_snapshots — confidence_weighted
# ---------------------------------------------------------------------------


class TestConfidenceWeighted:
    def test_equal_confidence(self) -> None:
        snaps = [
            _snap({"vata": 0.6}, confidence=1.0, source="journal"),
            _snap({"vata": 0.4}, confidence=1.0, source="body"),
        ]
        result = reconcile_snapshots(snaps, "confidence_weighted")
        assert abs(result["vata"] - 0.5) < 0.01  # (0.6 + 0.4) / 2

    def test_weighted_by_confidence(self) -> None:
        snaps = [
            _snap({"vata": 0.8}, confidence=0.9, source="journal"),
            _snap({"vata": 0.2}, confidence=0.1, source="body"),
        ]
        result = reconcile_snapshots(snaps, "confidence_weighted")
        # 0.8*0.9 + 0.2*0.1 = 0.72 + 0.02 = 0.74; / (0.9+0.1) = 0.74
        assert result["vata"] > 0.7  # Journal dominates

    def test_multiple_keys(self) -> None:
        snaps = [
            _snap({"vata": 0.5, "pitta": 0.3}, confidence=1.0),
            _snap({"vata": 0.5, "pitta": 0.7}, confidence=1.0),
        ]
        result = reconcile_snapshots(snaps, "confidence_weighted")
        assert "vata" in result
        assert "pitta" in result
        assert abs(result["pitta"] - 0.5) < 0.01

    def test_empty_snapshots(self) -> None:
        assert reconcile_snapshots([], "confidence_weighted") == {}


# ---------------------------------------------------------------------------
# reconcile_snapshots — latest_wins
# ---------------------------------------------------------------------------


class TestLatestWins:
    def test_takes_most_recent(self) -> None:
        snaps = [
            _snap({"vata": 0.3}, days=1, source="old"),
            _snap({"vata": 0.7}, days=2, source="new"),
        ]
        result = reconcile_snapshots(snaps, "latest_wins")
        assert result["vata"] == 0.7

    def test_ignores_confidence(self) -> None:
        snaps = [
            _snap({"vata": 0.3}, days=1, confidence=0.99),
            _snap({"vata": 0.7}, days=2, confidence=0.01),
        ]
        result = reconcile_snapshots(snaps, "latest_wins")
        assert result["vata"] == 0.7


# ---------------------------------------------------------------------------
# reconcile_snapshots — average
# ---------------------------------------------------------------------------


class TestAverage:
    def test_simple_average(self) -> None:
        snaps = [
            _snap({"score": 10.0}),
            _snap({"score": 20.0}, days=1),
            _snap({"score": 30.0}, days=2),
        ]
        result = reconcile_snapshots(snaps, "average")
        assert abs(result["score"] - 20.0) < 0.01

    def test_ignores_confidence(self) -> None:
        snaps = [
            _snap({"score": 10.0}, confidence=0.01),
            _snap({"score": 20.0}, days=1, confidence=0.99),
        ]
        result = reconcile_snapshots(snaps, "average")
        assert abs(result["score"] - 15.0) < 0.01


# ---------------------------------------------------------------------------
# reconcile_snapshots — default strategy
# ---------------------------------------------------------------------------


class TestDefaultStrategy:
    def test_default_is_confidence_weighted(self) -> None:
        snaps = [
            _snap({"x": 0.8}, confidence=0.9),
            _snap({"x": 0.2}, confidence=0.1),
        ]
        result_default = reconcile_snapshots(snaps)
        result_explicit = reconcile_snapshots(snaps, "confidence_weighted")
        assert result_default == result_explicit


# ---------------------------------------------------------------------------
# detect_conflict
# ---------------------------------------------------------------------------


class TestDetectConflict:
    def test_conflict_detected(self) -> None:
        snaps = [
            _snap({"vata": 0.8, "pitta": 0.1}),
            _snap({"vata": 0.2, "pitta": 0.1}),
        ]
        conflicts = detect_conflict(snaps, threshold=0.3)
        assert "vata" in conflicts
        assert "pitta" not in conflicts

    def test_no_conflict(self) -> None:
        snaps = [
            _snap({"vata": 0.5}),
            _snap({"vata": 0.55}),
        ]
        conflicts = detect_conflict(snaps, threshold=0.3)
        assert conflicts == []

    def test_single_snapshot(self) -> None:
        snaps = [_snap({"vata": 0.5})]
        assert detect_conflict(snaps) == []

    def test_empty(self) -> None:
        assert detect_conflict([]) == []

    def test_multi_key_conflict(self) -> None:
        snaps = [
            _snap({"vata": 0.8, "pitta": 0.9, "kapha": 0.1}),
            _snap({"vata": 0.1, "pitta": 0.1, "kapha": 0.1}),
        ]
        conflicts = detect_conflict(snaps, threshold=0.3)
        assert "vata" in conflicts
        assert "pitta" in conflicts
        assert "kapha" not in conflicts
