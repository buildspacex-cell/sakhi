"""Thread-aware resolver for continuity entry attachment.

After the per-entry classifier runs, some entries are left with anchor="unknown"
because they lack strong keyword signal. These are usually follow-up entries
that continue an already-active thread without repeating the anchor name.

The resolver now uses a two-layer model:
  1. Build confident threads from CONFIDENT entries.
  2. For each unresolved entry, score it against all live threads.
  3. If the best thread clears the attachment threshold, attach it there.
  4. If another thread is nearly as plausible, attach that too as contextual
     overlap instead of forcing a single winner.
  5. If nothing clears the threshold, keep the entry unresolved for auditability.

This keeps the strict primary anchor classifier intact while allowing a
follow-up entry to belong to more than one thread when the evidence is close.
"""

from __future__ import annotations

import re
from typing import Any

_STRONG_FOLLOWUP_PHRASES: tuple[str, ...] = (
    "deep reflect",
    "whole story",
    "my story",
    "this feature",
    "the screen",
    "the app",
    "this screen",
    "continuity",
    "the product",
    "this product",
    "the reflection",
    "this reflection",
    "the topic",
    "that topic",
)

_WEAK_FOLLOWUP_WORDS: tuple[str, ...] = (
    "it",
    "this",
    "that",
    "these",
    "those",
    "we want",
    "we need",
    "i want",
    "building on",
    "following up",
    "as i said",
    "like i mentioned",
    "going back to",
    "back to",
)

_THREAD_AGE_DECAY_START = 30
_THREAD_AGE_FULL_DECAY = 60

_W_CANDIDATE_SCORE = 0.45
_W_FOLLOWUP = 0.20
_W_TERM_OVERLAP = 0.25
_W_RECENCY = 0.10

_SECONDARY_ATTACHMENT_RATIO = 0.82
_SECONDARY_ATTACHMENT_MARGIN = 0.08
_MAX_CONTEXTUAL_ATTACHMENTS = 1

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_TOKEN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "they",
    "them",
    "then",
    "from",
    "into",
    "about",
    "have",
    "been",
    "were",
    "what",
    "when",
    "where",
    "which",
    "would",
    "could",
    "should",
    "there",
    "their",
    "just",
    "only",
    "really",
    "also",
}


