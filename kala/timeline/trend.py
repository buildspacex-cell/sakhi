"""Trend detection — temporal analysis on numeric timelines.

All functions operate on ``Timeline[dict[str, float]]`` and extract
trend direction, moving averages, and rates of change.
Pure computation — no DB, no LLM.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from kala.timeline.core import Timeline


def detect_trend(
    timeline: Timeline[dict[str, Any]],
    key: str,
    window: timedelta,
) -> str:
    """Detect if *key* is ``'rising'``, ``'falling'``, or ``'stable'`` over *window*.

    Splits the window into two halves and compares the average value in
    each half.  Returns ``'unknown'`` if there are fewer than 2 snapshots.
    """
    snaps = timeline.window(window)
    values = [(s.timestamp, _extract(s.value, key)) for s in snaps]
    values = [(ts, v) for ts, v in values if v is not None]
    if len(values) < 2:
        return "unknown"

    mid = len(values) // 2
    first_half = [v for _, v in values[:mid]]
    second_half = [v for _, v in values[mid:]]

    if not first_half or not second_half:
        return "unknown"

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    delta = avg_second - avg_first
    # Use 5% of the range as threshold for "stable"
    threshold = max(0.02, abs(avg_first) * 0.05)

    if delta > threshold:
        return "rising"
    if delta < -threshold:
        return "falling"
    return "stable"


def moving_average(
    timeline: Timeline[dict[str, Any]],
    key: str,
    window: timedelta,
) -> float | None:
    """Compute the mean of *key* over the last *window* of the timeline.

    Returns ``None`` if no snapshots contain *key*.
    """
    snaps = timeline.window(window)
    values = [_extract(s.value, key) for s in snaps]
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def rate_of_change(
    timeline: Timeline[dict[str, Any]],
    key: str,
    window: timedelta,
) -> float | None:
    """Compute the rate of change of *key* per day over *window*.

    Uses a simple (last − first) / days formula.  Returns ``None`` if
    fewer than 2 data points or zero time span.
    """
    snaps = timeline.window(window)
    pairs = [(s.timestamp, _extract(s.value, key)) for s in snaps]
    pairs = [(ts, v) for ts, v in pairs if v is not None]
    if len(pairs) < 2:
        return None

    first_ts, first_val = pairs[0]
    last_ts, last_val = pairs[-1]

    span_days = (last_ts - first_ts).total_seconds() / 86400
    if span_days == 0:
        return None
    return (last_val - first_val) / span_days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract(value: Any, key: str) -> float | None:
    """Safely extract a float from a dict value, supporting nested keys.

    Supports dotted keys like ``"dosha.vata"`` for nested dicts.
    """
    if not isinstance(value, dict):
        return None
    parts = key.split(".")
    current: Any = value
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    if current is None:
        return None
    try:
        return float(current)
    except (TypeError, ValueError):
        return None
