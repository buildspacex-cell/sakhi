"""Tests for kala.timeline.core — Snapshot and Timeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kala.timeline.core import Snapshot, Timeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ts(days: int = 0, hours: int = 0) -> datetime:
    return _T0 + timedelta(days=days, hours=hours)


def _snap(value: float, days: int = 0, hours: int = 0, confidence: float = 1.0, source: str = "") -> Snapshot[float]:
    return Snapshot(timestamp=_ts(days, hours), value=value, confidence=confidence, source=source)


def _dict_snap(value: dict, days: int = 0, **kw) -> Snapshot[dict]:
    return Snapshot(timestamp=_ts(days), value=value, **kw)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_ordering(self) -> None:
        a = _snap(1.0, days=1)
        b = _snap(2.0, days=2)
        assert a < b
        assert not b < a

    def test_equal_timestamps(self) -> None:
        a = _snap(1.0, days=1)
        b = _snap(2.0, days=1)
        assert not a < b
        assert not b < a

    def test_default_confidence(self) -> None:
        s = Snapshot(timestamp=_T0, value=42)
        assert s.confidence == 1.0

    def test_default_source(self) -> None:
        s = Snapshot(timestamp=_T0, value=42)
        assert s.source == ""


# ---------------------------------------------------------------------------
# Timeline — construction
# ---------------------------------------------------------------------------


class TestTimelineConstruction:
    def test_empty(self) -> None:
        tl = Timeline()
        assert len(tl) == 0
        assert not tl

    def test_from_list(self) -> None:
        snaps = [_snap(3.0, days=3), _snap(1.0, days=1), _snap(2.0, days=2)]
        tl = Timeline(snaps)
        assert len(tl) == 3
        # Sorted by timestamp
        values = [s.value for s in tl]
        assert values == [1.0, 2.0, 3.0]

    def test_add_maintains_order(self) -> None:
        tl = Timeline()
        tl.add(_snap(3.0, days=3))
        tl.add(_snap(1.0, days=1))
        tl.add(_snap(2.0, days=2))
        values = [s.value for s in tl]
        assert values == [1.0, 2.0, 3.0]


# ---------------------------------------------------------------------------
# Timeline — queries
# ---------------------------------------------------------------------------


class TestTimelineAt:
    def test_at_exact_time(self) -> None:
        tl = Timeline([_snap(10, days=1), _snap(20, days=2), _snap(30, days=3)])
        result = tl.at(_ts(days=2))
        assert result is not None
        assert result.value == 20

    def test_at_between_snapshots(self) -> None:
        tl = Timeline([_snap(10, days=1), _snap(30, days=3)])
        result = tl.at(_ts(days=2))
        assert result is not None
        assert result.value == 10  # Latest before t=day2

    def test_at_before_all(self) -> None:
        tl = Timeline([_snap(10, days=5)])
        result = tl.at(_ts(days=1))
        assert result is None

    def test_at_after_all(self) -> None:
        tl = Timeline([_snap(10, days=1), _snap(20, days=2)])
        result = tl.at(_ts(days=100))
        assert result is not None
        assert result.value == 20

    def test_at_empty_timeline(self) -> None:
        tl = Timeline()
        assert tl.at(_T0) is None


class TestTimelineBetween:
    def test_between_inclusive_exclusive(self) -> None:
        tl = Timeline([_snap(i, days=i) for i in range(5)])
        result = tl.between(_ts(days=1), _ts(days=3))
        values = [s.value for s in result]
        assert values == [1, 2]  # Days 1, 2 — not 3

    def test_between_no_match(self) -> None:
        tl = Timeline([_snap(1, days=1)])
        result = tl.between(_ts(days=5), _ts(days=10))
        assert result == []

    def test_between_all(self) -> None:
        tl = Timeline([_snap(i, days=i) for i in range(3)])
        result = tl.between(_ts(days=0), _ts(days=100))
        assert len(result) == 3


class TestTimelineWindow:
    def test_window_returns_recent(self) -> None:
        tl = Timeline([_snap(i, days=i) for i in range(10)])
        result = tl.window(timedelta(days=3))
        # Last 3 days from day 9: start=day6, end=day9+ε → days 6, 7, 8, 9
        values = [s.value for s in result]
        assert values == [6, 7, 8, 9]

    def test_window_empty_timeline(self) -> None:
        tl = Timeline()
        assert tl.window(timedelta(days=7)) == []

    def test_window_larger_than_timeline(self) -> None:
        tl = Timeline([_snap(1, days=1), _snap(2, days=2)])
        result = tl.window(timedelta(days=365))
        assert len(result) == 2


class TestTimelineLatestEarliest:
    def test_latest(self) -> None:
        tl = Timeline([_snap(1, days=1), _snap(2, days=2), _snap(3, days=3)])
        assert tl.latest().value == 3

    def test_earliest(self) -> None:
        tl = Timeline([_snap(1, days=1), _snap(2, days=2), _snap(3, days=3)])
        assert tl.earliest().value == 1

    def test_latest_empty(self) -> None:
        assert Timeline().latest() is None

    def test_earliest_empty(self) -> None:
        assert Timeline().earliest() is None


# ---------------------------------------------------------------------------
# Timeline — dunder
# ---------------------------------------------------------------------------


class TestTimelineDunder:
    def test_len(self) -> None:
        tl = Timeline([_snap(i, days=i) for i in range(5)])
        assert len(tl) == 5

    def test_bool_empty(self) -> None:
        assert not Timeline()

    def test_bool_nonempty(self) -> None:
        assert Timeline([_snap(1, days=1)])

    def test_repr_empty(self) -> None:
        assert "empty" in repr(Timeline())

    def test_repr_nonempty(self) -> None:
        tl = Timeline([_snap(1, days=1), _snap(2, days=2)])
        r = repr(tl)
        assert "2 snapshots" in r

    def test_iter(self) -> None:
        tl = Timeline([_snap(1, days=1), _snap(2, days=2)])
        values = [s.value for s in tl]
        assert values == [1, 2]


# ---------------------------------------------------------------------------
# Generic type usage
# ---------------------------------------------------------------------------


class TestGenericTypes:
    def test_dict_timeline(self) -> None:
        tl: Timeline[dict] = Timeline()
        tl.add(Snapshot(timestamp=_ts(days=1), value={"vata": 0.5, "pitta": 0.3, "kapha": 0.2}))
        tl.add(Snapshot(timestamp=_ts(days=2), value={"vata": 0.4, "pitta": 0.4, "kapha": 0.2}))
        assert len(tl) == 2
        assert tl.latest().value["pitta"] == 0.4

    def test_string_timeline(self) -> None:
        tl: Timeline[str] = Timeline()
        tl.add(Snapshot(timestamp=_ts(days=1), value="morning"))
        tl.add(Snapshot(timestamp=_ts(days=2), value="evening"))
        assert tl.latest().value == "evening"
