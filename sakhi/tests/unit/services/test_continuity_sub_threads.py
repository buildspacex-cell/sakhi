"""Unit tests for sub-thread detection logic in simulation_continuity.

Tests cover:
- _classify_sub_thread_stage: stage assignment given moment/day/stake counts
- _detect_stake_types: stake inference from facet name + moment data
- _detect_sub_threads: end-to-end grouping + stage classification
"""
from __future__ import annotations

import pytest

from sakhi.apps.api.services.demo.simulation_continuity import (
    _classify_sub_thread_stage,
    _detect_stake_types,
    _detect_sub_threads,
)


# ---------------------------------------------------------------------------
# _classify_sub_thread_stage
# ---------------------------------------------------------------------------


def test_stage_mention_single_occurrence():
    stage = _classify_sub_thread_stage(moment_count=1, distinct_days=1, stake_types=[])
    assert stage == "mention"


def test_stage_candidate_two_moments_same_day():
    stage = _classify_sub_thread_stage(moment_count=2, distinct_days=1, stake_types=["planning_logistics"])
    assert stage == "candidate_sub_thread"


def test_stage_candidate_two_moments_no_stakes():
    stage = _classify_sub_thread_stage(moment_count=2, distinct_days=2, stake_types=[])
    # Meets day count but not moment threshold (visible requires >= 3)
    assert stage == "candidate_sub_thread"


def test_stage_visible_meets_all_thresholds():
    stage = _classify_sub_thread_stage(
        moment_count=3,
        distinct_days=2,
        stake_types=["planning_logistics"],
    )
    assert stage == "visible_sub_thread"


def test_stage_visible_with_multiple_stakes():
    stage = _classify_sub_thread_stage(
        moment_count=5,
        distinct_days=3,
        stake_types=["emotional_charge", "tradeoff"],
    )
    assert stage == "visible_sub_thread"


def test_stage_below_visible_day_threshold():
    # 4 moments but only 1 day → candidate, not visible
    stage = _classify_sub_thread_stage(moment_count=4, distinct_days=1, stake_types=["identity_signal"])
    assert stage == "candidate_sub_thread"


def test_stage_below_visible_moment_threshold():
    # 2 moments across 3 days with stakes → still candidate (not enough moments)
    stage = _classify_sub_thread_stage(moment_count=2, distinct_days=3, stake_types=["emotional_charge"])
    assert stage == "candidate_sub_thread"


# ---------------------------------------------------------------------------
# _detect_stake_types
# ---------------------------------------------------------------------------


def test_stake_planning_from_decision_state():
    moments = [
        {"decision_state": "questioning", "stance": "unclear", "related_anchors": []},
        {"decision_state": "questioning", "stance": "unclear", "related_anchors": []},
    ]
    stakes = _detect_stake_types("parenting", moments)
    assert "planning_logistics" in stakes


def test_stake_planning_committed():
    moments = [
        {"decision_state": "committed", "stance": "toward", "related_anchors": []},
    ]
    stakes = _detect_stake_types("workload", moments)
    assert "planning_logistics" in stakes


def test_stake_emotional_from_facet_name():
    moments = [
        {"decision_state": "resolved", "stance": "toward", "related_anchors": []},
    ]
    stakes = _detect_stake_types("grief", moments)
    assert "emotional_charge" in stakes


def test_stake_emotional_from_stance_away():
    moments = [
        {"decision_state": "leaning_no", "stance": "away", "related_anchors": []},
        {"decision_state": "leaning_no", "stance": "away", "related_anchors": []},
    ]
    stakes = _detect_stake_types("family_pull", moments)
    assert "emotional_charge" in stakes


def test_stake_identity_from_facet_name():
    moments = [
        {"decision_state": "resolved", "stance": "toward", "related_anchors": []},
    ]
    stakes = _detect_stake_types("identity", moments)
    assert "identity_signal" in stakes


def test_stake_identity_leadership():
    moments = [
        {"decision_state": "committed", "stance": "toward", "related_anchors": []},
    ]
    stakes = _detect_stake_types("leadership", moments)
    assert "identity_signal" in stakes


def test_stake_tradeoff_from_related_anchors():
    moments = [
        {"decision_state": "questioning", "stance": "unclear", "related_anchors": [{"anchor": "career", "score": 0.7}]},
    ]
    stakes = _detect_stake_types("parenting", moments)
    assert "tradeoff" in stakes


