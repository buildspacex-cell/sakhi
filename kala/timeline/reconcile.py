"""State reconciliation — merge conflicting snapshots from multiple sources.

When multiple systems produce observations of the same state at similar
times (e.g. journal-derived dosha vs body-derived dosha), reconciliation
merges them into a single consensus snapshot.

Pure computation — no DB, no LLM.
"""

from __future__ import annotations

from typing import Any

from kala.timeline.core import Snapshot


def reconcile_snapshots(
    snapshots: list[Snapshot[dict[str, float]]],
    strategy: str = "confidence_weighted",
) -> dict[str, float]:
    """Merge multiple snapshots into a single consensus dict.

    Strategies:

    * ``"confidence_weighted"`` — weight each snapshot's values by its
      confidence score, then normalise.
    * ``"latest_wins"`` — take the most recent snapshot's values.
    * ``"average"`` — simple unweighted mean across all snapshots.

    Returns an empty dict if *snapshots* is empty.
    """
    if not snapshots:
        return {}

    if strategy == "latest_wins":
        return dict(_latest_wins(snapshots))

    if strategy == "average":
        return _average(snapshots)

    # Default: confidence_weighted
    return _confidence_weighted(snapshots)


def detect_conflict(
    snapshots: list[Snapshot[dict[str, float]]],
    threshold: float = 0.3,
) -> list[str]:
    """Identify keys where snapshots disagree beyond *threshold*.

    For each key present in any snapshot, computes the spread
    (max − min).  Returns the list of keys whose spread exceeds
    *threshold*.
    """
    if len(snapshots) < 2:
        return []

    all_keys: set[str] = set()
    for s in snapshots:
        if isinstance(s.value, dict):
            all_keys.update(k for k, v in s.value.items() if _is_numeric(v))

    conflicts: list[str] = []
    for key in sorted(all_keys):
        values = [
            float(s.value[key])
            for s in snapshots
            if isinstance(s.value, dict) and key in s.value and _is_numeric(s.value[key])
        ]
        if len(values) < 2:
            continue
        spread = max(values) - min(values)
        if spread > threshold:
            conflicts.append(key)

    return conflicts


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------


def _confidence_weighted(snapshots: list[Snapshot[dict[str, float]]]) -> dict[str, float]:
    """Weight values by confidence, then normalise per key."""
    all_keys: set[str] = set()
    for s in snapshots:
        if isinstance(s.value, dict):
            all_keys.update(k for k, v in s.value.items() if _is_numeric(v))

    result: dict[str, float] = {}
    for key in all_keys:
        weighted_sum = 0.0
        weight_total = 0.0
        for s in snapshots:
            if not isinstance(s.value, dict):
                continue
            val = s.value.get(key)
            if val is not None and _is_numeric(val):
                w = max(s.confidence, 0.01)  # Avoid zero weight
                weighted_sum += float(val) * w
                weight_total += w
        if weight_total > 0:
            result[key] = round(weighted_sum / weight_total, 4)

    return result


def _latest_wins(snapshots: list[Snapshot[dict[str, float]]]) -> dict[str, float]:
    """Return the values from the most recent snapshot."""
    latest = max(snapshots, key=lambda s: s.timestamp)
    if isinstance(latest.value, dict):
        return {k: float(v) for k, v in latest.value.items() if _is_numeric(v)}
    return {}


def _average(snapshots: list[Snapshot[dict[str, float]]]) -> dict[str, float]:
    """Simple unweighted mean across all snapshots."""
    all_keys: set[str] = set()
    for s in snapshots:
        if isinstance(s.value, dict):
            all_keys.update(k for k, v in s.value.items() if _is_numeric(v))

    result: dict[str, float] = {}
    for key in all_keys:
        values = [
            float(s.value[key])
            for s in snapshots
            if isinstance(s.value, dict) and key in s.value and _is_numeric(s.value[key])
        ]
        if values:
            result[key] = round(sum(values) / len(values), 4)

    return result


def _is_numeric(val: Any) -> bool:
    """Check if a value can be converted to float."""
    try:
        float(val)
        return True
    except (TypeError, ValueError):
        return False
