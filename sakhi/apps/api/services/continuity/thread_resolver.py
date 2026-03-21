"""Thread-aware resolver for continuity entry attachment.

After the per-entry classifier runs, some entries are left with anchor="unknown"
because they lack strong keyword signal. These are typically follow-up entries
that use pronouns, deictic references ("it", "this screen"), or topic-specific
vocabulary without repeating the anchor keyword.

This resolver does a second pass over the classified entry list:
  1. Build confident threads from entries with anchor_state=CONFIDENT.
  2. For each unknown/unclassified entry, score it against every thread using
     multiple signals (partial candidate scores, follow-up language, term
     overlap, thread recency).
  3. Attach the entry to a thread only when one thread wins clearly (minimum
     score AND minimum margin over runner-up).
  4. Leave non-attachable entries as unresolved; never silently discard them.

Attached entries are marked with membership_role="inferred" so debug traces
can explain why they joined a thread. Unresolved entries are returned
separately for auditability.

SEMANTICS:
- source_anchor: For primary memberships, this is the resolved anchor (the thread
  the entry was attached to). For inferred entries, the original unresolved
  classification is preserved in thread_attachment.original_anchor_state.
  The "source" anchor is what the membership is attributed to in the topic.

- original_anchor_state: For inferred entries, stores the classification state
  before resolution (UNKNOWN), so downstream code can make informed choices
  about weighting. For example, _entry_confidence may wish to check this
  before trusting the UNCERTAIN state applied by inference.
"""

from __future__ import annotations

import re
from typing import Any

# ── Follow-up language signal tables ─────────────────────────────────────────
# Strong phrases: specific product/topic references that strongly imply
# continuation of a prior topic rather than a new topic.
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

# Weak words: generic deictic/anaphoric language. Present in many entries but
# in combination they raise the follow-up probability.
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

# Thread age thresholds (in relative day units, same scale as entry["day"])
_THREAD_AGE_DECAY_START = 30   # decay begins after this many days of inactivity
_THREAD_AGE_FULL_DECAY = 60    # score reaches 0 at this gap

# Scoring weights: must sum to 1.0
_W_CANDIDATE_SCORE = 0.50   # normalized raw candidate score from anchor trace
_W_FOLLOWUP = 0.20          # follow-up language signal
_W_TERM_OVERLAP = 0.20      # term overlap with thread's accumulated hits
_W_RECENCY = 0.10           # recency boost (light; only a tie-breaker)


