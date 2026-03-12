from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.continuity.adapters import (
    canonicalize_anchor,
    get_continuity_policy,
    load_journal_entries_for_continuity,
)
from sakhi.apps.api.services.continuity.compiler import (
    ClassificationState,
    build_compiled_topics_index,
    classify_continuity_text,
    compile_journal_continuity,
    parse_continuity_window,
    select_compiled_topic,
)
from sakhi.apps.api.services.continuity.cross_topic import compute_cross_topic_signals
from sakhi.apps.api.services.continuity.service import CONTINUITY_SCOPE
from sakhi.apps.api.services.continuity.thresholds import (
    CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE,
)

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_TOPIC_STOPWORDS = {
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
}
_ACCEPTANCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(yes|yeah|yep|ok|okay|sure)\b",
        r"\b(i did|done|completed|implemented)\b",
        r"\b(i'?ll do|will do|let'?s do that)\b",
        r"\b(that helps|helped|makes sense|works)\b",
        r"\b(thanks|thank you)\b",
    )
]


async def build_continuity_pack(
    person_id: str,
    user_text: str,
    *,
    topic_key: str | None = None,
    window: str = "120d",
    evidence_limit: int = 8,
    scope: str = CONTINUITY_SCOPE,
) -> dict[str, Any] | None:
    if evidence_limit <= 0:
        return None

    policy = await get_continuity_policy(person_id, scope)
    if not policy.get("enabled"):
        return None

    target_anchor, classification = _select_target_anchor(user_text, topic_key)
    if not target_anchor:
        return None

    now = datetime.now(UTC)
    from_ts = now - parse_continuity_window(window)
    journal_rows = await load_journal_entries_for_continuity(
        person_id,
        from_ts=from_ts,
        to_ts=now,
        exclusions=policy.get("exclusions") or [],
    )
    compiled = compile_journal_continuity(
        person_id=person_id,
        journal_rows=journal_rows,
    )
    try:
        topic = select_compiled_topic(compiled, anchor=target_anchor, debug=False)
    except LookupError:
        return None

    surface = topic.get("surface") or {}
    if not surface.get("mirror_allowed"):
        return None
    detail_allowed = bool(surface.get("detail_allowed"))

    included_moments = _included_moments(topic)
    if not included_moments:
        return None

    evidence = _select_evidence(
        user_text=user_text,
        included_moments=included_moments,
        evidence_limit=evidence_limit,
    )
    topic_keywords = _topic_keywords_for_context(
        topic_key=target_anchor,
        topic=topic,
        included_moments=included_moments,
    )
    acknowledged_assistant_signals = await _load_acknowledged_assistant_signals(
        person_id=person_id,
        topic_keywords=topic_keywords,
    )
    history_compact = _build_history_compact(
        topic,
        included_moments,
        detail_allowed=detail_allowed,
        acknowledged_assistant_signals=acknowledged_assistant_signals,
    )
    topics_index = build_compiled_topics_index(compiled, debug=False)
    candidate_topics = _build_candidate_topics(
        user_text=user_text,
        topics=topics_index,
        selected_anchor=target_anchor,
    )
    cross_context, whole_story, life_dimensions = await compute_cross_topic_signals(
        person_id=person_id,
        selected_anchor=target_anchor,
        selected_topic=topic,
        topics=topics_index,
        window_start=from_ts.isoformat(),
        window_end=now.isoformat(),
        now=now,
    )

    return {
        "topic_key": target_anchor,
        "topic_label": topic.get("label") or target_anchor.replace("_", " ").title(),
        "window_start": from_ts.isoformat(),
        "window_end": now.isoformat(),
        "topic_confidence": float(topic.get("confidence") or 0.0),
        "classification": classification,
        "arc_compact": {
            "start_signal": _phase_signal(topic, 0, fallback="started as one continuing thread"),
            "pivots_signal": _pivot_signal(topic),
            "current_signal": _phase_signal(topic, -1, fallback="currently holding the same thread"),
            "disclaimer": "Direction is consistency over time, not success.",
        },
        "history_compact": history_compact,
        "evidence": evidence,
        "versions": {
            "taxonomy_version": compiled.get("taxonomy_version"),
            "compiler_version": compiled.get("compiler_version"),
            "threshold_profile_version": compiled.get("threshold_profile_version"),
            "inputs_hash": compiled.get("inputs_hash"),
        },
        "surface": surface,
        "exclusions_applied": bool(policy.get("exclusions")),
        "candidate_topics": candidate_topics or None,
        "cross_context": cross_context,
        "whole_story": whole_story,
        "life_dimensions": life_dimensions,
    }


