"""Deterministic temporal arc construction and feature extraction."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Callable, Sequence, TypeVar

from kala.arc.core import ArcFeatures, ArcPhase, TemporalArc

T = TypeVar("T")


def build_arcs(
    items: Sequence[T],
    *,
    get_ts: Callable[[T], datetime],
    get_group_key: Callable[[T], str],
    get_ref: Callable[[T], str] | None = None,
    max_gap: timedelta,
    min_len: int = 3,
) -> list[TemporalArc[T]]:
    """Group items into deterministic arcs using key + max_gap splitting."""
    grouped: dict[str, list[T]] = defaultdict(list)
    for item in items:
        grouped[get_group_key(item)].append(item)

    arcs: list[TemporalArc[T]] = []
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=get_ts)
        if not ordered:
            continue

        current: list[T] = [ordered[0]]
        for item in ordered[1:]:
            prev_ts = get_ts(current[-1])
            item_ts = get_ts(item)
            if item_ts - prev_ts > max_gap:
                arc = _make_arc(key, current, get_ts=get_ts, get_ref=get_ref)
                if len(arc.elements) >= min_len:
                    arcs.append(arc)
                current = [item]
            else:
                current.append(item)

        arc = _make_arc(key, current, get_ts=get_ts, get_ref=get_ref)
        if len(arc.elements) >= min_len:
            arcs.append(arc)

    arcs.sort(key=lambda arc: (arc.start_ts, arc.key, arc.id))
    return arcs


def segment_arc(
    arc: TemporalArc[T],
    *,
    method: str = "quantile",
    k: int = 3,
    get_ts: Callable[[T], datetime],
    get_scalar: Callable[[T], float | None] | None = None,
) -> TemporalArc[T]:
    """Attach deterministic phase slices to an arc."""
    if not arc.elements:
        return arc

    if k <= 1 or len(arc.elements) <= 1:
        phases = (
            ArcPhase(index=0, start_ts=arc.start_ts, end_ts=arc.end_ts, elements=arc.elements),
        )
        return replace(arc, phases=phases)

    if method == "change_point":
        bounds = _change_point_bounds(arc.elements, k=k, get_scalar=get_scalar)
    elif method == "quantile":
        bounds = _quantile_bounds(len(arc.elements), k=k)
    else:
        raise ValueError(f"Unsupported segmentation method: {method}")

    phases: list[ArcPhase[T]] = []
    for index, (start_idx, end_idx) in enumerate(bounds):
        phase_elements = arc.elements[start_idx:end_idx]
        if not phase_elements:
            continue
        phase_start = get_ts(phase_elements[0])
        phase_end = get_ts(phase_elements[-1])
        stats = {
            "element_count": len(phase_elements),
        }
        if get_scalar is not None:
            scalar_values = [get_scalar(item) for item in phase_elements]
            scalar_values = [float(v) for v in scalar_values if v is not None]
            if scalar_values:
                stats = {
                    **stats,
                    "scalar_min": round(min(scalar_values), 4),
                    "scalar_max": round(max(scalar_values), 4),
                    "scalar_avg": round(sum(scalar_values) / len(scalar_values), 4),
                }
        phases.append(
            ArcPhase(
                index=index,
                start_ts=phase_start,
                end_ts=phase_end,
                elements=tuple(phase_elements),
                stats=stats,
            )
        )

    return replace(arc, phases=tuple(phases))


def extract_arc_features(
    arc: TemporalArc[T],
    *,
    get_ts: Callable[[T], datetime],
    get_scalar: Callable[[T], float | None] | None = None,
) -> ArcFeatures:
    """Compute deterministic shape features for an arc."""
    count = len(arc.elements)
    if count == 0:
        return ArcFeatures(
            direction="flat",
            stability=1.0,
            oscillation=0.0,
            momentum=None,
            average_rate=None,
            density=0.0,
            change_points=(),
        )

    span_days = max((arc.end_ts - arc.start_ts).total_seconds() / 86400, 0.0)
    density = round(count / max(span_days, 1.0), 4)

    scalar_values: list[float] = []
    if get_scalar is not None:
        scalar_values = [float(v) for v in (get_scalar(item) for item in arc.elements) if v is not None]

    if len(scalar_values) >= 2:
        deltas = [b - a for a, b in zip(scalar_values, scalar_values[1:])]
        total_delta = scalar_values[-1] - scalar_values[0]
        threshold = max(0.05, abs(scalar_values[0]) * 0.05)
        if total_delta > threshold:
            direction = "rising"
        elif total_delta < -threshold:
            direction = "falling"
        else:
            direction = "flat"

        sign_changes = 0
        prev_sign = 0
        for delta in deltas:
            sign = 1 if delta > 0 else -1 if delta < 0 else 0
            if sign and prev_sign and sign != prev_sign:
                sign_changes += 1
            if sign:
                prev_sign = sign
        oscillation = round(sign_changes / max(len(deltas), 1), 4)

        avg_abs_delta = mean(abs(delta) for delta in deltas)
        value_span = max(max(scalar_values) - min(scalar_values), 1e-6)
        stability = round(max(0.0, min(1.0, 1.0 - (avg_abs_delta / value_span))), 4)

        average_rate = None
        momentum = None
        if span_days > 0:
            average_rate = round(total_delta / span_days, 4)
            momentum = average_rate

        change_points = _top_scalar_jump_indexes(scalar_values)
    else:
        gaps = [
            max((get_ts(b) - get_ts(a)).total_seconds() / 86400, 0.0)
            for a, b in zip(arc.elements, arc.elements[1:])
        ]
        direction = "flat"
        if gaps:
            avg_gap = mean(gaps)
            gap_span = max(max(gaps) - min(gaps), 1e-6)
            stability = round(max(0.0, min(1.0, 1.0 - (gap_span / max(avg_gap, 1e-6, gap_span)))), 4)
        else:
            stability = 1.0
        oscillation = 0.0
        average_rate = None
        momentum = None
        change_points = ()

    return ArcFeatures(
        direction=direction,
        stability=stability,
        oscillation=oscillation,
        momentum=momentum,
        average_rate=average_rate,
        density=density,
        change_points=change_points,
    )


def summarize_arc_structure(arc: TemporalArc[Any]) -> dict[str, Any]:
    """Return a structure-only summary for downstream apps."""
    features = arc.features
    phases = [
        {
            "index": phase.index,
            "start_ts": phase.start_ts.isoformat(),
            "end_ts": phase.end_ts.isoformat(),
            "element_count": len(phase.elements),
            "stats": dict(phase.stats),
        }
        for phase in arc.phases
    ]
    return {
        "id": arc.id,
        "key": arc.key,
        "start_ts": arc.start_ts.isoformat(),
        "end_ts": arc.end_ts.isoformat(),
        "span_days": round(max((arc.end_ts - arc.start_ts).total_seconds() / 86400, 0.0), 4),
        "element_count": len(arc.elements),
        "phase_count": len(phases),
        "phases": phases,
        "features": {
            "direction": features.direction,
            "stability": features.stability,
            "oscillation": features.oscillation,
            "momentum": features.momentum,
            "average_rate": features.average_rate,
            "density": features.density,
            "change_points": list(features.change_points),
        } if features is not None else None,
    }


def _make_arc(
    key: str,
    items: Sequence[T],
    *,
    get_ts: Callable[[T], datetime],
    get_ref: Callable[[T], str] | None,
) -> TemporalArc[T]:
    ordered = tuple(sorted(items, key=get_ts))
    start_ts = get_ts(ordered[0])
    end_ts = get_ts(ordered[-1])
    refs = [get_ref(item) for item in ordered] if get_ref is not None else [f"{idx}:{get_ts(item).isoformat()}" for idx, item in enumerate(ordered)]
    digest = hashlib.sha256(
        json.dumps(
            {
                "key": key,
                "start_ts": start_ts.isoformat(),
                "end_ts": end_ts.isoformat(),
                "refs": refs,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return TemporalArc(
        id=f"arc_{digest}",
        key=key,
        start_ts=start_ts,
        end_ts=end_ts,
        elements=ordered,
    )


def _quantile_bounds(length: int, *, k: int) -> list[tuple[int, int]]:
    bucket_count = max(1, min(k, length))
    bounds: list[tuple[int, int]] = []
    last = 0
    for index in range(bucket_count):
        boundary = math.ceil((index + 1) * length / bucket_count)
        bounds.append((last, boundary))
        last = boundary
    return bounds


def _change_point_bounds(
    items: Sequence[T],
    *,
    k: int,
    get_scalar: Callable[[T], float | None] | None,
) -> list[tuple[int, int]]:
    if get_scalar is None or len(items) <= 2:
        return _quantile_bounds(len(items), k=k)

    scalar_values = [get_scalar(item) for item in items]
    if any(value is None for value in scalar_values):
        return _quantile_bounds(len(items), k=k)

    jumps = [abs(float(b) - float(a)) for a, b in zip(scalar_values, scalar_values[1:])]
    if not jumps:
        return _quantile_bounds(len(items), k=k)

    boundary_indexes = sorted(
        idx + 1
        for idx, _ in sorted(
            enumerate(jumps),
            key=lambda pair: (-pair[1], pair[0]),
        )[: max(0, min(k - 1, len(jumps)))]
    )
    if not boundary_indexes:
        return _quantile_bounds(len(items), k=k)

    bounds: list[tuple[int, int]] = []
    start = 0
    for boundary in boundary_indexes:
        bounds.append((start, boundary))
        start = boundary
    bounds.append((start, len(items)))
    return bounds


def _top_scalar_jump_indexes(values: Sequence[float], limit: int = 2) -> tuple[int, ...]:
    jumps = [(idx + 1, abs(b - a)) for idx, (a, b) in enumerate(zip(values, values[1:]))]
    if not jumps:
        return ()
    ranked = sorted(jumps, key=lambda pair: (-pair[1], pair[0]))[:limit]
    return tuple(sorted(index for index, magnitude in ranked if magnitude > 0))