def test_stake_no_stakes_neutral_facet():
    moments = [
        {"decision_state": "resolved", "stance": "toward", "related_anchors": []},
    ]
    stakes = _detect_stake_types("discipline", moments)
    # discipline has no emotional/identity keywords and stance is toward
    assert "tradeoff" not in stakes
    assert "planning_logistics" not in stakes


# ---------------------------------------------------------------------------
# _detect_sub_threads — end-to-end
# ---------------------------------------------------------------------------


def _make_event_refs(*facets_and_days: tuple[str, int]) -> list[dict]:
    """Build minimal event_refs: (facet, day) → event_ref entry."""
    refs = []
    for idx, (facet, day) in enumerate(facets_and_days):
        ts = f"2026-01-{day:02d}T10:00:00+00:00"
        refs.append({
            "facet": facet,
            "day": day,
            "ts": ts,
            "source_ref": f"journal:entry-{idx}",
            "decision_state": "questioning",
            "stance": "unclear",
        })
    return refs


def _make_entry_tags(event_refs: list[dict], related_anchors_by_ref: dict | None = None) -> dict:
    """Build minimal entry_tags keyed by 'day|ts'."""
    tags = {}
    for ref in event_refs:
        key = f"{int(ref['day'])}|{ref['ts']}"
        src_ref = ref.get("source_ref", "")
        tags[key] = {
            "facet": ref["facet"],
            "decision_state": ref["decision_state"],
            "stance": ref["stance"],
            "related_anchors": (related_anchors_by_ref or {}).get(src_ref, []),
        }
    return tags


def test_detect_sub_threads_single_mention():
    refs = _make_event_refs(("parenting", 1))
    tags = _make_entry_tags(refs)
    result = _detect_sub_threads(tags, refs)
    assert len(result) == 1
    assert result[0]["facet"] == "parenting"
    assert result[0]["stage"] == "mention"
    assert result[0]["moment_count"] == 1


def test_detect_sub_threads_candidate_two_same_day():
    refs = _make_event_refs(("parenting", 5), ("parenting", 5))
    tags = _make_entry_tags(refs)
    result = _detect_sub_threads(tags, refs)
    assert result[0]["stage"] == "candidate_sub_thread"
    assert result[0]["distinct_days"] == 1


def test_detect_sub_threads_visible_threshold_met():
    # 3 moments, 2 days, with planning stake (decision_state=questioning)
    refs = _make_event_refs(("parenting", 1), ("parenting", 3), ("parenting", 5))
    tags = _make_entry_tags(refs)
    result = _detect_sub_threads(tags, refs)
    assert result[0]["stage"] == "visible_sub_thread"
    assert result[0]["moment_count"] == 3
    assert result[0]["distinct_days"] == 3
    assert "planning_logistics" in result[0]["stake_types"]


def test_detect_sub_threads_ignores_unknown_facets():
    refs = _make_event_refs(("unknown", 1), ("", 2), ("parenting", 3))
    tags = _make_entry_tags(refs)
    result = _detect_sub_threads(tags, refs)
    # Only parenting should appear
    assert len(result) == 1
    assert result[0]["facet"] == "parenting"


def test_detect_sub_threads_multiple_facets_sorted():
    refs = _make_event_refs(
        ("parenting", 1), ("parenting", 2), ("parenting", 4),  # 3 moments, 3 days → visible
        ("discipline", 1),                                     # 1 moment → mention
        ("grief", 3), ("grief", 5),                           # 2 moments, 2 days → candidate
    )
    tags = _make_entry_tags(refs)
    result = _detect_sub_threads(tags, refs)
    stages = [st["stage"] for st in result]
    # visible comes first
    assert stages[0] == "visible_sub_thread"
    assert "candidate_sub_thread" in stages
    assert "mention" in stages


def test_detect_sub_threads_empty_inputs():
    assert _detect_sub_threads({}, []) == []


def test_detect_sub_threads_entry_refs_populated():
    refs = _make_event_refs(("parenting", 1), ("parenting", 2))
    tags = _make_entry_tags(refs)
    result = _detect_sub_threads(tags, refs)
    assert len(result[0]["entry_refs"]) == 2
    assert all(ref.startswith("journal:") for ref in result[0]["entry_refs"])


def test_detect_sub_threads_tradeoff_stake_from_related_anchors():
    refs = _make_event_refs(("parenting", 1), ("parenting", 2), ("parenting", 4))
    related = {"journal:entry-0": [{"anchor": "career", "score": 0.7}]}
    tags = _make_entry_tags(refs, related_anchors_by_ref=related)
    result = _detect_sub_threads(tags, refs)
    assert "tradeoff" in result[0]["stake_types"]