def resolve_thread_attachments(
    inferred: list[dict[str, Any]],
    *,
    min_attachment_score: float = 0.30,
    min_margin: float = 0.15,
    thread_age_decay_days: int = _THREAD_AGE_DECAY_START,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Second-pass resolver that attaches unknown entries to confident threads.

    Processes entries in chronological order (preserving the order of
    ``inferred``, which must already be sorted by day/timestamp). As entries
    are resolved they are added to the live thread index so that later entries
    in the same pass can benefit from their attachment.

    Args:
        inferred: Classified entries from _classify_entry(), sorted by
            (day, timestamp). Entries with anchor != "unknown"/"life" are
            passed through unchanged.
        min_attachment_score: Minimum composite score for attachment.
        min_margin: Required gap between top-scoring thread and runner-up.
        thread_age_decay_days: Days of thread inactivity before decay starts.

    Returns:
        A 2-tuple:
        - resolved_inferred: All entries, with unknowns either patched with
          an inferred anchor or left with their original anchor="unknown".
        - unresolved_entries: Subset of resolved_inferred where attachment
          failed; kept visible for debug/auditability.
    """
    # Build the initial thread index from CONFIDENT entries only.
    threads: dict[str, list[dict[str, Any]]] = {}
    for item in inferred:
        if _is_confident(item):
            anchor = str(item["anchor"])
            threads.setdefault(anchor, []).append(item)

    if not threads:
        # No confident threads exist — nothing to attach to.
        unresolved = [item for item in inferred if _is_unclassified(item)]
        return inferred, unresolved

    resolved_inferred: list[dict[str, Any]] = []
    unresolved_entries: list[dict[str, Any]] = []

    for item in inferred:
        if not _is_unclassified(item):
            resolved_inferred.append(item)
            continue

        current_day = _safe_int((item.get("entry") or {}).get("day"))

        # Score against every confident thread.
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

        ranked = sorted(scores.items(), key=lambda pair: -pair[1])
        top_anchor, top_score = ranked[0] if ranked else ("", 0.0)
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = top_score - runner_up_score

        if top_score >= min_attachment_score and margin >= min_margin:
            # Attach: carry the raw candidate score for this anchor so that
            # _annotate_topic_entries can compute a reasonable confidence.
            raw_candidate_score = _raw_candidate_score_for(item, top_anchor)
            resolved_item = {
                **item,
                "anchor": top_anchor,
                "anchor_state": "UNCERTAIN",   # inferred, not directly classified
                "anchor_score": raw_candidate_score,
                "membership_role": "inferred",
                "source_anchor": item.get("anchor") or "unknown",
                "thread_attachment": {
                    "attached_to": top_anchor,
                    "score": round(top_score, 4),
                    "runner_up_score": round(runner_up_score, 4),
                    "margin": round(margin, 4),
                    "all_scores": {k: round(v, 4) for k, v in scores.items()},
                    "followup_signal": _followup_language_score(
                        str(item.get("text") or "")
                    ) > 0,
                    "reason": "thread_attached",
                    "original_anchor_state": item.get("anchor_state"),  # Preserve original classification state
                },
            }
            resolved_inferred.append(resolved_item)
            # Add to the live thread so subsequent entries can see this one.
            threads[top_anchor].append(resolved_item)
        else:
            reason = (
                "below_min_score" if top_score < min_attachment_score
                else "insufficient_margin"
            )
            unresolved_item = {
                **item,
                "thread_attachment": {
                    "attached_to": None,
                    "reason": reason,
                    "top_score": round(top_score, 4),
                    "top_anchor": top_anchor or None,
                    "runner_up_score": round(runner_up_score, 4),
                    "all_scores": {k: round(v, 4) for k, v in scores.items()},
                },
            }
            resolved_inferred.append(unresolved_item)
            unresolved_entries.append(unresolved_item)

    return resolved_inferred, unresolved_entries


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score_entry_against_thread(
    item: dict[str, Any],
    thread_anchor: str,
    thread_entries: list[dict[str, Any]],
    current_entry_day: int,
    thread_age_decay_days: int,
) -> float:
    """Compute composite attachment score for item against a specific thread.

    Signals (weighted, capped individually before weighting):
      1. Normalized raw candidate score for the thread's anchor (up to 0.50).
      2. Follow-up language score (up to 0.20).
      3. Term overlap with thread's accumulated hit set (up to 0.20).
      4. Recency boost — how recently the thread had activity (up to 0.10).

    Thread age decay is applied as a final multiplicative factor.
    """
    # Signal 1: normalized raw candidate score
    raw = _raw_candidate_score_for(item, thread_anchor)
    threshold = _anchor_threshold_for(thread_anchor)
    normalized_candidate = min(raw / max(threshold, 0.01), 1.0)
    s1 = normalized_candidate * _W_CANDIDATE_SCORE

    # Signal 2: follow-up language
    text = str(item.get("text") or "")
    s2 = _followup_language_score(text) * _W_FOLLOWUP

    # Signal 3: term overlap with thread's accumulated hits
    thread_hits = _accumulate_thread_hits(thread_entries)
    entry_hits = {h for h in (item.get("anchor_hits") or []) if h}
    if thread_hits and entry_hits:
        overlap_ratio = len(entry_hits & thread_hits) / len(thread_hits)
        s3 = overlap_ratio * _W_TERM_OVERLAP
    else:
        s3 = 0.0

    # Signal 4: recency boost
    last_day = _last_thread_day(thread_entries)
    if last_day is not None and current_entry_day >= last_day:
        gap = current_entry_day - last_day
        # Max boost when gap=0; decays linearly to 0 at thread_age_decay_days.
        recency_ratio = max(0.0, 1.0 - gap / max(thread_age_decay_days, 1))
        s4 = recency_ratio * _W_RECENCY
    else:
        s4 = 0.0

    raw_score = s1 + s2 + s3 + s4

    # Thread age decay: multiplicative reduction for very cold threads.
    if last_day is not None:
        gap = max(0, current_entry_day - last_day)
        if gap > thread_age_decay_days:
            extra = gap - thread_age_decay_days
            decay_range = max(_THREAD_AGE_FULL_DECAY - thread_age_decay_days, 1)
            decay_factor = max(0.0, 1.0 - extra / decay_range)
            raw_score *= decay_factor

    return round(raw_score, 4)


def _followup_language_score(text: str) -> float:
    """Score the degree of follow-up/deictic language in text.

    Strong phrases (specific feature/topic references) contribute 0.8 each.
    Weak words (generic pronouns/deictics) contribute 0.15 each.
    Score is capped at 1.0.
    """
    strong_count = sum(
        1 for phrase in _STRONG_FOLLOWUP_PHRASES if _phrase_present(text, phrase)
    )
    weak_count = sum(
        1 for word in _WEAK_FOLLOWUP_WORDS if _phrase_present(text, word)
    )
    strong_score = min(strong_count * 0.8, 1.0)
    weak_score = min(weak_count * 0.15, 0.45)
    # Use strong if present; otherwise fall back to weak
    return round(min(strong_score if strong_score > 0 else weak_score, 1.0), 4)


def _accumulate_thread_hits(thread_entries: list[dict[str, Any]]) -> set[str]:
    """Collect all anchor_hits across all thread entries into one set.

    Alias hits (prefixed with "alias:") are excluded; they are not useful
    for term-overlap comparison against a new entry's raw hit set.
    """
    hits: set[str] = set()
    for entry in thread_entries:
        for hit in entry.get("anchor_hits") or []:
            h = str(hit or "").strip()
            if h and not h.startswith("alias:"):
                hits.add(h)
    return hits


def _raw_candidate_score_for(item: dict[str, Any], anchor: str) -> float:
    """Extract the raw candidate score for ``anchor`` from the entry's trace.

    Even entries classified as UNKNOWN have a candidates list with partial
    scores from the scoring pass. This extracts that partial score so we can
    use it as a normalized attachment signal.
    """
    anchor_trace = item.get("anchor_trace") or {}
    for candidate in anchor_trace.get("candidates") or []:
        if str(candidate.get("key") or "") == anchor:
            return float(candidate.get("score") or 0.0)
    return 0.0


def _last_thread_day(thread_entries: list[dict[str, Any]]) -> int | None:
    """Return the highest day value seen across all entries in a thread."""
    days = [
        _safe_int((e.get("entry") or {}).get("day"))
        for e in thread_entries
        if (e.get("entry") or {}).get("day") is not None
    ]
    return max(days) if days else None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_confident(item: dict[str, Any]) -> bool:
    anchor = str(item.get("anchor") or "").strip()
    state = str(item.get("anchor_state") or "").upper()
    return bool(anchor) and anchor not in {"unknown", "life"} and state == "CONFIDENT"


def _is_unclassified(item: dict[str, Any]) -> bool:
    anchor = str(item.get("anchor") or "").strip()
    return not anchor or anchor in {"unknown", "life"}


def _phrase_present(text: str, phrase: str) -> bool:
    """Check if ``phrase`` appears as a whole word/phrase in ``text``."""
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def _anchor_threshold_for(anchor: str) -> float:
    """Return the minimum score threshold for ``anchor``.

    Imported lazily to avoid circular imports with simulation_continuity.
    """
    from sakhi.apps.api.services.continuity.taxonomy import SIMULATION_CONTINUITY_TAXONOMY
    from sakhi.apps.api.services.continuity.thresholds import SIMULATION_CONTINUITY_THRESHOLD_PROFILE

    base = SIMULATION_CONTINUITY_THRESHOLD_PROFILE.anchor_min_score
    override = SIMULATION_CONTINUITY_TAXONOMY.anchor_min_score(anchor)
    return max(base, override)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


__all__ = ["resolve_thread_attachments"]