def _select_target_anchor(user_text: str, explicit_topic: str | None) -> tuple[str | None, dict[str, Any]]:
    if explicit_topic:
        anchor = canonicalize_anchor(explicit_topic)
        return anchor, {
            "anchor": anchor,
            "anchor_state": ClassificationState.CONFIDENT.value,
            "reason": "explicit_topic",
        }

    classified = classify_continuity_text(user_text)
    anchor = canonicalize_anchor(classified.get("primary_anchor"))
    if anchor == "unknown":
        return None, classified
    if classified.get("anchor_state") != ClassificationState.CONFIDENT.value:
        return None, classified
    return anchor, classified


def _included_moments(topic: dict[str, Any]) -> list[dict[str, Any]]:
    event_refs = (topic.get("arc") or {}).get("event_refs") or []
    entry_tags = topic.get("entry_tags") or {}
    moments: list[dict[str, Any]] = []
    for ref in event_refs:
        key = f"{int(ref.get('day') or 0)}|{str(ref.get('ts') or '')}"
        tag = entry_tags.get(key) or {}
        moments.append(
            {
                "source_ref": ref.get("source_ref"),
                "ts": ref.get("ts"),
                "snippet": ref.get("excerpt") or "",
                "confidence": float(tag.get("confidence") or 0.0),
                "facet": tag.get("facet"),
                "decision_state": tag.get("decision_state"),
                "stance": tag.get("stance"),
            }
        )
    return moments


def _phase_signal(topic: dict[str, Any], phase_index: int, *, fallback: str) -> str:
    phases = ((topic.get("arc") or {}).get("phases") or [])
    if not phases:
        return fallback

    phase = phases[phase_index]
    stats = phase.get("stats") or {}
    dominant_tag = stats.get("dominant_tag") or {}
    if isinstance(dominant_tag, dict) and dominant_tag.get("label"):
        label = str(dominant_tag["label"])
        if phase_index == 0:
            return f"started around {label}"
        if phase_index == -1:
            return f"currently centered on {label}"
        return f"shifted toward {label}"

    density = _phase_density(phase)
    if density >= 0.12:
        descriptor = "dense"
    elif density <= 0.04:
        descriptor = "sparse"
    else:
        descriptor = "steady"

    if phase_index == 0:
        return f"started {descriptor} and exploratory"
    if phase_index == -1:
        return f"currently {descriptor} and coherent"
    return f"shifted into a {descriptor} phase"


def _pivot_signal(topic: dict[str, Any]) -> str:
    arc = topic.get("arc") or {}
    phase_count = int(arc.get("phase_count") or 0)
    pivot_count = max(0, phase_count - 1)
    if pivot_count <= 0:
        return "no visible pivot in the current window"

    middle_signal = _phase_signal(topic, 1, fallback="the thread reorganized once") if phase_count >= 3 else None
    if pivot_count == 1:
        return middle_signal or "one pivot reorganized the thread"
    return f"{pivot_count} pivots reorganized the thread"


def _phase_density(phase: dict[str, Any]) -> float:
    element_count = max(int(phase.get("element_count") or 0), 0)
    start = _coerce_ts(phase.get("start_ts"))
    end = _coerce_ts(phase.get("end_ts"))
    if not start or not end:
        return 0.0
    duration_days = max(1.0, (end - start).total_seconds() / 86400.0)
    return element_count / duration_days


def _select_evidence(
    *,
    user_text: str,
    included_moments: list[dict[str, Any]],
    evidence_limit: int,
) -> list[dict[str, Any]]:
    query_tokens = set(_tokenize(user_text))

    ranked = []
    for moment in included_moments:
        snippet = str(moment.get("snippet") or "")
        overlap = len(query_tokens.intersection(_tokenize(snippet)))
        confidence = float(moment.get("confidence") or 0.0)
        ts = str(moment.get("ts") or "")
        source_ref = str(moment.get("source_ref") or "")
        ranked.append(
            (
                -overlap,
                -confidence,
                -_iso_sort_value(ts),
                source_ref,
                {
                    "ts": ts,
                    "source_ref": source_ref,
                    "snippet": _truncate(snippet, 220),
                    "confidence": round(confidence, 4),
                },
            )
        )

    ranked.sort()
    selected = [item[-1] for item in ranked[:evidence_limit]]
    selected.sort(key=lambda item: (item["ts"], item["source_ref"]))
    return selected


