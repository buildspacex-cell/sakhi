from __future__ import annotations

import json
import logging
import math
import re
from datetime import UTC, datetime, timedelta
from itertools import combinations
from typing import Any
from uuid import UUID

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.continuity.adapters import canonicalize_anchor
from sakhi.apps.api.services.continuity.thresholds import (
    CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE,
)
from sakhi.libs.embeddings import parse_pgvector

LOGGER = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "about",
    "around",
    "current",
    "phase",
    "thread",
    "started",
    "currently",
    "return",
    "today",
}
_MONEY_TERMS = {
    "money",
    "budget",
    "cost",
    "debt",
    "expense",
    "salary",
    "funding",
    "runway",
    "afford",
}
_CORRELATION_SELECT_COLUMNS_SQL = """
                topic_key_a,
                topic_key_b,
                combined_score,
                temporal_score,
                semantic_score,
                facet_score,
                directional_score,
                correlation_types,
                shared_facets,
                overlap_windows,
                source_window_start,
                source_window_end,
                computed_at
"""


async def compute_cross_topic_signals(
    *,
    person_id: str,
    selected_anchor: str,
    selected_topic: dict[str, Any],
    topics: list[dict[str, Any]],
    window_start: str,
    window_end: str,
    now: datetime,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    selected_anchor = canonicalize_anchor(selected_anchor)
    topics_map = _topics_map(topics)
    selected = topics_map.get(selected_anchor)
    if not selected:
        return None, None, None

    correlations = await _load_or_compute_correlations(
        person_id=person_id,
        selected_anchor=selected_anchor,
        selected_topic=selected,
        topics_map=topics_map,
        window_start=window_start,
        window_end=window_end,
        now=now,
    )
    cross_context = _build_cross_context_signal(
        selected_topic=selected,
        selected_anchor=selected_anchor,
        topics_map=topics_map,
        correlations=correlations,
        now=now,
    )
    whole_story = _build_whole_story_signal(
        selected_topic=selected,
        cross_context=cross_context,
        topics_map=topics_map,
    )
    life_dimensions = await get_life_dimensions(
        person_id=person_id,
        topics=topics,
        now=now,
    )
    return cross_context, whole_story, life_dimensions


async def get_life_dimensions(
    *,
    person_id: str,
    topics: list[dict[str, Any]] | None,
    now: datetime,
) -> dict[str, Any] | None:
    cached = await _load_cached_life_dimensions(person_id=person_id, now=now)
    if cached is not None:
        return cached
    if not topics:
        return None

    topics_map = _topics_map(topics)
    computed = _compute_life_dimensions(topics_map=topics_map, now=now)
    await _upsert_life_dimensions(person_id=person_id, dimensions=computed)
    surfaced = {
        key: value
        for key, value in computed.items()
        if isinstance(value, dict) and bool(value.get("surface"))
    }
    if not surfaced:
        return None
    return {
        "time_availability": surfaced.get("time_availability"),
        "financial_pressure": surfaced.get("financial_pressure"),
        "emotional_bandwidth": surfaced.get("emotional_bandwidth"),
    }


async def invalidate_person_cross_topic_cache(*, person_id: str) -> None:
    """
    Invalidate cached cross-topic signals for a person.

    Called when source journal evidence is deleted so follow-up continuity reads
    cannot serve stale correlation/life-dimension data.
    """
    statements = [
        "DELETE FROM continuity_topic_correlations WHERE person_id = $1::uuid",
        "DELETE FROM continuity_life_dimensions WHERE person_id = $1::uuid",
    ]
    for sql in statements:
        try:
            await dbexec(sql, person_id)
        except Exception as exc:
            LOGGER.info(
                "Cross-topic cache invalidation skipped for %s (%s): %s",
                person_id,
                sql.split("FROM ", 1)[-1],
                exc,
            )


def _topics_map(topics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for topic in topics:
        anchor = canonicalize_anchor(topic.get("anchor"))
        if not anchor or anchor == "unknown":
            continue
        output[anchor] = topic
    return output


def _pair_key(anchor_a: str, anchor_b: str) -> tuple[str, str]:
    left, right = sorted([canonicalize_anchor(anchor_a), canonicalize_anchor(anchor_b)])
    return left, right


def _topic_pairs(anchors: list[str]) -> list[tuple[str, str]]:
    return [_pair_key(a, b) for a, b in combinations(anchors, 2)]


async def _load_cached_correlations_by_pair(
    *,
    person_id: str,
    anchors: list[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    if len(anchors) < 2:
        return {}
    try:
        rows = await dbfetch(
            f"""
            SELECT
{_CORRELATION_SELECT_COLUMNS_SQL}
            FROM continuity_topic_correlations
            WHERE person_id = $1::uuid
              AND topic_key_a = ANY($2::text[])
              AND topic_key_b = ANY($2::text[])
            ORDER BY computed_at DESC
            """,
            person_id,
            anchors,
        )
    except Exception as exc:
        LOGGER.info("Correlation cache read unavailable for %s: %s", person_id, exc)
        return {}

    cached: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows or []:
        key = _pair_key(
            str(row.get("topic_key_a") or ""), str(row.get("topic_key_b") or "")
        )
        if not key[0] or not key[1]:
            continue
        cached[key] = row
    return cached


def _collect_source_refs_for_topics(
    *,
    moments_by_anchor: dict[str, list[dict[str, Any]]],
    topic_keys: list[str],
) -> set[str]:
    refs: set[str] = set()
    for topic_key in topic_keys:
        for moment in moments_by_anchor.get(topic_key) or []:
            source_ref = str(moment.get("source_ref") or "").strip()
            if source_ref:
                refs.add(source_ref)
    return refs


def _journal_id_from_source_ref(source_ref: str | None) -> str | None:
    raw = str(source_ref or "").strip()
    if not raw:
        return None
    if ":" in raw:
        prefix, candidate = raw.split(":", 1)
        if prefix.strip().lower() != "journal":
            return None
        token = candidate.strip()
    else:
        token = raw
    if not token:
        return None
    try:
        return str(UUID(token))
    except Exception:
        return None


async def _load_journal_embedding_lookup(
    source_refs: set[str],
) -> dict[str, list[float]]:
    entry_ids = sorted(
        {
            journal_id
            for journal_id in (
                _journal_id_from_source_ref(source_ref) for source_ref in source_refs
            )
            if journal_id
        }
    )
    if not entry_ids:
        return {}
    try:
        rows = await dbfetch(
            """
            SELECT entry_id::text AS entry_id, COALESCE(embedding_vec, embedding) AS embedding
            FROM journal_embeddings
            WHERE entry_id = ANY($1::uuid[])
            """,
            entry_ids,
        )
    except Exception as exc:
        LOGGER.info("Journal embedding lookup unavailable: %s", exc)
        return {}

    lookup: dict[str, list[float]] = {}
    for row in rows or []:
        entry_id = str(row.get("entry_id") or "").strip()
        if not entry_id:
            continue
        vector = parse_pgvector(row.get("embedding"))
        if not vector:
            continue
        if not any(abs(value) > 1e-9 for value in vector):
            continue
        lookup[entry_id] = vector
    return lookup


async def _load_or_compute_correlations(
    *,
    person_id: str,
    selected_anchor: str,
    selected_topic: dict[str, Any],
    topics_map: dict[str, dict[str, Any]],
    window_start: str,
    window_end: str,
    now: datetime,
) -> list[dict[str, Any]]:
    if not _primary_topic_allows_linked_story(
        selected_anchor=selected_anchor,
        selected_topic=selected_topic,
        topics_map=topics_map,
    ):
        return []

    eligible_topics = {
        anchor: topic
        for anchor, topic in topics_map.items()
        if (
            _primary_topic_allows_linked_story(
                selected_anchor=anchor,
                selected_topic=topic,
                topics_map=topics_map,
            )
            if anchor == selected_anchor
            else _related_topic_allows_linked_story(topic)
        )
    }
    if selected_anchor not in eligible_topics:
        return []

    eligible_anchors = sorted(eligible_topics.keys())
    sweep_cap = max(
        2, CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.correlation_full_sweep_max_topics
    )
    if len(eligible_anchors) > sweep_cap:
        ranked = sorted(
            [anchor for anchor in eligible_anchors if anchor != selected_anchor],
            key=lambda anchor: (
                -int(eligible_topics.get(anchor, {}).get("selected_count") or 0),
                -_iso_sort_value(
                    str(
                        (
                            (eligible_topics.get(anchor, {}).get("arc") or {}).get(
                                "end_ts"
                            )
                        )
                        or ""
                    )
                ),
                anchor,
            ),
        )
        eligible_anchors = [selected_anchor, *ranked[: sweep_cap - 1]]
        eligible_anchors = sorted(set(eligible_anchors))
    all_pairs = _topic_pairs(eligible_anchors)
    cached_by_pair = await _load_cached_correlations_by_pair(
        person_id=person_id,
        anchors=eligible_anchors,
    )
    stale_pairs = [
        pair
        for pair in all_pairs
        if pair not in cached_by_pair
        or not _is_cache_fresh(cached_by_pair[pair], now=now)
    ]
    if stale_pairs:
        moments_by_anchor = {
            anchor: _included_moments(topic)
            for anchor, topic in eligible_topics.items()
        }
        stale_topic_keys = sorted({anchor for pair in stale_pairs for anchor in pair})
        embedding_lookup = await _load_journal_embedding_lookup(
            _collect_source_refs_for_topics(
                moments_by_anchor=moments_by_anchor,
                topic_keys=stale_topic_keys,
            )
        )
        for topic_key_a, topic_key_b in stale_pairs:
            metrics = _compute_correlation_metrics(
                topic_a=eligible_topics[topic_key_a],
                topic_b=eligible_topics[topic_key_b],
                anchor_a=topic_key_a,
                anchor_b=topic_key_b,
                window_start=window_start,
                window_end=window_end,
                moments_a=moments_by_anchor.get(topic_key_a),
                moments_b=moments_by_anchor.get(topic_key_b),
                embedding_lookup=embedding_lookup,
            )
            if metrics is None:
                continue
            cached_by_pair[_pair_key(topic_key_a, topic_key_b)] = metrics
            await _upsert_correlation_row(
                person_id=person_id,
                metrics=metrics,
                window_start=window_start,
                window_end=window_end,
            )

    selected_rows: list[dict[str, Any]] = []
    for related_anchor in eligible_anchors:
        if related_anchor == selected_anchor:
            continue
        pair = _pair_key(selected_anchor, related_anchor)
        row = cached_by_pair.get(pair)
        if row is None:
            continue
        related_topic = eligible_topics.get(related_anchor) or {}
        selected_rows.append(
            _normalize_correlation_row(
                row,
                related_anchor=related_anchor,
                related_topic=related_topic,
            )
        )

    selected_rows.sort(
        key=lambda item: (
            -float(item.get("combined_score") or 0.0),
            -int(item.get("overlap_pairs") or 0),
            str(item.get("related_topic_key") or ""),
        )
    )
    return selected_rows


def _normalize_correlation_row(
    row: dict[str, Any],
    *,
    related_anchor: str,
    related_topic: dict[str, Any],
) -> dict[str, Any]:
    related_label = str(
        related_topic.get("label") or related_anchor.replace("_", " ").title()
    ).strip()
    return {
        "related_topic_key": related_anchor,
        "related_topic_label": related_label,
        "related_selected_count": _topic_story_count(related_topic),
        "related_end_ts": str(((related_topic.get("arc") or {}).get("end_ts")) or ""),
        "combined_score": float(row.get("combined_score") or 0.0),
        "temporal_score": float(row.get("temporal_score") or 0.0),
        "semantic_score": float(row.get("semantic_score") or 0.0),
        "facet_score": float(row.get("facet_score") or 0.0),
        "directional_score": float(row.get("directional_score") or 0.0),
        "correlation_types": _parse_json_array(row.get("correlation_types")),
        "shared_facets": _parse_json_array(row.get("shared_facets")),
        "overlap_windows": _parse_json_array(row.get("overlap_windows")),
        "source_window_start": _iso(row.get("source_window_start")),
        "source_window_end": _iso(row.get("source_window_end")),
        "computed_at": _iso(row.get("computed_at")),
    }


def _is_cache_fresh(row: dict[str, Any], *, now: datetime) -> bool:
    computed_at = _coerce_ts(row.get("computed_at"))
    if computed_at is None:
        return False
    return (now - computed_at) <= timedelta(
        hours=CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.correlation_cache_ttl_hours
    )


def _compute_correlation_metrics(
    *,
    topic_a: dict[str, Any],
    topic_b: dict[str, Any],
    anchor_a: str,
    anchor_b: str,
    window_start: str,
    window_end: str,
    moments_a: list[dict[str, Any]] | None = None,
    moments_b: list[dict[str, Any]] | None = None,
    embedding_lookup: dict[str, list[float]] | None = None,
) -> dict[str, Any] | None:
    selected_moments_a = (
        moments_a if moments_a is not None else _included_moments(topic_a)
    )
    selected_moments_b = (
        moments_b if moments_b is not None else _included_moments(topic_b)
    )
    if not selected_moments_a or not selected_moments_b:
        return None

    temporal_score, overlap_pairs, overlap_windows = _temporal_overlap_details(
        selected_moments_a,
        selected_moments_b,
        max_days=7,
    )
    semantic_score = _semantic_overlap_score(
        selected_moments_a,
        selected_moments_b,
        embedding_lookup=embedding_lookup,
    )
    facet_score, shared_facets = _facet_overlap_score(
        selected_moments_a, selected_moments_b
    )
    directional_score = _directional_alignment_score(
        selected_moments_a, selected_moments_b
    )
    combined_score = (
        0.45 * temporal_score
        + 0.25 * semantic_score
        + 0.20 * facet_score
        + 0.10 * directional_score
    )
    correlation_types = [
        name
        for name, score in (
            ("temporal", temporal_score),
            ("semantic", semantic_score),
            ("facet", facet_score),
            ("directional", directional_score),
        )
        if score >= 0.3
    ]
    if not correlation_types and temporal_score > 0:
        correlation_types = ["temporal"]

    topic_key_a, topic_key_b = sorted([anchor_a, anchor_b])
    related_topic_key = anchor_b
    related_topic_label = str(
        topic_b.get("label") or anchor_b.replace("_", " ").title()
    ).strip()
    related_selected_count = _topic_story_count(topic_b)
    related_end_ts = str(((topic_b.get("arc") or {}).get("end_ts")) or "")

    return {
        "topic_key_a": topic_key_a,
        "topic_key_b": topic_key_b,
        "related_topic_key": related_topic_key,
        "related_topic_label": related_topic_label,
        "related_selected_count": related_selected_count,
        "related_end_ts": related_end_ts,
        "combined_score": round(combined_score, 4),
        "temporal_score": round(temporal_score, 4),
        "semantic_score": round(semantic_score, 4),
        "facet_score": round(facet_score, 4),
        "directional_score": round(directional_score, 4),
        "correlation_types": correlation_types[:4],
        "shared_facets": shared_facets[:8],
        "overlap_windows": overlap_windows[:3],
        "overlap_pairs": overlap_pairs,
        "source_window_start": window_start,
        "source_window_end": window_end,
        "computed_at": datetime.now(UTC).isoformat(),
    }


async def _upsert_correlation_row(
    *,
    person_id: str,
    metrics: dict[str, Any],
    window_start: str,
    window_end: str,
) -> None:
    try:
        await dbexec(
            """
            INSERT INTO continuity_topic_correlations (
                person_id,
                topic_key_a,
                topic_key_b,
                combined_score,
                temporal_score,
                semantic_score,
                facet_score,
                directional_score,
                correlation_types,
                shared_facets,
                overlap_windows,
                source_window_start,
                source_window_end,
                computed_at
            )
            VALUES (
                $1::uuid,
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8,
                $9::jsonb,
                $10::jsonb,
                $11::jsonb,
                $12::timestamptz,
                $13::timestamptz,
                now()
            )
            ON CONFLICT (person_id, topic_key_a, topic_key_b)
            DO UPDATE
            SET combined_score = EXCLUDED.combined_score,
                temporal_score = EXCLUDED.temporal_score,
                semantic_score = EXCLUDED.semantic_score,
                facet_score = EXCLUDED.facet_score,
                directional_score = EXCLUDED.directional_score,
                correlation_types = EXCLUDED.correlation_types,
                shared_facets = EXCLUDED.shared_facets,
                overlap_windows = EXCLUDED.overlap_windows,
                source_window_start = EXCLUDED.source_window_start,
                source_window_end = EXCLUDED.source_window_end,
                computed_at = now()
            """,
            person_id,
            str(metrics.get("topic_key_a") or ""),
            str(metrics.get("topic_key_b") or ""),
            float(metrics.get("combined_score") or 0.0),
            float(metrics.get("temporal_score") or 0.0),
            float(metrics.get("semantic_score") or 0.0),
            float(metrics.get("facet_score") or 0.0),
            float(metrics.get("directional_score") or 0.0),
            json.dumps(metrics.get("correlation_types") or [], ensure_ascii=False),
            json.dumps(metrics.get("shared_facets") or [], ensure_ascii=False),
            json.dumps(metrics.get("overlap_windows") or [], ensure_ascii=False),
            window_start,
            window_end,
        )
    except Exception as exc:
        LOGGER.info("Correlation cache upsert skipped for %s: %s", person_id, exc)


def _build_cross_context_signal(
    *,
    selected_topic: dict[str, Any],
    selected_anchor: str,
    topics_map: dict[str, dict[str, Any]],
    correlations: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    if not _primary_topic_allows_linked_story(
        selected_anchor=selected_anchor,
        selected_topic=selected_topic,
        topics_map=topics_map,
    ):
        return {
            "ready": False,
            "reason": "insufficient_depth",
            "correlation_score": 0.0,
            "correlation_type": "composite",
        }
    if not correlations:
        return {
            "ready": False,
            "reason": "insufficient_overlap",
            "correlation_score": 0.0,
            "correlation_type": "composite",
        }

    best = correlations[0]
    selected_end = _coerce_ts(
        str(((selected_topic.get("arc") or {}).get("end_ts")) or "")
    )
    related_end = _coerce_ts(best.get("related_end_ts"))
    recent_cutoff = now.timestamp() - (
        CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.cross_context_recent_activity_days
        * 86400
    )
    has_recent = bool(
        (selected_end and selected_end.timestamp() >= recent_cutoff)
        or (related_end and related_end.timestamp() >= recent_cutoff)
    )
    if not has_recent:
        reason = "threads_inactive"
    elif (
        float(best.get("combined_score") or 0.0)
        < CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.cross_context_min_combined_score
    ):
        reason = "insufficient_overlap"
    else:
        reason = "ready"

    correlation_types = _parse_json_array(best.get("correlation_types"))
    correlation_type = correlation_types[0] if correlation_types else "composite"
    return {
        "correlated_topic_key": str(best.get("related_topic_key") or ""),
        "correlated_topic_label": str(best.get("related_topic_label") or "").strip(),
        "correlated_selected_count": int(best.get("related_selected_count") or 0),
        "ready": reason == "ready",
        "reason": reason,
        "correlation_score": round(float(best.get("combined_score") or 0.0), 4),
        "correlation_type": correlation_type,
        "correlation_breakdown": {
            "temporal": round(float(best.get("temporal_score") or 0.0), 4),
            "semantic": round(float(best.get("semantic_score") or 0.0), 4),
            "facet": round(float(best.get("facet_score") or 0.0), 4),
            "directional": round(float(best.get("directional_score") or 0.0), 4),
        },
        "overlap_pairs": int(best.get("overlap_pairs") or 0),
    }


def _build_whole_story_signal(
    *,
    selected_topic: dict[str, Any],
    cross_context: dict[str, Any] | None,
    topics_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not cross_context:
        return None
    primary_anchor = canonicalize_anchor(selected_topic.get("anchor"))
    related_anchor = str(cross_context.get("correlated_topic_key") or "").strip()
    primary_count = _topic_story_count(selected_topic)
    related_count = int(cross_context.get("correlated_selected_count") or 0)
    related_topic = topics_map.get(related_anchor) or {}
    total = _whole_story_unique_moment_count(
        primary_topic=selected_topic,
        related_topic=related_topic,
    )

    if not cross_context.get("ready"):
        reason = str(cross_context.get("reason") or "insufficient_overlap")
    elif (
        primary_count
        < CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.whole_story_min_primary_moments
        or related_count
        < CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.whole_story_min_related_moments
    ):
        reason = "insufficient_depth"
    elif total < CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.whole_story_min_total_moments:
        reason = "insufficient_depth"
    else:
        reason = "ready"

    selected_topics = [item for item in [primary_anchor, related_anchor] if item]
    return {
        "ready": reason == "ready",
        "reason": reason,
        "selected_topics": selected_topics[
            : CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.max_topic_keys
        ],
        "selected_count_total": total,
        "correlation_score": round(
            float(cross_context.get("correlation_score") or 0.0), 4
        ),
    }


def _topic_story_count(topic: dict[str, Any]) -> int:
    if "effective_selected_count" in topic:
        return int(topic.get("effective_selected_count") or 0)
    if "primary_selected_count" in topic:
        return int(topic.get("primary_selected_count") or 0)
    return int(topic.get("selected_count") or 0)


def _primary_topic_allows_linked_story(
    *,
    selected_anchor: str,
    selected_topic: dict[str, Any],
    topics_map: dict[str, dict[str, Any]],
) -> bool:
    surface = selected_topic.get("surface") or {}
    selected_count = _topic_story_count(selected_topic)
    if (
        bool(surface.get("detail_allowed"))
        and selected_count
        >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.cross_context_min_moments
    ):
        return True
    if not bool(surface.get("mirror_allowed")):
        return False
    if (
        selected_count
        < CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.whole_story_min_primary_moments
    ):
        return False
    return _primary_topic_is_dominant(
        selected_anchor=selected_anchor,
        selected_topic=selected_topic,
        topics_map=topics_map,
    )


def _related_topic_allows_linked_story(topic: dict[str, Any]) -> bool:
    surface = topic.get("surface") or {}
    count = _topic_story_count(topic)
    if bool(surface.get("detail_allowed")):
        return (
            count
            >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.whole_story_min_related_moments
        )
    if not bool(surface.get("mirror_allowed")):
        return False
    return (
        count
        >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.whole_story_min_related_moments
    )


def _primary_topic_is_dominant(
    *,
    selected_anchor: str,
    selected_topic: dict[str, Any],
    topics_map: dict[str, dict[str, Any]],
) -> bool:
    selected_count = _topic_story_count(selected_topic)
    runner_up = max(
        (
            _topic_story_count(topic)
            for anchor, topic in topics_map.items()
            if anchor != selected_anchor
        ),
        default=0,
    )
    if runner_up <= 0:
        return False
    return selected_count >= math.ceil(
        runner_up
        * CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.whole_story_primary_dominance_ratio
    )


def _whole_story_unique_moment_count(
    *,
    primary_topic: dict[str, Any],
    related_topic: dict[str, Any],
) -> int:
    identities = {
        _moment_identity(moment)
        for moment in _included_moments(primary_topic) + _included_moments(related_topic)
    }
    identities.discard("")
    if identities:
        return len(identities)
    return max(0, _topic_story_count(primary_topic) + _topic_story_count(related_topic))


async def _load_cached_life_dimensions(
    *, person_id: str, now: datetime
) -> dict[str, Any] | None:
    try:
        rows = await dbfetch(
            """
            SELECT
                dimension,
                signal_level,
                signal_direction,
                affected_topics,
                evidence_summary,
                signal_markers,
                computed_at
            FROM continuity_life_dimensions
            WHERE person_id = $1::uuid
            """,
            person_id,
        )
    except Exception as exc:
        LOGGER.info("Life dimensions cache read unavailable for %s: %s", person_id, exc)
        return None

    dimensions: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        key = str(row.get("dimension") or "").strip()
        if not key:
            continue
        computed_at = _coerce_ts(row.get("computed_at"))
        if computed_at is None or (now - computed_at) > timedelta(
            hours=CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.life_dimensions_cache_ttl_hours
        ):
            return None
        level = float(row.get("signal_level") or 0.0)
        direction = str(row.get("signal_direction") or "neutral").strip()
        affected_topics = [
            str(x).strip() for x in (row.get("affected_topics") or []) if str(x).strip()
        ]
        markers = _parse_json_object(row.get("signal_markers"))
        surface = _should_surface_dimension(
            level=level,
            topic_count=len(affected_topics),
            entry_count=int(markers.get("entry_count") or 0),
            financial=(key == "financial_pressure"),
        )
        dimensions[key] = {
            "level": round(level, 4),
            "direction": direction,
            "affected_topics": affected_topics[:3],
            "evidence_summary": str(row.get("evidence_summary") or "").strip(),
            "signal_markers": markers,
            "surface": surface,
        }

    if not dimensions:
        return None

    surfaced = {
        key: value for key, value in dimensions.items() if bool(value.get("surface"))
    }
    if not surfaced:
        return None
    return {
        "time_availability": surfaced.get("time_availability"),
        "financial_pressure": surfaced.get("financial_pressure"),
        "emotional_bandwidth": surfaced.get("emotional_bandwidth"),
    }


def _compute_life_dimensions(
    *,
    topics_map: dict[str, dict[str, Any]],
    now: datetime,
) -> dict[str, dict[str, Any]]:
    rows = _collect_recent_moments(
        topics_map=topics_map,
        now=now,
        days=max(
            CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_time_window_days,
            CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_emotion_window_days,
            CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_financial_window_days,
        ),
    )
    recent_time = _filter_recent(
        rows,
        now=now,
        days=CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_time_window_days,
    )
    recent_emotion = _filter_recent(
        rows,
        now=now,
        days=CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_emotion_window_days,
    )
    recent_financial = _filter_recent(
        rows,
        now=now,
        days=CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_financial_window_days,
    )

    time_topics = sorted(
        {item["topic_key"] for item in recent_time if item.get("topic_key")}
    )
    time_level = min(
        1.0, (len(time_topics) / 4.0) * 0.6 + (len(recent_time) / 20.0) * 0.4
    )
    time_direction = _direction_for_level(time_level)
    time_markers = {
        "entry_count": len(recent_time),
        "topic_count": len(time_topics),
        "window_days": CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_time_window_days,
    }

    financial_rows = [
        item
        for item in recent_financial
        if set(
            _tokenize(f"{item.get('facet', '')} {item.get('snippet', '')}")
        ).intersection(_MONEY_TERMS)
    ]
    financial_topics = sorted(
        {item["topic_key"] for item in financial_rows if item.get("topic_key")}
    )
    financial_level = min(1.0, len(financial_rows) / 8.0)
    financial_direction = (
        "pressured"
        if financial_level
        >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.financial_surface_min_level
        else "neutral"
    )
    financial_markers = {
        "entry_count": len(financial_rows),
        "topic_count": len(financial_topics),
        "window_days": CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_financial_window_days,
    }

    stance_rows = [item for item in recent_emotion if item.get("stance")]
    away_count = sum(
        1
        for item in stance_rows
        if str(item.get("stance") or "").strip().lower() == "away"
    )
    toward_count = sum(
        1
        for item in stance_rows
        if str(item.get("stance") or "").strip().lower() == "toward"
    )
    emotional_level = (away_count / len(stance_rows)) if stance_rows else 0.0
    emotional_topics = sorted(
        {item["topic_key"] for item in stance_rows if item.get("topic_key")}
    )
    if (
        emotional_level
        >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_high
    ):
        emotional_direction = "pressured"
    elif (
        toward_count > away_count
        and emotional_level
        <= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_low
    ):
        emotional_direction = "resourced"
    else:
        emotional_direction = "neutral"
    emotional_markers = {
        "entry_count": len(stance_rows),
        "topic_count": len(emotional_topics),
        "away_count": away_count,
        "toward_count": toward_count,
        "window_days": CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_emotion_window_days,
    }

    time_surface = _should_surface_dimension(
        level=time_level,
        topic_count=len(time_topics),
        entry_count=len(recent_time),
        financial=False,
    )
    financial_surface = _should_surface_dimension(
        level=financial_level,
        topic_count=len(financial_topics),
        entry_count=len(financial_rows),
        financial=True,
    )
    emotional_surface = _should_surface_dimension(
        level=emotional_level,
        topic_count=len(emotional_topics),
        entry_count=len(stance_rows),
        financial=False,
    )

    return {
        "time_availability": {
            "level": round(time_level, 4),
            "direction": time_direction,
            "affected_topics": time_topics[:3],
            "evidence_summary": (
                f"Recent activity is spread across {len(time_topics)} threads in the last "
                f"{CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_time_window_days} days."
            ),
            "signal_markers": time_markers,
            "surface": time_surface,
        },
        "financial_pressure": {
            "level": round(financial_level, 4),
            "direction": financial_direction,
            "affected_topics": financial_topics[:3],
            "evidence_summary": (
                f"Money and tradeoff language appeared in {len(financial_rows)} moments recently."
            ),
            "signal_markers": financial_markers,
            "surface": financial_surface,
        },
        "emotional_bandwidth": {
            "level": round(emotional_level, 4),
            "direction": emotional_direction,
            "affected_topics": emotional_topics[:3],
            "evidence_summary": (
                "Recent stance signals show whether emotional bandwidth is compressed or resourced."
            ),
            "signal_markers": emotional_markers,
            "surface": emotional_surface,
        },
    }


async def _upsert_life_dimensions(
    *,
    person_id: str,
    dimensions: dict[str, dict[str, Any]],
) -> None:
    for dimension, payload in dimensions.items():
        try:
            await dbexec(
                """
                INSERT INTO continuity_life_dimensions (
                    person_id,
                    dimension,
                    signal_level,
                    signal_direction,
                    affected_topics,
                    evidence_summary,
                    signal_markers,
                    computed_at
                )
                VALUES (
                    $1::uuid,
                    $2,
                    $3,
                    $4,
                    $5::text[],
                    $6,
                    $7::jsonb,
                    now()
                )
                ON CONFLICT (person_id, dimension)
                DO UPDATE
                SET signal_level = EXCLUDED.signal_level,
                    signal_direction = EXCLUDED.signal_direction,
                    affected_topics = EXCLUDED.affected_topics,
                    evidence_summary = EXCLUDED.evidence_summary,
                    signal_markers = EXCLUDED.signal_markers,
                    computed_at = now()
                """,
                person_id,
                dimension,
                float(payload.get("level") or 0.0),
                str(payload.get("direction") or "neutral"),
                list(payload.get("affected_topics") or []),
                str(payload.get("evidence_summary") or ""),
                json.dumps(payload.get("signal_markers") or {}, ensure_ascii=False),
            )
        except Exception as exc:
            LOGGER.info(
                "Life dimensions cache upsert skipped for %s/%s: %s",
                person_id,
                dimension,
                exc,
            )


def _should_surface_dimension(
    *,
    level: float,
    topic_count: int,
    entry_count: int,
    financial: bool,
) -> bool:
    if (
        topic_count
        < CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_min_topics
    ):
        return False
    if (
        entry_count
        < CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_min_entries
    ):
        return False
    if financial:
        return (
            level
            >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.financial_surface_min_level
        )
    return bool(
        level >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_high
        or level <= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_low
    )


def _direction_for_level(level: float) -> str:
    if level >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_high:
        return "pressured"
    if level <= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_low:
        return "resourced"
    return "neutral"


def _collect_recent_moments(
    *,
    topics_map: dict[str, dict[str, Any]],
    now: datetime,
    days: int,
) -> list[dict[str, Any]]:
    cutoff = now.timestamp() - (days * 86400)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for topic_key, topic in topics_map.items():
        for moment in _included_moments(topic):
            ts = _coerce_ts(moment.get("ts"))
            if ts is None or ts.timestamp() < cutoff:
                continue
            identity = _moment_identity(moment)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(
                {
                    "topic_key": topic_key,
                    "ts": ts,
                    "facet": str(moment.get("facet") or ""),
                    "stance": str(moment.get("stance") or "").strip().lower(),
                    "snippet": str(moment.get("snippet") or ""),
                }
            )
    return rows


def _filter_recent(
    rows: list[dict[str, Any]], *, now: datetime, days: int
) -> list[dict[str, Any]]:
    cutoff = now.timestamp() - (days * 86400)
    return [
        item
        for item in rows
        if isinstance(item.get("ts"), datetime) and item["ts"].timestamp() >= cutoff
    ]


def _included_moments(topic: dict[str, Any]) -> list[dict[str, Any]]:
    event_refs = (topic.get("arc") or {}).get("event_refs") or []
    entry_tags = topic.get("entry_tags") or {}
    moments: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in event_refs:
        tag = _resolve_entry_tag(entry_tags=entry_tags, ref=ref)
        item = {
            "source_ref": ref.get("source_ref"),
            "ts": ref.get("ts"),
            "snippet": ref.get("excerpt") or "",
            "facet": tag.get("facet"),
            "stance": tag.get("stance"),
        }
        identity = _moment_identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        moments.append(item)
    return moments


def _resolve_entry_tag(
    *, entry_tags: dict[str, Any], ref: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(entry_tags, dict) or not entry_tags:
        return {}
    for key in _entry_tag_lookup_keys(ref):
        candidate = entry_tags.get(key)
        if isinstance(candidate, dict):
            return candidate

    source_ref = str(ref.get("source_ref") or "").strip()
    source_id = _journal_id_from_source_ref(source_ref)
    ref_ts = _coerce_ts(ref.get("ts"))
    for candidate in entry_tags.values():
        if not isinstance(candidate, dict):
            continue
        candidate_source = str(candidate.get("source_ref") or "").strip()
        candidate_source_id = _journal_id_from_source_ref(candidate_source)
        if source_ref and candidate_source and source_ref == candidate_source:
            return candidate
        if source_id and candidate_source_id and source_id == candidate_source_id:
            return candidate
        candidate_ts = _coerce_ts(candidate.get("timestamp"))
        if (
            ref_ts
            and candidate_ts
            and abs((ref_ts - candidate_ts).total_seconds()) <= 1.0
        ):
            return candidate
    return {}


def _entry_tag_lookup_keys(ref: dict[str, Any]) -> list[str]:
    ts_raw = str(ref.get("ts") or "").strip()
    source_ref = str(ref.get("source_ref") or "").strip()
    source_id = _journal_id_from_source_ref(source_ref)
    day = int(ref.get("day") or 0)
    keys: list[str] = []
    ts_variants = _timestamp_variants(ts_raw)
    for ts in ts_variants:
        keys.append(f"{day}|{ts}")
        keys.append(ts)
    if source_ref:
        keys.append(source_ref)
    if source_id:
        keys.append(source_id)
        keys.append(f"journal:{source_id}")

    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        token = str(key or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _timestamp_variants(value: str) -> list[str]:
    token = str(value or "").strip()
    if not token:
        return []
    variants = {token}
    ts = _coerce_ts(token)
    if ts is not None:
        variants.add(ts.isoformat())
        variants.add(ts.isoformat().replace("+00:00", "Z"))
        variants.add(ts.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return sorted(variants)


def _temporal_overlap_details(
    moments_a: list[dict[str, Any]],
    moments_b: list[dict[str, Any]],
    *,
    max_days: int,
) -> tuple[float, int, list[dict[str, Any]]]:
    if not moments_a or not moments_b:
        return 0.0, 0, []

    rows_a = [
        (idx, _coerce_ts(item.get("ts")))
        for idx, item in enumerate(moments_a)
        if _coerce_ts(item.get("ts")) is not None
    ]
    rows_b = [
        (idx, _coerce_ts(item.get("ts")))
        for idx, item in enumerate(moments_b)
        if _coerce_ts(item.get("ts")) is not None
    ]
    if not rows_a or not rows_b:
        return 0.0, 0, []

    threshold = max_days * 86400
    overlaps: list[tuple[int, int, datetime, datetime]] = []
    rows_a.sort(key=lambda item: item[1] or datetime.min.replace(tzinfo=UTC))
    rows_b.sort(key=lambda item: item[1] or datetime.min.replace(tzinfo=UTC))
    left = 0
    for idx_a, ts_a in rows_a:
        if ts_a is None:
            continue
        while left < len(rows_b):
            ts_left = rows_b[left][1]
            if ts_left is None:
                left += 1
                continue
            if (ts_a - ts_left).total_seconds() > threshold:
                left += 1
                continue
            break

        nearest_pair: tuple[int, int, datetime, datetime] | None = None
        nearest_delta = float("inf")
        right = left
        while right < len(rows_b):
            idx_b, ts_b = rows_b[right]
            if ts_b is None:
                right += 1
                continue
            delta = (ts_b - ts_a).total_seconds()
            if delta > threshold:
                break
            abs_delta = abs(delta)
            if abs_delta <= threshold and abs_delta < nearest_delta:
                nearest_delta = abs_delta
                nearest_pair = (idx_a, idx_b, ts_a, ts_b)
            right += 1

        if nearest_pair is None:
            for probe in [left - 1, left]:
                if probe < 0 or probe >= len(rows_b):
                    continue
                idx_b, ts_b = rows_b[probe]
                if ts_b is None:
                    continue
                abs_delta = abs((ts_a - ts_b).total_seconds())
                if abs_delta <= threshold and abs_delta < nearest_delta:
                    nearest_delta = abs_delta
                    nearest_pair = (idx_a, idx_b, ts_a, ts_b)

        if nearest_pair:
            overlaps.append(nearest_pair)

    overlap_pairs = len(overlaps)
    baseline = max(1, min(len(rows_a), len(rows_b)))
    score = min(1.0, overlap_pairs / baseline)
    if not overlaps:
        return score, 0, []

    ts_values = [pair[2] for pair in overlaps] + [pair[3] for pair in overlaps]
    unique_a = {pair[0] for pair in overlaps}
    unique_b = {pair[1] for pair in overlaps}
    overlap_windows = [
        {
            "start": min(ts_values).isoformat(),
            "end": max(ts_values).isoformat(),
            "moment_count_a": len(unique_a),
            "moment_count_b": len(unique_b),
        }
    ]
    return score, overlap_pairs, overlap_windows


def _semantic_overlap_score(
    moments_a: list[dict[str, Any]],
    moments_b: list[dict[str, Any]],
    *,
    embedding_lookup: dict[str, list[float]] | None = None,
) -> float:
    if embedding_lookup:
        vector_score = _semantic_overlap_score_from_vectors(
            moments_a=moments_a,
            moments_b=moments_b,
            embedding_lookup=embedding_lookup,
        )
        if vector_score is not None:
            return vector_score

    tokens_a = _token_set(
        " ".join(str(item.get("snippet") or "") for item in moments_a)
    )
    tokens_b = _token_set(
        " ".join(str(item.get("snippet") or "") for item in moments_b)
    )
    if not tokens_a or not tokens_b:
        return 0.0
    union = tokens_a.union(tokens_b)
    if not union:
        return 0.0
    return len(tokens_a.intersection(tokens_b)) / len(union)


def _semantic_overlap_score_from_vectors(
    *,
    moments_a: list[dict[str, Any]],
    moments_b: list[dict[str, Any]],
    embedding_lookup: dict[str, list[float]],
) -> float | None:
    vectors_a = _vectors_for_moments(moments_a, embedding_lookup=embedding_lookup)
    vectors_b = _vectors_for_moments(moments_b, embedding_lookup=embedding_lookup)
    if not vectors_a or not vectors_b:
        return None
    centroid_a = _centroid(vectors_a)
    centroid_b = _centroid(vectors_b)
    if centroid_a is None or centroid_b is None:
        return None
    cosine = _cosine_similarity(centroid_a, centroid_b)
    if cosine is None:
        return None
    return max(0.0, min(1.0, (cosine + 1.0) / 2.0))


def _vectors_for_moments(
    moments: list[dict[str, Any]],
    *,
    embedding_lookup: dict[str, list[float]],
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for moment in moments:
        source_ref = str(moment.get("source_ref") or "").strip()
        journal_id = _journal_id_from_source_ref(source_ref)
        if not journal_id:
            continue
        vector = embedding_lookup.get(journal_id)
        if not vector:
            continue
        vectors.append(vector)
    return vectors


def _centroid(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    length = len(vectors[0])
    if length <= 0:
        return None
    total = [0.0] * length
    count = 0
    for vector in vectors:
        if len(vector) != length:
            continue
        for idx, value in enumerate(vector):
            total[idx] += float(value)
        count += 1
    if count <= 0:
        return None
    return [value / count for value in total]


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float | None:
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return None
    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    denom = norm_a * norm_b
    if denom <= 0:
        return None
    return max(-1.0, min(1.0, dot / denom))


def _facet_overlap_score(
    moments_a: list[dict[str, Any]],
    moments_b: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    facets_a = {
        str(item.get("facet") or "").strip().lower()
        for item in moments_a
        if str(item.get("facet") or "").strip()
    }
    facets_b = {
        str(item.get("facet") or "").strip().lower()
        for item in moments_b
        if str(item.get("facet") or "").strip()
    }
    if not facets_a or not facets_b:
        return 0.0, []
    union = facets_a.union(facets_b)
    if not union:
        return 0.0, []
    shared = sorted(facets_a.intersection(facets_b))
    return len(shared) / len(union), shared


def _directional_alignment_score(
    moments_a: list[dict[str, Any]],
    moments_b: list[dict[str, Any]],
) -> float:
    series_a = _weekly_stance_series(moments_a)
    series_b = _weekly_stance_series(moments_b)
    common_weeks = sorted(set(series_a.keys()).intersection(series_b.keys()))
    if len(common_weeks) >= 2:
        values_a = [series_a[key] for key in common_weeks]
        values_b = [series_b[key] for key in common_weeks]
        corr = _pearson(values_a, values_b)
        return (corr + 1.0) / 2.0
    if len(common_weeks) == 1:
        delta = abs(series_a[common_weeks[0]] - series_b[common_weeks[0]])
        return max(0.0, 1.0 - (delta / 2.0))
    return 0.0


def _weekly_stance_series(moments: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for item in moments:
        ts = _coerce_ts(item.get("ts"))
        if ts is None:
            continue
        stance = str(item.get("stance") or "").strip().lower()
        if stance == "toward":
            value = 1.0
        elif stance == "away":
            value = -1.0
        else:
            value = 0.0
        bucket = ts.strftime("%Y-%W")
        buckets.setdefault(bucket, []).append(value)
    return {key: sum(values) / max(1, len(values)) for key, values in buckets.items()}


def _pearson(values_a: list[float], values_b: list[float]) -> float:
    n = min(len(values_a), len(values_b))
    if n <= 1:
        return 0.0
    mean_a = sum(values_a) / n
    mean_b = sum(values_b) / n
    num = sum((values_a[i] - mean_a) * (values_b[i] - mean_b) for i in range(n))
    den_a = math.sqrt(sum((values_a[i] - mean_a) ** 2 for i in range(n)))
    den_b = math.sqrt(sum((values_b[i] - mean_b) ** 2 for i in range(n)))
    denom = den_a * den_b
    if denom <= 0:
        return 0.0
    return max(-1.0, min(1.0, num / denom))


def _token_set(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall((text or "").lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _moment_identity(moment: dict[str, Any]) -> str:
    source_ref = str(moment.get("source_ref") or "").strip()
    ts = str(moment.get("ts") or "").strip()
    if source_ref:
        return f"{source_ref}|{ts}"
    snippet = str(moment.get("snippet") or "").strip().lower()
    return f"{ts}|{snippet[:80]}"


def _parse_json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _coerce_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _iso(value: Any) -> str:
    ts = _coerce_ts(value)
    if ts is None:
        return ""
    return ts.isoformat()


def _iso_sort_value(value: str) -> float:
    ts = _coerce_ts(value)
    if ts is None:
        return 0.0
    return ts.timestamp()


__all__ = ["compute_cross_topic_signals", "get_life_dimensions"]
