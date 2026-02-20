"""Temporal feature extraction — Timeline data → enriched action_context.

Bridges temporal intelligence into the constraint evaluation pipeline.
Instead of embedding temporal computation inside the evaluator, this module
extracts features from Timelines into a flat dict that the existing evaluator
can evaluate constraints against.

Flow::

    Timelines → TemporalContext.build() → enriched action_context → evaluate() → Verdict
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from kala.ledger.core import Ledger
from kala.timeline.core import Timeline
from kala.timeline.trend import detect_trend, moving_average, rate_of_change

# ---------------------------------------------------------------------------
# Standard windows
# ---------------------------------------------------------------------------

_WINDOWS: dict[str, timedelta] = {
    "7d": timedelta(days=7),
    "14d": timedelta(days=14),
}


# ---------------------------------------------------------------------------
# TemporalContext
# ---------------------------------------------------------------------------


class TemporalContext:
    """Builds an enriched action_context from Timeline data.

    Extracts temporal features (moving averages, trends, rates of change)
    and merges them into the action_context dict so constraints can
    reference them via dotted paths.

    Example::

        tc = TemporalContext()
        tc.add_timeline("dosha", dosha_timeline)
        ctx = tc.build({"proposed_hour": 22})
        # ctx now contains:
        #   "dosha.latest.vata": 0.5
        #   "dosha.moving_avg_7d.vata": 0.48
        #   "dosha.trend_7d.vata": "rising"
        #   etc.
    """

    def __init__(self) -> None:
        self._timelines: dict[str, Timeline[dict[str, Any]]] = {}
        self._ledger: Ledger | None = None

    def add_timeline(self, name: str, timeline: Timeline[dict[str, Any]]) -> None:
        """Register a named timeline (e.g., ``'dosha'``, ``'guna'``)."""
        self._timelines[name] = timeline

    def set_ledger(self, ledger: Ledger) -> None:
        """Optionally attach a ledger for event-count features."""
        self._ledger = ledger

    def build(self, base_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build enriched action_context with temporal features.

        For each registered timeline, extracts:

        - ``{name}.latest.{key}``: latest value for each key
        - ``{name}.moving_avg_7d.{key}``: 7-day moving average
        - ``{name}.moving_avg_14d.{key}``: 14-day moving average
        - ``{name}.trend_7d.{key}``: 7-day trend (rising/falling/stable)
        - ``{name}.trend_14d.{key}``: 14-day trend
        - ``{name}.rate_7d.{key}``: 7-day rate of change

        Merges into *base_context* (or new dict).
        """
        ctx = dict(base_context) if base_context else {}

        for name, timeline in self._timelines.items():
            if not timeline:
                continue

            # Determine keys from the latest snapshot
            latest_snap = timeline.latest()
            if latest_snap is None or not isinstance(latest_snap.value, dict):
                continue

            keys = list(latest_snap.value.keys())

            # --- Latest values ---
            for key in keys:
                val = latest_snap.value.get(key)
                if val is not None:
                    ctx[f"{name}.latest.{key}"] = val

            # --- Moving averages + trends + rates ---
            for window_label, window_td in _WINDOWS.items():
                for key in keys:
                    avg = moving_average(timeline, key, window_td)
                    if avg is not None:
                        ctx[f"{name}.moving_avg_{window_label}.{key}"] = round(avg, 4)

                    trend = detect_trend(timeline, key, window_td)
                    if trend != "unknown":
                        ctx[f"{name}.trend_{window_label}.{key}"] = trend

                    rate = rate_of_change(timeline, key, window_td)
                    if rate is not None:
                        ctx[f"{name}.rate_{window_label}.{key}"] = round(rate, 4)

            # --- Ledger event counts (if ledger attached) ---
            if self._ledger is not None:
                for window_label, window_td in _WINDOWS.items():
                    events = self._ledger.query(after=latest_snap.timestamp - window_td)
                    ctx[f"ledger.event_count_{window_label}"] = len(events)

        return ctx

    def evaluate_feature(self, feature_spec: str) -> Any:
        """Evaluate a single feature spec like ``'dosha.moving_avg_14d.vata'``.

        Used for ad-hoc queries outside the constraint pipeline.
        Returns ``None`` if the feature cannot be resolved.
        """
        parts = feature_spec.split(".", 2)
        if len(parts) < 3:
            return None

        timeline_name = parts[0]
        feature_type = parts[1]
        key = parts[2]

        timeline = self._timelines.get(timeline_name)
        if timeline is None or not timeline:
            return None

        if feature_type.startswith("latest"):
            snap = timeline.latest()
            if snap is None or not isinstance(snap.value, dict):
                return None
            return snap.value.get(key)

        if feature_type.startswith("moving_avg_"):
            window_label = feature_type.replace("moving_avg_", "")
            window_td = _WINDOWS.get(window_label)
            if window_td is None:
                return None
            return moving_average(timeline, key, window_td)

        if feature_type.startswith("trend_"):
            window_label = feature_type.replace("trend_", "")
            window_td = _WINDOWS.get(window_label)
            if window_td is None:
                return None
            result = detect_trend(timeline, key, window_td)
            return result if result != "unknown" else None

        if feature_type.startswith("rate_"):
            window_label = feature_type.replace("rate_", "")
            window_td = _WINDOWS.get(window_label)
            if window_td is None:
                return None
            return rate_of_change(timeline, key, window_td)

        return None