def _build_history_compact(
    topic: dict[str, Any],
    included_moments: list[dict[str, Any]],
    *,
    detail_allowed: bool,
    acknowledged_assistant_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    arc = topic.get("arc") or {}
    phases = arc.get("phases") or []
    span_days = float(arc.get("span_days") or 0.0)
    element_count = int(arc.get("element_count") or len(included_moments))
    phase_count = int(arc.get("phase_count") or len(phases))
    return {
        "span_days": round(span_days, 2),
        "element_count": element_count,
        "phase_count": phase_count,
        "phase_path": _build_phase_path(phases, limit=4),
        "anchor_points": _build_history_anchors(included_moments, limit=3),
        "qualitative_mode": "detailed" if detail_allowed else "mirror_only",
        "qualitative_arc_summary": _build_qualitative_arc_summary(
            topic,
            phases=phases,
            included_moments=included_moments,
            detail_allowed=detail_allowed,
        ),
        "decision_ledger": _build_decision_ledger(
            included_moments,
            acknowledged_assistant_signals=acknowledged_assistant_signals,
        ),
    }


_CANDIDATE_TOPICS_MAX = CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.max_candidate_topics


def _build_candidate_topics(
    *,
    user_text: str,
    topics: list[dict[str, Any]],
    selected_anchor: str,
) -> list[dict[str, Any]]:
    if not topics:
        return []

    query_tokens = set(_tokenize(user_text))
    if not query_tokens:
        query_tokens = {"thread"}

    max_selected = max(1, max(int(topic.get("selected_count") or 0) for topic in topics))
    end_scores = [
        _iso_sort_value(str(((topic.get("arc") or {}).get("end_ts")) or ""))
        for topic in topics
    ]
    max_recency = max(end_scores) if end_scores else 0.0

    ranked: list[tuple[float, dict[str, Any]]] = []
    for topic in topics:
        anchor = canonicalize_anchor(topic.get("anchor"))
        if not anchor or anchor == "unknown":
            continue
        surface = topic.get("surface") or {}
        detail_allowed = bool(surface.get("detail_allowed"))
        if not detail_allowed:
            continue
        label = str(topic.get("label") or anchor.replace("_", " ").title()).strip()
        selected_count = max(0, int(topic.get("selected_count") or 0))
        confidence = float(topic.get("confidence") or 0.0)
        topic_tokens = set(_tokenize(f"{anchor} {label}"))
        overlap = len(query_tokens.intersection(topic_tokens))
        query_score = min(1.0, overlap / max(1, len(query_tokens)))
        recency_raw = _iso_sort_value(str(((topic.get("arc") or {}).get("end_ts")) or ""))
        recency_score = (recency_raw / max_recency) if max_recency > 0 else 0.0
        depth_score = selected_count / max_selected
        score = (
            0.45 * query_score
            + 0.20 * recency_score
            + 0.20 * depth_score
            + 0.15 * min(1.0, max(0.0, confidence))
        )
        ranked.append(
            (
                score,
                {
                    "topic_key": anchor,
                    "topic_label": label,
                    "score": round(score, 4),
                    "selected_count": selected_count,
                    "detail_allowed": detail_allowed,
                },
            )
        )

    ranked.sort(key=lambda item: (-item[0], -item[1]["selected_count"], item[1]["topic_key"]))
    return [item[1] for item in ranked[:_CANDIDATE_TOPICS_MAX]]


def _build_phase_path(phases: list[dict[str, Any]], *, limit: int) -> list[str]:
    if not phases:
        return []
    lines: list[str] = []
    for idx in _sample_indices(len(phases), limit):
        phase = phases[idx]
        start = _date_label(phase.get("start_ts"))
        end = _date_label(phase.get("end_ts"))
        label = _phase_tag_label(phase)
        count = int(phase.get("element_count") or 0)
        lines.append(f"{start}->{end}: {label} ({count} moments)")
    return lines


def _build_history_anchors(included_moments: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if not included_moments:
        return []
    ordered = sorted(
        included_moments,
        key=lambda item: (str(item.get("ts") or ""), str(item.get("source_ref") or "")),
    )
    anchors: list[dict[str, Any]] = []
    for idx in _sample_indices(len(ordered), limit):
        moment = ordered[idx]
        anchors.append(
            {
                "ts": str(moment.get("ts") or ""),
                "source_ref": str(moment.get("source_ref") or ""),
                "snippet": _truncate(str(moment.get("snippet") or ""), 140),
            }
        )
    return anchors


def _build_decision_ledger(
    included_moments: list[dict[str, Any]],
    *,
    acknowledged_assistant_signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for moment in included_moments:
        decision_state = str(moment.get("decision_state") or "").strip()
        stance = str(moment.get("stance") or "").strip()
        if not decision_state and not stance:
            continue
        rows.append(
            {
                "ts": str(moment.get("ts") or ""),
                "status": decision_state or "observed",
                "decision": _decision_label(decision_state, stance),
                "source": "user_journal",
                "evidence_ref": str(moment.get("source_ref") or ""),
                "note": _truncate(str(moment.get("snippet") or ""), 110),
            }
        )

    for signal in acknowledged_assistant_signals:
        rows.append(
            {
                "ts": str(signal.get("ts") or ""),
                "status": "accepted",
                "decision": f"Sakhi suggestion acknowledged: {str(signal.get('assistant_snippet') or '').strip()}",
                "source": "accepted_sakhi_suggestion",
                "evidence_ref": str(signal.get("source_ref") or "conversation_turns"),
                "note": _truncate(str(signal.get("user_ack") or ""), 110),
            }
        )

    rows.sort(key=lambda item: _iso_sort_value(str(item.get("ts") or "")))
    if len(rows) > 6:
        rows = [rows[idx] for idx in _sample_indices(len(rows), 6)]
    return rows


def _sample_indices(total: int, limit: int) -> list[int]:
    if total <= 0 or limit <= 0:
        return []
    if total <= limit:
        return list(range(total))
    if limit == 1:
        return [total - 1]
    step = (total - 1) / (limit - 1)
    return sorted({min(total - 1, round(i * step)) for i in range(limit)})


def _date_label(value: Any) -> str:
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return "unknown"


def _phase_tag_label(phase: dict[str, Any]) -> str:
    stats = phase.get("stats") or {}
    dominant = stats.get("dominant_tag") or {}
    label = str((dominant or {}).get("label") or "").strip()
    if label:
        return label
    density = _phase_density(phase)
    if density >= 0.12:
        return "dense phase"
    if density <= 0.04:
        return "sparse phase"
    return "steady phase"


def _decision_label(decision_state: str, stance: str) -> str:
    normalized = decision_state.strip().lower()
    if normalized == "resolved":
        return "resolved direction"
    if normalized == "reversed":
        return "reversed previous direction"
    if normalized in {"leaning_no", "away"}:
        return "leaning away from prior direction"
    if normalized in {"leaning_yes", "toward"}:
        return "leaning toward current direction"
    if normalized in {"questioning", "unclear"}:
        return "questioning direction"
    if stance.strip().lower() == "toward":
        return "moving toward this thread"
    if stance.strip().lower() == "away":
        return "moving away from this thread"
    return "direction under review"


def _build_qualitative_arc_summary(
    topic: dict[str, Any],
    *,
    phases: list[dict[str, Any]],
    included_moments: list[dict[str, Any]],
    detail_allowed: bool,
) -> str:
    if not phases:
        return "Thread has limited historical structure so far."

    start_label = _phase_tag_label(phases[0])
    current_label = _phase_tag_label(phases[-1])
    phase_count = int((topic.get("arc") or {}).get("phase_count") or len(phases))
    pivot_count = max(0, phase_count - 1)
    span_days = float((topic.get("arc") or {}).get("span_days") or 0.0)
    direction = str((((topic.get("arc") or {}).get("features") or {}).get("direction")) or "").strip()
    middle_labels = [
        _phase_tag_label(phase)
        for phase in phases[1:-1]
    ]
    recurring_labels = _recurring_phase_labels(phases)

    parts: list[str] = []
    pivot_phrase = "without major pivots"
    if pivot_count == 1:
        pivot_phrase = "through one pivot"
    elif pivot_count > 1:
        pivot_phrase = f"through {pivot_count} pivots"
    parts.append(
        f"It started around {start_label}, moved {pivot_phrase}, and is now centered on {current_label}."
    )

    if middle_labels:
        parts.append(f"Middle chapters cycled through {_list_phrase(middle_labels)}.")

    if recurring_labels:
        parts.append(f"A recurring pull toward {_list_phrase(recurring_labels)} keeps reappearing.")

    if direction:
        parts.append(f"The overall thread direction is {direction}.")

    if detail_allowed:
        anchors_count = len(included_moments)
        if span_days > 0 and anchors_count > 0:
            parts.append(
                f"This arc is built from {anchors_count} moments across about {span_days:.0f} days."
            )
    return _truncate(" ".join(parts), 420)


def _recurring_phase_labels(phases: list[dict[str, Any]]) -> list[str]:
    counts: dict[str, int] = {}
    for phase in phases:
        label = _phase_tag_label(phase).strip()
        if not label:
            continue
        counts[label] = counts.get(label, 0) + 1
    recurring = [label for label, count in counts.items() if count > 1]
    recurring.sort()
    return recurring[:3]


def _list_phrase(values: list[str]) -> str:
    cleaned = []
    seen = set()
    for item in values:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        cleaned.append(token)
    if not cleaned:
        return "key shifts"
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def _topic_keywords_for_context(
    *,
    topic_key: str,
    topic: dict[str, Any],
    included_moments: list[dict[str, Any]],
) -> set[str]:
    raw_parts: list[str] = [topic_key, str(topic.get("label") or "")]
    arc = topic.get("arc") or {}
    for phase in arc.get("phases") or []:
        raw_parts.append(_phase_tag_label(phase))
    for moment in included_moments[:6]:
        raw_parts.append(str(moment.get("snippet") or ""))
    tokens = {
        token
        for token in _tokenize(" ".join(raw_parts))
        if len(token) > 2 and token not in _TOPIC_STOPWORDS
    }
    return tokens


async def _load_acknowledged_assistant_signals(
    *,
    person_id: str,
    topic_keywords: set[str],
) -> list[dict[str, Any]]:
    if not topic_keywords:
        return []
    try:
        rows = await dbfetch(
            """
            SELECT role, text, created_at
            FROM conversation_turns
            WHERE user_id = $1::uuid OR person_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT 60
            """,
            person_id,
        )
    except Exception:
        return []

    turns = list(reversed(rows or []))
    signals: list[dict[str, Any]] = []
    for idx in range(1, len(turns) - 1):
        prev_row = turns[idx - 1] or {}
        current_row = turns[idx] or {}
        next_row = turns[idx + 1] or {}

        current_role = str(current_row.get("role") or "").lower()
        if current_role not in {"assistant", "sakhi"}:
            continue
        if str(prev_row.get("role") or "").lower() != "user":
            continue
        if str(next_row.get("role") or "").lower() != "user":
            continue

        prev_text = str(prev_row.get("text") or "").strip()
        current_text = str(current_row.get("text") or "").strip()
        next_text = str(next_row.get("text") or "").strip()
        if not current_text or not next_text:
            continue
        if not _matches_topic(prev_text, topic_keywords) and not _matches_topic(next_text, topic_keywords):
            continue
        if not _is_acceptance_message(next_text):
            continue

        signals.append(
            {
                "ts": _iso_value(current_row.get("created_at")) or _iso_value(next_row.get("created_at")),
                "assistant_snippet": _truncate(current_text, 120),
                "user_ack": _truncate(next_text, 120),
                "source_ref": "conversation_turns",
            }
        )

    if len(signals) > 3:
        signals = signals[-3:]
    return signals


def _matches_topic(text: str, topic_keywords: set[str]) -> bool:
    if not text:
        return False
    present = set(_tokenize(text))
    return bool(present.intersection(topic_keywords))


def _is_acceptance_message(text: str) -> bool:
    value = text.strip()
    if not value:
        return False
    if "?" in value and len(value) > 18:
        return False
    return any(pattern.search(value) for pattern in _ACCEPTANCE_PATTERNS)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _truncate(text: str, max_chars: int) -> str:
    value = (text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "…"


def _coerce_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _iso_value(value: Any) -> str:
    if isinstance(value, datetime):
        ts = value if value.tzinfo else value.replace(tzinfo=UTC)
        return ts.astimezone(UTC).isoformat()
    return ""


def _iso_sort_value(value: str) -> float:
    ts = _coerce_ts(value)
    if ts is None:
        return 0.0
    return ts.timestamp()


__all__ = ["build_continuity_pack"]
