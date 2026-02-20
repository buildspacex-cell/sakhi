"""Tests for kala.timeline.trend — trend detection and temporal analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kala.timeline.core import Snapshot, Timeline
from kala.timeline.trend import detect_trend, moving_average, rate_of_change

_T0 = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ts(days: int = 0) -> datetime:
    return _T0 + timedelta(days=days)


def _snap(dosha: dict, days: int = 0) -> Snapshot[dict]:
    return Snapshot(timestamp=_ts(days), value=dosha)


# ---------------------------------------------------------------------------
# detect_trend
# ---------------------------------------------------------------------------


class TestDetectTrend:
    def test_rising_trend(self) -> None:
        tl = Timeline([
            _snap({"vata": 0.3}, days=0),
            _snap({"vata": 0.35}, days=1),
            _snap({"vata": 0.4}, days=2),
            _snap({"vata": 0.5}, days=3),
            _snap({"vata": 0.6}, days=4),
            _snap({"vata": 0.7}, days=5),
        ])
        assert detect_trend(tl, "vata", timedelta(days=6)) == "rising"

    def test_falling_trend(self) -> None:
        tl = Timeline([
            _snap({"vata": 0.7}, days=0),
            _snap({"vata": 0.6}, days=1),
            _snap({"vata": 0.5}, days=2),
            _snap({"vata": 0.4}, days=3),
            _snap({"vata": 0.3}, days=4),
            _snap({"vata": 0.2}, days=5),
        ])
        assert detect_trend(tl, "vata", timedelta(days=6)) == "falling"

    def test_stable_trend(self) -> None:
        tl = Timeline([
            _snap({"vata": 0.33}, days=0),
            _snap({"vata": 0.33}, days=1),
            _snap({"vata": 0.34}, days=2),
            _snap({"vata": 0.33}, days=3),
        ])
        assert detect_trend(tl, "vata", timedelta(days=5)) == "stable"

    def test_unknown_with_insufficient_data(self) -> None:
        tl = Timeline([_snap({"vata": 0.5}, days=0)])
        assert detect_trend(tl, "vata", timedelta(days=7)) == "unknown"

    def test_unknown_with_empty_timeline(self) -> None:
        tl: Timeline[dict] = Timeline()
        assert detect_trend(tl, "vata", timedelta(days=7)) == "unknown"

    def test_missing_key_returns_unknown(self) -> None:
        tl = Timeline([
            _snap({"pitta": 0.5}, days=0),
            _snap({"pitta": 0.6}, days=1),
        ])
        assert detect_trend(tl, "vata", timedelta(days=3)) == "unknown"

    def test_nested_key(self) -> None:
        tl = Timeline([
            _snap({"dosha": {"vata": 0.3}}, days=0),
            _snap({"dosha": {"vata": 0.4}}, days=1),
            _snap({"dosha": {"vata": 0.5}}, days=2),
            _snap({"dosha": {"vata": 0.7}}, days=3),
        ])
        assert detect_trend(tl, "dosha.vata", timedelta(days=5)) == "rising"


# ---------------------------------------------------------------------------
# moving_average
# ---------------------------------------------------------------------------


class TestMovingAverage:
    def test_simple_average(self) -> None:
        tl = Timeline([
            _snap({"score": 1.0}, days=0),
            _snap({"score": 2.0}, days=1),
            _snap({"score": 3.0}, days=2),
        ])
        avg = moving_average(tl, "score", timedelta(days=10))
        assert avg == 2.0

    def test_windowed_average(self) -> None:
        tl = Timeline([
            _snap({"score": 100.0}, days=0),  # Outside window
            _snap({"score": 1.0}, days=8),
            _snap({"score": 3.0}, days=9),
            _snap({"score": 5.0}, days=10),
        ])
        avg = moving_average(tl, "score", timedelta(days=3))
        assert avg == 3.0  # (1 + 3 + 5) / 3

    def test_empty_timeline(self) -> None:
        tl: Timeline[dict] = Timeline()
        assert moving_average(tl, "score", timedelta(days=7)) is None

    def test_missing_key(self) -> None:
        tl = Timeline([_snap({"other": 1.0}, days=0)])
        assert moving_average(tl, "score", timedelta(days=7)) is None

    def test_nested_key(self) -> None:
        tl = Timeline([
            _snap({"dosha": {"vata": 0.4}}, days=0),
            _snap({"dosha": {"vata": 0.6}}, days=1),
        ])
        avg = moving_average(tl, "dosha.vata", timedelta(days=5))
        assert avg == 0.5


# ---------------------------------------------------------------------------
# rate_of_change
# ---------------------------------------------------------------------------


class TestRateOfChange:
    def test_positive_rate(self) -> None:
        tl = Timeline([
            _snap({"score": 0.0}, days=0),
            _snap({"score": 10.0}, days=10),
        ])
        rate = rate_of_change(tl, "score", timedelta(days=20))
        assert rate == 1.0  # 10 / 10 days

    def test_negative_rate(self) -> None:
        tl = Timeline([
            _snap({"score": 10.0}, days=0),
            _snap({"score": 0.0}, days=5),
        ])
        rate = rate_of_change(tl, "score", timedelta(days=10))
        assert rate == -2.0  # -10 / 5 days

    def test_zero_rate(self) -> None:
        tl = Timeline([
            _snap({"score": 5.0}, days=0),
            _snap({"score": 5.0}, days=10),
        ])
        rate = rate_of_change(tl, "score", timedelta(days=20))
        assert rate == 0.0

    def test_insufficient_data(self) -> None:
        tl = Timeline([_snap({"score": 5.0}, days=0)])
        assert rate_of_change(tl, "score", timedelta(days=7)) is None

    def test_same_timestamp(self) -> None:
        tl = Timeline([
            _snap({"score": 1.0}, days=0),
            _snap({"score": 2.0}, days=0),
        ])
        assert rate_of_change(tl, "score", timedelta(days=7)) is None

    def test_empty_timeline(self) -> None:
        tl: Timeline[dict] = Timeline()
        assert rate_of_change(tl, "score", timedelta(days=7)) is None
