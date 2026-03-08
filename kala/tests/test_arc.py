"""Tests for domain-agnostic temporal arc primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from kala.arc import build_arcs, extract_arc_features, segment_arc, summarize_arc_structure

_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class _Item:
    ref: str
    key: str
    ts: datetime
    score: float | None = None


class TestBuildArcs:
    def test_splits_on_max_gap(self) -> None:
        items = [
            _Item("a", "career", _BASE + timedelta(days=0), 0.2),
            _Item("b", "career", _BASE + timedelta(days=5), 0.4),
            _Item("c", "career", _BASE + timedelta(days=30), 0.6),
            _Item("d", "career", _BASE + timedelta(days=35), 0.7),
        ]
        arcs = build_arcs(
            items,
            get_ts=lambda item: item.ts,
            get_group_key=lambda item: item.key,
            get_ref=lambda item: item.ref,
            max_gap=timedelta(days=10),
            min_len=2,
        )
        assert len(arcs) == 2
        assert [len(arc.elements) for arc in arcs] == [2, 2]

    def test_ids_are_deterministic(self) -> None:
        items = [
            _Item("a", "career", _BASE + timedelta(days=0), 0.2),
            _Item("b", "career", _BASE + timedelta(days=1), 0.4),
            _Item("c", "career", _BASE + timedelta(days=2), 0.6),
        ]
        first = build_arcs(
            items,
            get_ts=lambda item: item.ts,
            get_group_key=lambda item: item.key,
            get_ref=lambda item: item.ref,
            max_gap=timedelta(days=10),
        )
        second = build_arcs(
            list(reversed(items)),
            get_ts=lambda item: item.ts,
            get_group_key=lambda item: item.key,
            get_ref=lambda item: item.ref,
            max_gap=timedelta(days=10),
        )
        assert len(first) == len(second) == 1
        assert first[0].id == second[0].id


class TestSegmentArc:
    def test_quantile_segmentation(self) -> None:
        items = [
            _Item(str(idx), "career", _BASE + timedelta(days=idx), float(idx))
            for idx in range(6)
        ]
        arc = build_arcs(
            items,
            get_ts=lambda item: item.ts,
            get_group_key=lambda item: item.key,
            get_ref=lambda item: item.ref,
            max_gap=timedelta(days=10),
        )[0]
        segmented = segment_arc(
            arc,
            method="quantile",
            k=3,
            get_ts=lambda item: item.ts,
            get_scalar=lambda item: item.score,
        )
        assert len(segmented.phases) == 3
        assert [len(phase.elements) for phase in segmented.phases] == [2, 2, 2]


class TestFeatures:
    def test_extract_features_with_scalar(self) -> None:
        items = [
            _Item("a", "career", _BASE + timedelta(days=0), 0.2),
            _Item("b", "career", _BASE + timedelta(days=3), 0.5),
            _Item("c", "career", _BASE + timedelta(days=6), 0.8),
        ]
        arc = build_arcs(
            items,
            get_ts=lambda item: item.ts,
            get_group_key=lambda item: item.key,
            get_ref=lambda item: item.ref,
            max_gap=timedelta(days=10),
        )[0]
        features = extract_arc_features(
            arc,
            get_ts=lambda item: item.ts,
            get_scalar=lambda item: item.score,
        )
        assert features.direction == "rising"
        assert features.average_rate is not None
        assert features.density is not None

    def test_summary_is_structure_only(self) -> None:
        items = [
            _Item("a", "career", _BASE + timedelta(days=0), 0.2),
            _Item("b", "career", _BASE + timedelta(days=1), 0.1),
            _Item("c", "career", _BASE + timedelta(days=2), 0.3),
        ]
        arc = build_arcs(
            items,
            get_ts=lambda item: item.ts,
            get_group_key=lambda item: item.key,
            get_ref=lambda item: item.ref,
            max_gap=timedelta(days=10),
        )[0]
        arc = segment_arc(
            arc,
            get_ts=lambda item: item.ts,
            get_scalar=lambda item: item.score,
        )
        arc = arc.__class__(
            id=arc.id,
            key=arc.key,
            start_ts=arc.start_ts,
            end_ts=arc.end_ts,
            elements=arc.elements,
            phases=arc.phases,
            features=extract_arc_features(arc, get_ts=lambda item: item.ts, get_scalar=lambda item: item.score),
        )
        summary = summarize_arc_structure(arc)
        assert summary["key"] == "career"
        assert summary["element_count"] == 3
        assert summary["features"]["direction"] in {"rising", "falling", "flat"}
        assert "story" not in summary
