"""Simulation continuity compilation and ad-hoc arc building.

This module has two responsibilities:
1. Compile stable continuity topics from simulation journal entries so the
   simulation artifact can ship with precomputed continuity intelligence.
2. Support ad-hoc demo-scoped arc construction over a caller-supplied set of
   entries when needed.

Kala owns the actual temporal arc computation. This module only maps simulation
entries into deterministic continuity structures.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from kala.arc import build_arcs, extract_arc_features, segment_arc, summarize_arc_structure
from sakhi.apps.api.services.continuity.taxonomy import SIMULATION_CONTINUITY_TAXONOMY
from sakhi.apps.api.services.continuity.thread_resolver import resolve_thread_attachments
from sakhi.apps.api.services.continuity.thresholds import (
    SIMULATION_CONTINUITY_THRESHOLD_PROFILE,
)

VALID_DECISION_STATES = {
    "questioning",
    "leaning_yes",
    "leaning_no",
    "committed",
    "deferred",
    "reversed",
    "resolved",
}
VALID_STANCES = {"toward", "away", "unclear"}

_TAXONOMY = SIMULATION_CONTINUITY_TAXONOMY
_THRESHOLDS = SIMULATION_CONTINUITY_THRESHOLD_PROFILE
_ALIAS_BOOST = 0.85
COMPILER_VERSION = "2026.03.18.1"


def _canonicalize_anchor(anchor: str) -> str:
    return re.sub(r"\s+", "_", (anchor or "").strip().lower())


class ClassificationState(str, Enum):
    CONFIDENT = "CONFIDENT"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CandidateScore:
    key: str
    score: float
    hits: tuple[str, ...]
    negative_hits: tuple[str, ...]
    priority: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "score": round(float(self.score), 4),
            "hits": list(self.hits),
            "negative_hits": list(self.negative_hits),
            "priority": self.priority,
        }


@dataclass(frozen=True)
class ClassificationTrace:
    state: ClassificationState
    threshold_profile_version: str
    winner: CandidateScore | None
    runner_up: CandidateScore | None
    threshold_used: float
    margin_used: float
    fallback_reason: str | None
    candidates: tuple[CandidateScore, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "threshold_profile_version": self.threshold_profile_version,
            "winner": self.winner.as_dict() if self.winner else None,
            "runner_up": self.runner_up.as_dict() if self.runner_up else None,
            "threshold_used": round(float(self.threshold_used), 4),
            "margin_used": round(float(self.margin_used), 4),
            "fallback_reason": self.fallback_reason,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
        }

def _parse_ts(raw: Any) -> datetime:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Each continuity entry requires a timestamp")
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid continuity timestamp: {raw}") from exc
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _compiled_entry_key(day: Any, timestamp: Any) -> str:
    return f"{int(day)}|{str(timestamp)}"


def _normalize_items(
    *,
    persona_id: str,
    anchor: str,
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        ts = _parse_ts(entry.get("timestamp"))
        content = str(entry.get("content") or "").strip()
        if not content:
            raise ValueError("Each continuity entry requires content")
        try:
            day = int(entry.get("day"))
        except Exception as exc:
            raise ValueError("Each continuity entry requires a numeric day") from exc

        time_of_day = str(entry.get("time_of_day") or "")
        facet = _normalize_token(entry.get("facet"))
        decision_state = _normalize_token(entry.get("decision_state"))
        stance = _normalize_token(entry.get("stance"))
        anchor_state = _normalize_state(entry.get("anchor_state"))
        facet_state = _normalize_state(entry.get("facet_state"))
        source_type = _normalize_token(entry.get("source_type")) or "simulation"
        source_id = str(entry.get("source_id") or f"{day}:{index}").strip()
        source_ref = str(entry.get("source_ref") or "").strip() or (
            f"{source_type}:{persona_id}:{day}:{index}"
            if source_type == "simulation"
            else f"{source_type}:{source_id}"
        )

        if decision_state and decision_state not in VALID_DECISION_STATES:
            raise ValueError(f"Invalid decision_state: {decision_state}")
        if stance and stance not in VALID_STANCES:
            raise ValueError(f"Invalid stance: {stance}")

        scalar_raw = entry.get("scalar")
        scalar = _normalize_scalar(scalar_raw)
        if scalar is None:
            scalar = _derive_scalar(decision_state=decision_state, stance=stance)
        confidence = _normalize_scalar(entry.get("confidence"))
        facet_terms = entry.get("facet_terms")
        if not isinstance(facet_terms, list):
            facet_terms = []
        facet_terms = [str(term).strip() for term in facet_terms if str(term).strip()]
        matched_terms = entry.get("matched_terms")
        if not isinstance(matched_terms, list):
            matched_terms = []
        matched_terms = [str(term).strip() for term in matched_terms if str(term).strip()]
        trace = entry.get("trace")
        if not isinstance(trace, dict):
            trace = {}

        items.append(
            {
                "ts": ts,
                "anchor": anchor,
                "day": day,
                "content": content,
                "content_excerpt": content[:180],
                "time_of_day": time_of_day,
                "scalar": scalar,
                "facet": facet,
                "anchor_state": anchor_state,
                "facet_state": facet_state,
                "decision_state": decision_state,
                "stance": stance,
                "confidence": confidence,
                "facet_terms": facet_terms,
                "matched_terms": matched_terms,
                "trace": trace,
                "membership_role": str(entry.get("membership_role") or "primary"),
                "source_anchor": str(entry.get("source_anchor") or anchor),
                "source_type": source_type,
                "source_id": source_id,
                "source_ref": source_ref,
            }
        )

    items.sort(key=lambda item: (item["ts"], item["day"], item["source_ref"]))
    return items


def build_simulation_continuity_arc(
    *,
    persona_id: str,
    anchor: str,
    entries: list[dict[str, Any]],
    max_gap_days: int = 21,
    min_len: int = 3,
) -> dict[str, Any]:
    normalized_anchor = _canonicalize_anchor(anchor)
    if not normalized_anchor:
        raise ValueError("Anchor is required")
    if max_gap_days <= 0:
        raise ValueError("max_gap_days must be positive")
    if min_len <= 0:
        raise ValueError("min_len must be positive")

    items = _normalize_items(persona_id=persona_id, anchor=normalized_anchor, entries=entries)
    if len(items) < min_len:
        raise LookupError("Select at least 3 entries to form a continuity arc")

    arcs = build_arcs(
        items,
        get_ts=lambda item: item["ts"],
        get_group_key=lambda item: item["anchor"],
        get_ref=lambda item: item["source_ref"],
        max_gap=timedelta(days=max_gap_days),
        min_len=min_len,
    )
    if not arcs:
        raise LookupError("No continuity arc found for the selected entries")

    arc = max(arcs, key=lambda candidate: (len(candidate.elements), candidate.end_ts, candidate.id))
    arc = segment_arc(
        arc,
        method="quantile",
        k=3,
        get_ts=lambda item: item["ts"],
        get_scalar=lambda item: item.get("scalar"),
    )
    arc = _enrich_phase_stats(arc)
    features = extract_arc_features(
        arc,
        get_ts=lambda item: item["ts"],
        get_scalar=lambda item: item.get("scalar"),
    )
    arc = replace(arc, features=features)

    summary = summarize_arc_structure(arc)
    summary["phases"] = [
        {
            "index": phase.index,
            "start_ts": phase.start_ts.isoformat(),
            "end_ts": phase.end_ts.isoformat(),
            "start_day": phase.elements[0]["day"],
            "end_day": phase.elements[-1]["day"],
            "element_count": len(phase.elements),
            "stats": dict(phase.stats),
        }
        for phase in arc.phases
    ]
    summary["event_refs"] = [
        {
            "day": item["day"],
            "ts": item["ts"].isoformat(),
            "time_of_day": item["time_of_day"],
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "source_ref": item.get("source_ref"),
            "membership_role": item.get("membership_role"),
            "source_anchor": item.get("source_anchor"),
            "facet": item["facet"],
            "anchor_state": item.get("anchor_state"),
            "facet_state": item.get("facet_state"),
            "decision_state": item["decision_state"],
            "stance": item["stance"],
            "scalar": item["scalar"],
            "excerpt": item["content_excerpt"],
        }
        for item in arc.elements
    ]

    return {
        "persona_id": persona_id,
        "anchor": normalized_anchor,
        "selected_count": len(items),
        "arc": summary,
    }


def compile_simulation_continuity(
    *,
    persona_id: str,
    entries: list[dict[str, Any]],
    max_gap_days: int = 21,
    min_len: int = 3,
) -> dict[str, Any]:
    ordered_entries = [entry for entry in entries if isinstance(entry, dict)]
    ordered_entries.sort(key=lambda entry: (_safe_int(entry.get("day")), _parse_ts(entry.get("timestamp"))))
    inferred = [_classify_entry(entry) for entry in ordered_entries]

    # Phase 1: Thread-aware resolution for ambiguous/unknown entries
    inferred, unresolved_entries = resolve_thread_attachments(inferred)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in inferred:
        for membership in _topic_memberships_for_entry(item):
            anchor = str(membership.get("anchor") or "").strip()
            if anchor and anchor not in {"unknown", "life"}:
                grouped.setdefault(anchor, []).append(membership)

    topics: list[dict[str, Any]] = []
    for anchor, anchor_entries in grouped.items():
        if len(anchor_entries) < min_len:
            continue
        try:
            topics.append(
                _build_compiled_topic(
                    persona_id=persona_id,
                    anchor=anchor,
                    inferred_entries=anchor_entries,
                    max_gap_days=max_gap_days,
                    min_len=min_len,
                )
            )
        except LookupError:
            continue

    if not topics and len(ordered_entries) >= min_len:
        fallback_entries = [
            {
                "entry": entry,
                "anchor": "life",
                "anchor_score": 0.25,
                "anchor_hits": [],
                "stance_score": 0.0,
                "text": _normalize_text(str(entry.get("content") or "")),
            }
            for entry in ordered_entries
        ]
        try:
            topics.append(
                _build_compiled_topic(
                    persona_id=persona_id,
                    anchor="life",
                    inferred_entries=fallback_entries,
                    max_gap_days=max_gap_days,
                    min_len=min_len,
                )
            )
        except LookupError:
            pass

    topics.sort(
        key=lambda topic: (
            -int(topic.get("selected_count") or 0),
            -float((topic.get("surface") or {}).get("classification_score") or 0.0),
            str(topic.get("anchor") or ""),
        )
    )

    compiled_at = datetime.now(UTC).isoformat()

    return {
        "version": 2,
        "taxonomy_version": _TAXONOMY.version,
        "compiler_version": COMPILER_VERSION,
        "threshold_profile_version": _THRESHOLDS.version,
        "compiled_at": compiled_at,
        "generated_at": compiled_at,
        "inputs_hash": _compute_inputs_hash(
            persona_id=persona_id,
            entries=ordered_entries,
            max_gap_days=max_gap_days,
            min_len=min_len,
        ),
        "topics": topics,
        "unresolved_entries": [
            {
                "entry_id": str(e.get("entry", {}).get("id") or ""),
                "day": _safe_int(e.get("entry", {}).get("day")),
                "timestamp": str(e.get("entry", {}).get("timestamp") or ""),
                "content_preview": str(e.get("entry", {}).get("content") or "")[:100],
                "anchor_trace": e.get("anchor_trace", {}),
                "attachment_info": e.get("thread_attachment", {}),
            }
            for e in unresolved_entries
        ],
    }


def enrich_simulation_payload(
    sim_data: dict[str, Any],
    *,
    persona_id: str | None = None,
    max_gap_days: int = 21,
    min_len: int = 3,
) -> dict[str, Any]:
    resolved_persona_id = str(persona_id or sim_data.get("persona_id") or "").strip()
    if not resolved_persona_id:
        raise ValueError("persona_id is required to compile simulation continuity")

    entries = [entry for entry in (sim_data.get("entries") or []) if isinstance(entry, dict)]
    sim_data["continuity"] = compile_simulation_continuity(
        persona_id=resolved_persona_id,
        entries=entries,
        max_gap_days=max_gap_days,
        min_len=min_len,
    )
    return sim_data


def _build_compiled_topic(
    *,
    persona_id: str,
    anchor: str,
    inferred_entries: list[dict[str, Any]],
    max_gap_days: int,
    min_len: int,
) -> dict[str, Any]:
    annotated_entries = _annotate_topic_entries(anchor=anchor, inferred_entries=inferred_entries)
    arc_payload = [
        {
            "day": item["day"],
            "timestamp": item["timestamp"],
            "content": item["content"],
            "time_of_day": item["time_of_day"],
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "source_ref": item.get("source_ref"),
            "facet": item["facet"],
            "anchor_state": item["anchor_state"],
            "facet_state": item["facet_state"],
            "decision_state": item["decision_state"],
            "stance": item["stance"],
            "scalar": item["scalar"],
            "confidence": item["confidence"],
            "facet_terms": item.get("facet_terms") or [],
            "matched_terms": item.get("matched_terms") or [],
            "membership_role": item.get("membership_role") or "primary",
            "source_anchor": item.get("source_anchor"),
            "related_anchors": item.get("related_anchors") or [],
            "trace": item.get("trace") or {},
        }
        for item in annotated_entries
    ]
    built = build_simulation_continuity_arc(
        persona_id=persona_id,
        anchor=anchor,
        entries=arc_payload,
        max_gap_days=max_gap_days,
        min_len=min_len,
    )
    event_refs = built["arc"]["event_refs"]
    visible_keys = {_compiled_entry_key(ref["day"], ref["ts"]) for ref in event_refs}
    visible_days = [int(ref["day"]) for ref in event_refs]

    confidence_values = [
        float(item["confidence"])
        for item in annotated_entries
        if _compiled_entry_key(item["day"], item["timestamp"]) in visible_keys
    ]
    entry_tags = {
        _compiled_entry_key(item["day"], item["timestamp"]): {
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "source_ref": item.get("source_ref"),
            "facet": item["facet"],
            "anchor_state": item["anchor_state"],
            "facet_state": item["facet_state"],
            "decision_state": item["decision_state"],
            "stance": item["stance"],
            "scalar": item["scalar"],
            "confidence": item["confidence"],
            "membership_role": item.get("membership_role") or "primary",
            "source_anchor": item.get("source_anchor"),
            "related_anchors": item.get("related_anchors") or [],
            "matched_terms": list(item.get("matched_terms") or []),
            "trace": item.get("trace") or {},
        }
        for item in annotated_entries
        if _compiled_entry_key(item["day"], item["timestamp"]) in visible_keys
    }
    primary_selected_count = sum(
        1
        for item in annotated_entries
        if (
            _compiled_entry_key(item["day"], item["timestamp"]) in visible_keys
            and str(item.get("membership_role") or "primary") == "primary"
        )
    )
    related_selected_count = max(len(visible_days) - primary_selected_count, 0)
    topic = {
        "anchor": anchor,
        "label": _TAXONOMY.label_for(anchor),
        "confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
        "selected_count": len(visible_days),
        "primary_selected_count": primary_selected_count,
        "related_selected_count": related_selected_count,
        "entry_days": visible_days,
        "entry_tags": entry_tags,
        "arc": built["arc"],
    }
    topic["surface"] = _build_topic_surface(topic)
    return topic


def _infer_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return _classify_entry(entry)


def classify_simulation_entry(entry: dict[str, Any]) -> dict[str, Any]:
    inferred = _classify_entry(entry)
    return {
        "taxonomy_version": _TAXONOMY.version,
        "compiler_version": COMPILER_VERSION,
        "threshold_profile_version": _THRESHOLDS.version,
        "primary_anchor": inferred["anchor"],
        "facet": inferred["facet"],
        "anchor_state": inferred["anchor_state"],
        "facet_state": inferred["facet_state"],
        "anchor_candidates": list(inferred.get("anchor_candidates") or []),
        "related_anchors": list(inferred.get("related_anchors") or []),
        "confidence": inferred["confidence"],
        "anchor_hits": list(inferred.get("anchor_hits") or []),
        "facet_hits": list(inferred.get("facet_hits") or []),
        "trace": {
            "anchor": inferred.get("anchor_trace") or {},
            "facet": inferred.get("facet_trace") or {},
        },
    }


def _classify_entry(entry: dict[str, Any]) -> dict[str, Any]:
    content = str(entry.get("content") or "").strip()
    text = _normalize_text(content)
    anchor, anchor_state, anchor_trace = _classify_anchor(text)
    stance_score = _score_text_direction(text)

    if anchor not in {"", "unknown"}:
        facet, facet_state, facet_trace = _classify_facet(anchor, text)
    else:
        facet = "unknown"
        facet_state = ClassificationState.UNKNOWN
        facet_trace = ClassificationTrace(
            state=ClassificationState.UNKNOWN,
            threshold_profile_version=_THRESHOLDS.version,
            winner=None,
            runner_up=None,
            threshold_used=_facet_threshold(None),
            margin_used=_THRESHOLDS.facet_margin_min,
            fallback_reason="anchor_unknown",
            candidates=(),
        )

    anchor_hits = list(anchor_trace.winner.hits) if anchor_trace.winner else []
    facet_hits = list(facet_trace.winner.hits) if facet_trace.winner else []
    confidence = _entry_confidence(
        anchor_score=float(anchor_trace.winner.score) if anchor_trace.winner else 0.0,
        anchor_hits=anchor_hits,
        facet_hits=facet_hits,
        stance_score=stance_score,
        anchor_state=anchor_state,
        facet_state=facet_state,
    )

    return {
        "entry": entry,
        "anchor": anchor,
        "facet": facet,
        "anchor_state": anchor_state.value,
        "facet_state": facet_state.value,
        "anchor_candidates": [
            candidate.key
            for candidate in anchor_trace.candidates
            if candidate.score >= _anchor_threshold(candidate.key)
        ],
        "related_anchors": _secondary_anchor_candidates(
            anchor_trace=anchor_trace,
            primary_anchor=anchor,
        ),
        "anchor_score": float(anchor_trace.winner.score) if anchor_trace.winner else 0.0,
        "anchor_hits": anchor_hits,
        "facet_hits": facet_hits,
        "anchor_trace": anchor_trace.as_dict(),
        "facet_trace": facet_trace.as_dict(),
        "stance_score": stance_score,
        "confidence": confidence,
        "text": text,
    }


def _secondary_anchor_candidates(
    *,
    anchor_trace: ClassificationTrace,
    primary_anchor: str,
) -> list[dict[str, Any]]:
    if not primary_anchor or primary_anchor in {"unknown", "life"}:
        return []

    winner_score = float(anchor_trace.winner.score) if anchor_trace.winner else 0.0
    if winner_score <= 0:
        return []

    related: list[dict[str, Any]] = []
    for candidate in anchor_trace.candidates:
        candidate_key = str(candidate.key or "").strip()
        if not candidate_key or candidate_key in {primary_anchor, "unknown", "life"}:
            continue
        if candidate.score < _anchor_threshold(candidate_key):
            continue
        if (candidate.score / winner_score) < _THRESHOLDS.related_anchor_min_score_ratio:
            continue
        related.append(
            {
                "anchor": candidate_key,
                "score": round(float(candidate.score), 4),
                "hits": list(candidate.hits),
            }
        )
        if len(related) >= _THRESHOLDS.max_related_anchors_per_entry:
            break
    return related


def _topic_memberships_for_entry(item: dict[str, Any]) -> list[dict[str, Any]]:
    anchor = str(item.get("anchor") or "").strip()
    if not anchor or anchor in {"unknown", "life"}:
        return []

    memberships: list[dict[str, Any]] = [
        {
            **item,
            "anchor": anchor,
            "source_anchor": anchor,
            "membership_role": item.get("membership_role") or "primary",
        }
    ]
    for related in item.get("related_anchors") or []:
        related_anchor = str((related or {}).get("anchor") or "").strip()
        if not related_anchor or related_anchor in {anchor, "unknown", "life"}:
            continue
        memberships.append(
            {
                **item,
                "anchor": related_anchor,
                "source_anchor": anchor,
                "membership_role": "related",
            }
        )
    return memberships


def _classify_anchor(text: str) -> tuple[str, ClassificationState, ClassificationTrace]:
    candidates = _score_anchor_candidates(text)
    winner = candidates[0] if candidates else None
    runner_up = candidates[1] if len(candidates) > 1 else None
    threshold = _anchor_threshold(winner.key if winner else None)

    if winner is None:
        trace = ClassificationTrace(
            state=ClassificationState.UNKNOWN,
            threshold_profile_version=_THRESHOLDS.version,
            winner=None,
            runner_up=None,
            threshold_used=threshold,
            margin_used=_THRESHOLDS.anchor_margin_min,
            fallback_reason="no_anchor_signal",
            candidates=(),
        )
        return "unknown", ClassificationState.UNKNOWN, trace

    if winner.score < threshold:
        trace = ClassificationTrace(
            state=ClassificationState.UNKNOWN,
            threshold_profile_version=_THRESHOLDS.version,
            winner=winner,
            runner_up=runner_up,
            threshold_used=threshold,
            margin_used=_THRESHOLDS.anchor_margin_min,
            fallback_reason="anchor_below_threshold",
            candidates=tuple(candidates),
        )
        return "unknown", ClassificationState.UNKNOWN, trace

    if runner_up and (winner.score - runner_up.score) < _THRESHOLDS.anchor_margin_min:
        state = (
            ClassificationState.UNKNOWN
            if _THRESHOLDS.unknown_if_ambiguous
            else ClassificationState.UNCERTAIN
        )
        trace = ClassificationTrace(
            state=state,
            threshold_profile_version=_THRESHOLDS.version,
            winner=winner,
            runner_up=runner_up,
            threshold_used=threshold,
            margin_used=_THRESHOLDS.anchor_margin_min,
            fallback_reason="anchor_ambiguous",
            candidates=tuple(candidates),
        )
        return ("unknown" if state == ClassificationState.UNKNOWN else winner.key), state, trace

    trace = ClassificationTrace(
        state=ClassificationState.CONFIDENT,
        threshold_profile_version=_THRESHOLDS.version,
        winner=winner,
        runner_up=runner_up,
        threshold_used=threshold,
        margin_used=_THRESHOLDS.anchor_margin_min,
        fallback_reason=None,
        candidates=tuple(candidates),
    )
    return winner.key, ClassificationState.CONFIDENT, trace


def _classify_facet(anchor: str | None, text: str) -> tuple[str, ClassificationState, ClassificationTrace]:
    if not anchor or anchor in {"unknown", "life"}:
        trace = ClassificationTrace(
            state=ClassificationState.UNKNOWN,
            threshold_profile_version=_THRESHOLDS.version,
            winner=None,
            runner_up=None,
            threshold_used=_facet_threshold(anchor),
            margin_used=_THRESHOLDS.facet_margin_min,
            fallback_reason="anchor_unknown",
            candidates=(),
        )
        return "unknown", ClassificationState.UNKNOWN, trace

    candidates = _score_facet_candidates(anchor, text)
    winner = candidates[0] if candidates else None
    runner_up = candidates[1] if len(candidates) > 1 else None
    threshold = _facet_threshold(anchor)

    if winner is None:
        trace = ClassificationTrace(
            state=ClassificationState.UNKNOWN,
            threshold_profile_version=_THRESHOLDS.version,
            winner=None,
            runner_up=None,
            threshold_used=threshold,
            margin_used=_THRESHOLDS.facet_margin_min,
            fallback_reason="no_facet_signal",
            candidates=(),
        )
        return "unknown", ClassificationState.UNKNOWN, trace

    if winner.score < threshold:
        trace = ClassificationTrace(
            state=ClassificationState.UNKNOWN,
            threshold_profile_version=_THRESHOLDS.version,
            winner=winner,
            runner_up=runner_up,
            threshold_used=threshold,
            margin_used=_THRESHOLDS.facet_margin_min,
            fallback_reason="facet_below_threshold",
            candidates=tuple(candidates),
        )
        return "unknown", ClassificationState.UNKNOWN, trace

    if runner_up and (winner.score - runner_up.score) < _THRESHOLDS.facet_margin_min:
        trace = ClassificationTrace(
            state=ClassificationState.UNCERTAIN,
            threshold_profile_version=_THRESHOLDS.version,
            winner=winner,
            runner_up=runner_up,
            threshold_used=threshold,
            margin_used=_THRESHOLDS.facet_margin_min,
            fallback_reason="facet_ambiguous",
            candidates=tuple(candidates),
        )
        return "unknown", ClassificationState.UNCERTAIN, trace

    trace = ClassificationTrace(
        state=ClassificationState.CONFIDENT,
        threshold_profile_version=_THRESHOLDS.version,
        winner=winner,
        runner_up=runner_up,
        threshold_used=threshold,
        margin_used=_THRESHOLDS.facet_margin_min,
        fallback_reason=None,
        candidates=tuple(candidates),
    )
    return winner.key, ClassificationState.CONFIDENT, trace


def _score_anchor_candidates(text: str) -> list[CandidateScore]:
    candidates: list[CandidateScore] = []
    for anchor, rule in _TAXONOMY.anchor_rules.items():
        positive_score, positive_hits = _match_terms(text, rule)
        alias_score, alias_hits = _match_aliases(text, _TAXONOMY.anchor_aliases, anchor)
        negative_score, negative_hits = _match_terms(text, _TAXONOMY.anchor_negative_rules.get(anchor) or {})
        score = round(max(0.0, positive_score + alias_score - negative_score), 4)
        if not positive_hits and not alias_hits and not negative_hits:
            continue
        candidates.append(
            CandidateScore(
                key=anchor,
                score=score,
                hits=tuple(dict.fromkeys([*positive_hits, *alias_hits])),
                negative_hits=tuple(dict.fromkeys(negative_hits)),
                priority=_TAXONOMY.priority_for(anchor),
            )
        )
    candidates.sort(key=lambda candidate: (-candidate.score, -candidate.priority, candidate.key))
    return candidates


def _score_facet_candidates(anchor: str, text: str) -> list[CandidateScore]:
    candidates: list[CandidateScore] = []
    facet_rules = _TAXONOMY.facet_rules.get(anchor) or {}
    facet_aliases = _TAXONOMY.facet_aliases.get(anchor) or {}
    facet_negative = _TAXONOMY.facet_negative_rules.get(anchor) or {}

    for facet, terms in facet_rules.items():
        positive_score, positive_hits = _match_terms(text, terms)
        alias_score, alias_hits = _match_aliases(text, facet_aliases, facet)
        negative_score, negative_hits = _match_terms(text, facet_negative.get(facet) or {})
        score = round(max(0.0, positive_score + alias_score - negative_score), 4)
        if not positive_hits and not alias_hits and not negative_hits:
            continue
        candidates.append(
            CandidateScore(
                key=facet,
                score=score,
                hits=tuple(dict.fromkeys([*positive_hits, *alias_hits])),
                negative_hits=tuple(dict.fromkeys(negative_hits)),
                priority=0,
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.key))
    return candidates


def _anchor_threshold(anchor: str | None) -> float:
    if anchor:
        return max(_THRESHOLDS.anchor_min_score, _TAXONOMY.anchor_min_score(anchor))
    return _THRESHOLDS.anchor_min_score


def _facet_threshold(anchor: str | None) -> float:
    if anchor:
        return max(_THRESHOLDS.facet_min_score, _TAXONOMY.facet_min_score(anchor))
    return _THRESHOLDS.facet_min_score


def _match_aliases(text: str, aliases: dict[str, str], target: str) -> tuple[float, list[str]]:
    score = 0.0
    hits: list[str] = []
    for alias, canonical in aliases.items():
        if canonical != target:
            continue
        if alias in text:
            score += _ALIAS_BOOST
            hits.append(f"alias:{alias}")
    return round(score, 4), hits


def _aggregate_classification_score(entry_tags: dict[str, dict[str, Any]]) -> float:
    if not entry_tags:
        return 0.0

    state_weight = {
        ClassificationState.CONFIDENT.value: 1.0,
        ClassificationState.UNCERTAIN.value: 0.72,
        ClassificationState.UNKNOWN.value: 0.42,
    }
    scores: list[float] = []
    for tag in entry_tags.values():
        confidence = float(tag.get("confidence") or 0.0)
        anchor_weight = state_weight.get(str(tag.get("anchor_state") or ClassificationState.UNKNOWN.value), 0.42)
        facet_weight = state_weight.get(str(tag.get("facet_state") or ClassificationState.UNKNOWN.value), 0.42)
        membership_weight = (
            _THRESHOLDS.related_anchor_membership_weight
            if str(tag.get("membership_role") or "primary") == "related"
            else 1.0
        )
        scores.append(
            confidence
            * ((anchor_weight * 0.6) + (facet_weight * 0.4))
            * membership_weight
        )
    return round(sum(scores) / len(scores), 4)


def _coherence_score(topic: dict[str, Any]) -> float:
    arc = topic.get("arc") or {}
    features = arc.get("features") or {}
    stability = _clamp(_normalize_scalar(features.get("stability")) or 0.0, 0.0, 1.0)
    density = _normalize_scalar(features.get("density")) or 0.0
    density_score = _clamp(density / 0.08, 0.0, 1.0)
    element_count = max(int(topic.get("selected_count") or 0), 0)
    count_score = _clamp(element_count / 6.0, 0.0, 1.0)
    return round((stability * 0.5) + (density_score * 0.3) + (count_score * 0.2), 4)


def _build_topic_surface(topic: dict[str, Any]) -> dict[str, Any]:
    classification_score = _aggregate_classification_score(topic.get("entry_tags") or {})
    coherence_score = _coherence_score(topic)
    mirror_allowed = (
        classification_score >= _THRESHOLDS.surface_mirror_min
        and coherence_score >= _THRESHOLDS.coherence_min
    )
    detail_allowed = (
        mirror_allowed
        and classification_score >= _THRESHOLDS.surface_detail_min
        and coherence_score >= _THRESHOLDS.coherence_min
    )

    blocked_reason = None
    if not mirror_allowed:
        if classification_score < _THRESHOLDS.surface_mirror_min:
            blocked_reason = "mirror_below_classification_threshold"
        elif coherence_score < _THRESHOLDS.coherence_min:
            blocked_reason = "mirror_below_coherence_threshold"
    elif not detail_allowed:
        blocked_reason = "detail_below_threshold"

    return {
        "mirror_allowed": mirror_allowed,
        "detail_allowed": detail_allowed,
        "classification_score": classification_score,
        "coherence_score": coherence_score,
        "blocked_reason": blocked_reason,
    }


def _compute_inputs_hash(
    *,
    persona_id: str,
    entries: list[dict[str, Any]],
    max_gap_days: int,
    min_len: int,
) -> str:
    canonical_entries = [
        {
            "day": _safe_int(entry.get("day")),
            "timestamp": _parse_ts(entry.get("timestamp")).isoformat(),
            "content": str(entry.get("content") or "").strip(),
            "time_of_day": str(entry.get("time_of_day") or "").strip(),
        }
        for entry in entries
    ]
    payload = {
        "persona_id": persona_id,
        "entries": canonical_entries,
        "max_gap_days": max_gap_days,
        "min_len": min_len,
        "taxonomy_version": _TAXONOMY.version,
        "compiler_version": COMPILER_VERSION,
        "threshold_profile_version": _THRESHOLDS.version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _annotate_topic_entries(
    *,
    anchor: str,
    inferred_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(
        inferred_entries,
        key=lambda item: (
            _safe_int(item["entry"].get("day")),
            _parse_ts(item["entry"].get("timestamp")),
        ),
    )

    annotated: list[dict[str, Any]] = []
    previous_stance: str | None = None
    total = len(ordered)

    for index, info in enumerate(ordered):
        entry = info["entry"]
        content = str(entry.get("content") or "").strip()
        text = str(info.get("text") or "")
        facet = info.get("facet")
        facet_state = info.get("facet_state") or ClassificationState.UNKNOWN.value
        facet_hits = list(info.get("facet_hits") or [])
        state = _infer_decision_state(
            text=text,
            stance_score=float(info.get("stance_score") or 0.0),
            index=index,
            total=total,
            previous_stance=previous_stance,
        )
        stance = _infer_stance(
            state=state,
            stance_score=float(info.get("stance_score") or 0.0),
        )
        scalar = _derive_scalar(decision_state=state, stance=stance)
        confidence = _entry_confidence(
            anchor_score=float(info.get("anchor_score") or 0.0),
            anchor_hits=info.get("anchor_hits") or [],
            facet_hits=facet_hits,
            stance_score=float(info.get("stance_score") or 0.0),
            anchor_state=ClassificationState(str(info.get("anchor_state") or ClassificationState.UNKNOWN.value)),
            facet_state=ClassificationState(str(facet_state or ClassificationState.UNKNOWN.value)),
        )

        annotated.append(
            {
                "day": _safe_int(entry.get("day")),
                "timestamp": str(entry.get("timestamp") or ""),
                "content": content,
                "time_of_day": str(entry.get("time_of_day") or ""),
                "source_type": str(entry.get("source_type") or "simulation"),
                "source_id": str(entry.get("source_id") or ""),
                "source_ref": str(entry.get("source_ref") or ""),
                "facet": facet if facet_state == ClassificationState.CONFIDENT.value else None,
                "anchor_state": info.get("anchor_state"),
                "facet_state": facet_state,
                "decision_state": state,
                "stance": stance,
                "scalar": scalar,
                "confidence": confidence,
                "facet_terms": list(dict.fromkeys(facet_hits)),
                "membership_role": str(info.get("membership_role") or "primary"),
                "source_anchor": str(info.get("source_anchor") or anchor),
                "related_anchors": list(info.get("related_anchors") or []),
                "matched_terms": list(dict.fromkeys([*(info.get("anchor_hits") or []), *facet_hits])),
                "trace": {
                    "anchor": info.get("anchor_trace") or {},
                    "facet": info.get("facet_trace") or {},
                    "fallback_reason": (
                        (info.get("facet_trace") or {}).get("fallback_reason")
                        or (info.get("anchor_trace") or {}).get("fallback_reason")
                    ),
                    "matched_terms": list(dict.fromkeys([*(info.get("anchor_hits") or []), *facet_hits])),
                    "negative_hits": list(
                        dict.fromkeys(
                            [
                                *(((info.get("anchor_trace") or {}).get("winner") or {}).get("negative_hits") or []),
                                *(((info.get("facet_trace") or {}).get("winner") or {}).get("negative_hits") or []),
                            ]
                        )
                    ),
                    "membership_role": str(info.get("membership_role") or "primary"),
                    "source_anchor": str(info.get("source_anchor") or anchor),
                    "related_anchors": list(info.get("related_anchors") or []),
                },
            }
        )
        if stance != "unclear":
            previous_stance = stance

    return annotated


def _enrich_phase_stats(arc):
    enriched_phases = []
    for phase in arc.phases:
        base_stats = dict(phase.stats)
        base_stats.update(_phase_tag_stats(phase.elements))
        enriched_phases.append(replace(phase, stats=base_stats))
    return replace(arc, phases=tuple(enriched_phases))


def _phase_tag_stats(elements: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    facet_scores: dict[str, float] = {}
    facet_counts: dict[str, int] = {}
    term_scores: dict[str, float] = {}
    facet_term_scores: dict[str, dict[str, float]] = {}

    for item in elements:
        facet = _normalize_token(item.get("facet"))
        confidence = _normalize_scalar(item.get("confidence"))
        weight = confidence if confidence is not None else 0.5
        if facet:
            facet_scores[facet] = facet_scores.get(facet, 0.0) + weight
            facet_counts[facet] = facet_counts.get(facet, 0) + 1

        raw_terms = item.get("facet_terms")
        if not isinstance(raw_terms, list) or not raw_terms:
            raw_terms = item.get("matched_terms")
        if isinstance(raw_terms, list):
            seen_terms: set[str] = set()
            for raw_term in raw_terms:
                term = str(raw_term).strip()
                if not term or term in seen_terms:
                    continue
                seen_terms.add(term)
                term_scores[term] = term_scores.get(term, 0.0) + weight
                if facet:
                    bucket = facet_term_scores.setdefault(facet, {})
                    bucket[term] = bucket.get(term, 0.0) + weight

    if not facet_scores:
        return {}

    ranked_facets = sorted(
        facet_scores.items(),
        key=lambda pair: (-pair[1], -facet_counts.get(pair[0], 0), pair[0]),
    )
    dominant_facet, dominant_score = ranked_facets[0]
    total_facet_score = sum(facet_scores.values()) or 1.0
    dominant_term_scores = facet_term_scores.get(dominant_facet) or term_scores
    top_terms = sorted(dominant_term_scores.items(), key=lambda pair: (-pair[1], pair[0]))

    dominant_tag_label = dominant_facet.replace("_", " ")

    return {
        "dominant_facet": dominant_facet,
        "dominant_facet_confidence": round(min(dominant_score / total_facet_score, 1.0), 4),
        "dominant_tag": {
            "label": dominant_tag_label,
            "confidence": round(min(dominant_score / total_facet_score, 1.0), 4),
            "kind": "facet",
        },
        "top_tags": [
            {
                "label": term.replace("_", " "),
                "confidence": round(min(score / total_facet_score, 1.0), 4),
                "kind": "matched_term",
            }
            for term, score in top_terms[:3]
        ],
        "top_facets": [
            {
                "label": facet.replace("_", " "),
                "confidence": round(min(score / total_facet_score, 1.0), 4),
                "kind": "facet",
            }
            for facet, score in ranked_facets[:3]
        ],
    }


def _infer_decision_state(
    *,
    text: str,
    stance_score: float,
    index: int,
    total: int,
    previous_stance: str | None,
) -> str:
    if _contains_any(text, _TAXONOMY.defer_cues):
        return "deferred"

    if _contains_any(text, _TAXONOMY.reversal_cues):
        return "reversed"

    if index == 0 and abs(stance_score) < 0.35:
        return "questioning"

    if index == total - 1:
        if stance_score <= -0.35:
            return "reversed"
        if stance_score >= 0.45:
            return "resolved"
        if abs(stance_score) < 0.2:
            return "resolved"
        return "committed"

    if previous_stance == "toward" and stance_score <= -0.35:
        return "reversed"
    if stance_score <= -0.45:
        return "leaning_no"
    if stance_score >= 0.65 and index >= max(1, total // 2):
        return "committed"
    if stance_score >= 0.25:
        return "leaning_yes"
    if abs(stance_score) < 0.2:
        return "questioning"
    return "leaning_no"


def _infer_stance(*, state: str, stance_score: float) -> str:
    if state == "deferred":
        return "unclear"
    if state in {"leaning_no", "reversed"}:
        return "away"
    if state in {"leaning_yes", "committed", "resolved"}:
        return "toward"
    if stance_score >= 0.2:
        return "toward"
    if stance_score <= -0.2:
        return "away"
    return "unclear"


def _match_terms(text: str, terms: dict[str, float]) -> tuple[float, list[str]]:
    score = 0.0
    hits: list[str] = []
    for term, weight in terms.items():
        if _term_present(text, term):
            score += float(weight)
            hits.append(term)
    return score, hits


def _score_text_direction(text: str) -> float:
    positive, _ = _match_terms(text, _TAXONOMY.positive_cues)
    negative, _ = _match_terms(text, _TAXONOMY.negative_cues)
    return round(positive - negative, 4)


def _entry_confidence(
    *,
    anchor_score: float,
    anchor_hits: list[str],
    facet_hits: list[str],
    stance_score: float,
    anchor_state: ClassificationState,
    facet_state: ClassificationState,
) -> float:
    confidence = 0.2
    confidence += min(anchor_score, 2.5) * 0.14
    confidence += min(len(anchor_hits), 4) * 0.04
    confidence += min(len(facet_hits), 3) * 0.04
    confidence += min(abs(stance_score), 1.0) * 0.05

    state_weight = {
        ClassificationState.CONFIDENT: 1.0,
        ClassificationState.UNCERTAIN: 0.72,
        ClassificationState.UNKNOWN: 0.42,
    }
    weighted = confidence * ((state_weight[anchor_state] * 0.6) + (state_weight[facet_state] * 0.4))
    return round(_clamp(weighted, 0.05, 0.95), 4)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_term_present(text, phrase) for phrase in phrases)


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().replace("\n", " ").replace("—", " ").split())


def _normalize_token(value: Any) -> str | None:
    token = str(value or "").strip().lower().replace(" ", "_")
    return token or None


def _normalize_state(value: Any) -> str | None:
    raw = str(value or "").strip().upper()
    if raw in {state.value for state in ClassificationState}:
        return raw
    return None


def _normalize_scalar(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _derive_scalar(
    *,
    decision_state: str | None,
    stance: str | None,
) -> float | None:
    if not decision_state and not stance:
        return None

    magnitude_map = {
        "questioning": 0.15,
        "leaning_yes": 0.45,
        "leaning_no": 0.45,
        "committed": 0.9,
        "deferred": 0.2,
        "reversed": 0.75,
        "resolved": 1.0,
    }
    base = magnitude_map.get(decision_state or "", 0.25)
    if stance == "away":
        return -base
    if stance == "unclear":
        return 0.0
    return base


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _term_present(text: str, term: str) -> bool:
    pattern = rf"(?<!\\w){re.escape(term)}(?!\\w)"
    return re.search(pattern, text) is not None