def resolve_thread_attachments(
    inferred: list[dict[str, Any]],
    *,
    min_attachment_score: float = 0.18,
    min_margin: float = 0.15,
    thread_age_decay_days: int = _THREAD_AGE_DECAY_START,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Second-pass resolver that attaches low-signal entries to live threads."""
    threads: dict[str, list[dict[str, Any]]] = {}
    for item in inferred:
        if _is_confident(item):
            anchor = str(item["anchor"])
            threads.setdefault(anchor, []).append(item)

    if not threads:
        unresolved = [item for item in inferred if _is_unclassified(item)]
        return inferred, unresolved

    resolved_inferred: list[dict[str, Any]] = []
    unresolved_entries: list[dict[str, Any]] = []

    for item in inferred:
        if not _is_unclassified(item):
            resolved_inferred.append(item)
            continue

        current_day = _safe_int((item.get("entry") or {}).get("day"))
        scores: dict[str, float] = {
            thread_anchor: _score_entry_against_thread(
                item=item,
                thread_anchor=thread_anchor,
                thread_entries=thread_entries,
                current_entry_day=current_day,
                thread_age_decay_days=thread_age_decay_days,
            )
            for thread_anchor, thread_entries in threads.items()
        }

        ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
        top_anchor, top_score = ranked[0] if ranked else ("", 0.0)
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = top_score - runner_up_score

        if top_score < min_attachment_score:
            unresolved_item = {
                **item,
                "contextual_attachments": [],
                "thread_attachment": {
                    "attached_to": None,
                    "reason": "below_min_score",
                    "top_score": round(top_score, 4),
                    "top_anchor": top_anchor or None,
                    "runner_up_score": round(runner_up_score, 4),
                    "all_scores": {k: round(v, 4) for k, v in scores.items()},
                },
            }
            resolved_inferred.append(unresolved_item)
            unresolved_entries.append(unresolved_item)
            continue

        contextual_attachments = _secondary_thread_attachments(
            item=item,
            ranked=ranked,
            top_anchor=top_anchor,
            top_score=top_score,
            min_attachment_score=min_attachment_score,
            min_margin=min_margin,
        )
        raw_candidate_score = _raw_candidate_score_for(item, top_anchor)
        resolved_item = {
            **item,
            "anchor": top_anchor,
            "anchor_state": "UNCERTAIN",
            "anchor_score": raw_candidate_score,
            "membership_role": "inferred",
            "source_anchor": item.get("anchor") or "unknown",
            "contextual_attachments": contextual_attachments,
            "thread_attachment": {
                "attached_to": top_anchor,
                "contextual_anchors": [
                    str(attachment.get("anchor") or "")
                    for attachment in contextual_attachments
                    if attachment.get("anchor")
                ],
                "score": round(top_score, 4),
                "runner_up_score": round(runner_up_score, 4),
                "margin": round(margin, 4),
                "all_scores": {k: round(v, 4) for k, v in scores.items()},
                "followup_signal": _followup_language_score(str(item.get("text") or "")) > 0,
                "reason": (
                    "thread_attached_multi"
                    if contextual_attachments
                    else "thread_attached"
                ),
                "original_anchor_state": item.get("anchor_state"),
            },
        }
        resolved_inferred.append(resolved_item)
        threads.setdefault(top_anchor, []).append(resolved_item)
        for attachment in contextual_attachments:
            attachment_anchor = str(attachment.get("anchor") or "").strip()
            if attachment_anchor:
                threads.setdefault(attachment_anchor, []).append(resolved_item)

    return resolved_inferred, unresolved_entries


def _score_entry_against_thread(
    item: dict[str, Any],
    thread_anchor: str,
    thread_entries: list[dict[str, Any]],
    current_entry_day: int,
    thread_age_decay_days: int,
) -> float:
    raw = _raw_candidate_score_for(item, thread_anchor)
    threshold = _anchor_threshold_for(thread_anchor)
    normalized_candidate = min(raw / max(threshold, 0.01), 1.0)
    s1 = normalized_candidate * _W_CANDIDATE_SCORE

    text = str(item.get("text") or "")
    s2 = _followup_language_score(text) * _W_FOLLOWUP

    thread_terms = _accumulate_thread_terms(thread_entries, thread_anchor)
    entry_terms = _entry_terms_for(item, thread_anchor)
    if thread_terms and entry_terms:
        overlap_ratio = len(entry_terms & thread_terms) / max(1, len(entry_terms))
        s3 = overlap_ratio * _W_TERM_OVERLAP
    else:
        s3 = 0.0

    last_day = _last_thread_day(thread_entries)
    if last_day is not None and current_entry_day >= last_day:
        gap = current_entry_day - last_day
        recency_ratio = max(0.0, 1.0 - gap / max(thread_age_decay_days, 1))
        s4 = recency_ratio * _W_RECENCY
    else:
        s4 = 0.0

    raw_score = s1 + s2 + s3 + s4

    if last_day is not None:
        gap = max(0, current_entry_day - last_day)
        if gap > thread_age_decay_days:
            extra = gap - thread_age_decay_days
            decay_range = max(_THREAD_AGE_FULL_DECAY - thread_age_decay_days, 1)
            decay_factor = max(0.0, 1.0 - extra / decay_range)
            raw_score *= decay_factor

    return round(raw_score, 4)


def _followup_language_score(text: str) -> float:
    strong_count = sum(
        1 for phrase in _STRONG_FOLLOWUP_PHRASES if _phrase_present(text, phrase)
    )
    weak_count = sum(
        1 for word in _WEAK_FOLLOWUP_WORDS if _phrase_present(text, word)
    )
    strong_score = min(strong_count * 0.8, 1.0)
    weak_score = min(weak_count * 0.15, 0.45)
    return round(min(strong_score if strong_score > 0 else weak_score, 1.0), 4)


def _secondary_thread_attachments(
    *,
    item: dict[str, Any],
    ranked: list[tuple[str, float]],
    top_anchor: str,
    top_score: float,
    min_attachment_score: float,
    min_margin: float,
) -> list[dict[str, Any]]:
    if not ranked or top_score < min_attachment_score:
        return []

    contextual: list[dict[str, Any]] = []
    for anchor, score in ranked[1:]:
        if score < min_attachment_score:
            continue
        if (top_score - score) > max(min_margin, _SECONDARY_ATTACHMENT_MARGIN) and (
            score / max(top_score, 0.01)
        ) < _SECONDARY_ATTACHMENT_RATIO:
            continue
        contextual.append(
            {
                "anchor": anchor,
                "score": round(score, 4),
                "raw_candidate_score": round(_raw_candidate_score_for(item, anchor), 4),
                "candidate_hits": _candidate_hits_for(item, anchor),
            }
        )
        if len(contextual) >= _MAX_CONTEXTUAL_ATTACHMENTS:
            break
    return contextual


def _accumulate_thread_terms(
    thread_entries: list[dict[str, Any]],
    thread_anchor: str,
) -> set[str]:
    terms: set[str] = set()
    for entry in thread_entries:
        for hit in _candidate_hits_for(entry, thread_anchor):
            if hit and not hit.startswith("alias:"):
                terms.add(hit)
        terms.update(_tokenize_terms(str(entry.get("text") or "")))
    return terms


def _entry_terms_for(item: dict[str, Any], anchor: str) -> set[str]:
    return {
        *[
            hit
            for hit in _candidate_hits_for(item, anchor)
            if hit and not hit.startswith("alias:")
        ],
        *_tokenize_terms(str(item.get("text") or "")),
    }


def _candidate_hits_for(item: dict[str, Any], anchor: str) -> list[str]:
    anchor_trace = item.get("anchor_trace") or {}
    winner = anchor_trace.get("winner") or {}
    if str(winner.get("key") or "") == anchor:
        return [str(hit) for hit in (winner.get("hits") or []) if str(hit or "").strip()]
    for candidate in anchor_trace.get("candidates") or []:
        if str(candidate.get("key") or "") == anchor:
            return [str(hit) for hit in (candidate.get("hits") or []) if str(hit or "").strip()]
    return [str(hit) for hit in (item.get("anchor_hits") or []) if str(hit or "").strip()]


def _raw_candidate_score_for(item: dict[str, Any], anchor: str) -> float:
    anchor_trace = item.get("anchor_trace") or {}
    winner = anchor_trace.get("winner") or {}
    if str(winner.get("key") or "") == anchor:
        return float(winner.get("score") or 0.0)
    for candidate in anchor_trace.get("candidates") or []:
        if str(candidate.get("key") or "") == anchor:
            return float(candidate.get("score") or 0.0)
    return 0.0


def _tokenize_terms(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall((text or "").lower())
        if len(token) >= 4 and token not in _TOKEN_STOPWORDS
    }


def _last_thread_day(thread_entries: list[dict[str, Any]]) -> int | None:
    days = [
        _safe_int((e.get("entry") or {}).get("day"))
        for e in thread_entries
        if (e.get("entry") or {}).get("day") is not None
    ]
    return max(days) if days else None


def _is_confident(item: dict[str, Any]) -> bool:
    anchor = str(item.get("anchor") or "").strip()
    state = str(item.get("anchor_state") or "").upper()
    return bool(anchor) and anchor not in {"unknown", "life"} and state == "CONFIDENT"


def _is_unclassified(item: dict[str, Any]) -> bool:
    anchor = str(item.get("anchor") or "").strip()
    return not anchor or anchor in {"unknown", "life"}


def _phrase_present(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def _anchor_threshold_for(anchor: str) -> float:
    from sakhi.apps.api.services.continuity.taxonomy import SIMULATION_CONTINUITY_TAXONOMY
    from sakhi.apps.api.services.continuity.thresholds import (
        SIMULATION_CONTINUITY_THRESHOLD_PROFILE,
    )

    base = SIMULATION_CONTINUITY_THRESHOLD_PROFILE.anchor_min_score
    override = SIMULATION_CONTINUITY_TAXONOMY.anchor_min_score(anchor)
    return max(base, override)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


__all__ = ["resolve_thread_attachments"]
