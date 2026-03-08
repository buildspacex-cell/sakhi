"""Generic temporal arc data types.

Arc primitives are domain-agnostic temporal structures built from ordered items.
They carry no product-specific semantics beyond grouping, ordering, and derived
shape features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Mapping, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ArcPhase(Generic[T]):
    """A deterministic phase slice inside a temporal arc."""

    index: int
    start_ts: datetime
    end_ts: datetime
    elements: tuple[T, ...]
    stats: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArcFeatures:
    """Shape features extracted from an arc."""

    direction: str
    stability: float
    oscillation: float
    momentum: float | None
    average_rate: float | None
    density: float | None
    change_points: tuple[int, ...] = ()


@dataclass(frozen=True)
class TemporalArc(Generic[T]):
    """Ordered slice of related items that forms a continuity arc."""

    id: str
    key: str
    start_ts: datetime
    end_ts: datetime
    elements: tuple[T, ...]
    phases: tuple[ArcPhase[T], ...] = ()
    features: ArcFeatures | None = None
