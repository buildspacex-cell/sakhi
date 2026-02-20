"""Core timeline types — Snapshot and Timeline.

``Snapshot[T]`` is a timestamped state observation.
``Timeline[T]`` is an ordered sequence of snapshots with temporal queries.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, order=False)
class Snapshot(Generic[T]):
    """A timestamped state observation.

    Attributes:
        timestamp: When the observation was recorded (UTC).
        value: The observed state.
        confidence: Confidence in the observation (0.0–1.0).
        source: Identifier of the system that produced this snapshot.
    """

    timestamp: datetime
    value: T
    confidence: float = 1.0
    source: str = ""

    def __lt__(self, other: Snapshot[T]) -> bool:  # type: ignore[override]
        return self.timestamp < other.timestamp

    def __le__(self, other: Snapshot[T]) -> bool:  # type: ignore[override]
        return self.timestamp <= other.timestamp


class Timeline(Generic[T]):
    """Ordered sequence of timestamped state snapshots.

    The fundamental temporal primitive.  Stores ``Snapshot[T]`` objects
    in chronological order and supports temporal queries.

    Not thread-safe — callers must synchronise externally if needed.
    """

    def __init__(self, snapshots: list[Snapshot[T]] | None = None) -> None:
        self._snapshots: list[Snapshot[T]] = sorted(snapshots or [])

    # -- Mutation -----------------------------------------------------------

    def add(self, snapshot: Snapshot[T]) -> None:
        """Insert a snapshot in chronological order (O(log n))."""
        bisect.insort(self._snapshots, snapshot)

    # -- Queries ------------------------------------------------------------

    def at(self, t: datetime) -> Snapshot[T] | None:
        """Return the latest snapshot whose timestamp is ≤ *t*, or ``None``."""
        if not self._snapshots:
            return None
        # Binary search for the rightmost snapshot ≤ t
        idx = bisect.bisect_right(
            self._snapshots,
            Snapshot(timestamp=t, value=None),  # type: ignore[arg-type]
        )
        if idx == 0:
            return None
        return self._snapshots[idx - 1]

    def between(self, start: datetime, end: datetime) -> list[Snapshot[T]]:
        """Return all snapshots with ``start ≤ timestamp < end``."""
        lo = bisect.bisect_left(
            self._snapshots,
            Snapshot(timestamp=start, value=None),  # type: ignore[arg-type]
        )
        hi = bisect.bisect_left(
            self._snapshots,
            Snapshot(timestamp=end, value=None),  # type: ignore[arg-type]
        )
        return self._snapshots[lo:hi]

    def window(self, duration: timedelta) -> list[Snapshot[T]]:
        """Return snapshots within the last *duration* from the latest entry."""
        if not self._snapshots:
            return []
        end = self._snapshots[-1].timestamp
        start = end - duration
        return self.between(start, end + timedelta(microseconds=1))

    def latest(self) -> Snapshot[T] | None:
        """Return the most recent snapshot, or ``None`` if empty."""
        return self._snapshots[-1] if self._snapshots else None

    def earliest(self) -> Snapshot[T] | None:
        """Return the oldest snapshot, or ``None`` if empty."""
        return self._snapshots[0] if self._snapshots else None

    # -- Dunder helpers -----------------------------------------------------

    def __len__(self) -> int:
        return len(self._snapshots)

    def __bool__(self) -> bool:
        return bool(self._snapshots)

    def __iter__(self) -> Iterator[Snapshot[T]]:
        return iter(self._snapshots)

    def __repr__(self) -> str:
        count = len(self._snapshots)
        if count == 0:
            return "Timeline(empty)"
        first = self._snapshots[0].timestamp.isoformat()
        last = self._snapshots[-1].timestamp.isoformat()
        return f"Timeline({count} snapshots, {first} → {last})"
