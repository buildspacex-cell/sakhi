"""LLM enrichment for continuity entries.

Runs as a background worker job (continuity_enrichment) after a turn is
ingested. Closes two gaps in the lexical classification pipeline:

  Phase 1.1 — Hybrid anchor classification
    When the lexical classifier returns anchor='unknown', call an LLM to infer
    the topic. The inferred anchor is stored in continuity_personal_taxonomy so
    future entries on the same topic are recognised without another LLM call.
    The continuity_labels record is patched with the inferred anchor so the next
    compile pass picks it up as a hint.

  Phase 1.2 — LLM decision state inference
    When decision_state is None (lexical cues missed the state), a lightweight
    LLM call infers one of the valid states from semantic meaning.

  Phase 2.2 — Affective scalar
    Derives an emotion-based scalar from the existing regex emotion tagger and
    stores it in continuity_labels.affective_scalar. No LLM call needed here.

  Phase 2.1 — Epistemic state
    Detects epistemic transitions ("I used to think…", "turns out…") via a
    lightweight LLM call and stores in continuity_labels.epistemic_state.

All DB writes are best-effort — failures are logged but never raise.
"""

from __future__ import annotations

import logging
from typing import Any

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.continuity.personal_taxonomy import (
    canonicalise_anchor,
    update_continuity_label_anchor,
    upsert_continuity_label_enrichment,
    upsert_personal_taxonomy,
)
from sakhi.apps.worker.utils.emotion import extract_emotion

LOGGER = logging.getLogger(__name__)

_VALID_DECISION_STATES = frozenset({
    "questioning", "leaning_yes", "leaning_no",
    "committed", "deferred", "reversed", "resolved",
})

_VALID_EPISTEMIC_STATES = frozenset({
    "certain", "uncertain", "updating", "contradicting", "resolved",
})

_AFFECTIVE_SCALAR_MAP: dict[str, float] = {
    "happy":       0.8,
    "calm":        0.5,
    "neutral":     0.0,
    "confused":   -0.2,
    "tired":      -0.4,
    "anxious":    -0.5,
    "sad":        -0.6,
    "frustrated": -0.6,
    "scared":     -0.7,
    "overwhelmed": -0.8,
}

_DECISION_STATE_PROMPT = """\
Classify the writer's decision state about the main topic in this journal entry.
Choose exactly one label from: questioning, leaning_yes, leaning_no, committed, deferred, reversed, resolved
If no clear decision state is present, reply: unknown

Journal entry:
{text}

Reply with the single label only. No explanation."""

_ANCHOR_PROMPT = """\
Identify the single main topic of this journal entry in 1-3 words (snake_case, e.g. job_search, health_anxiety, side_project).
If no clear topic exists, reply: unknown

Journal entry:
{text}

Reply with the topic key only. No explanation."""

_EPISTEMIC_STATE_PROMPT = """\
Classify the writer's epistemic state (certainty/belief) about the main topic in this journal entry.
Choose exactly one label from: certain, uncertain, updating, contradicting, resolved
- certain: writer is confident and clear
- uncertain: writer is unsure, doubting, or confused
- updating: writer is revising a prior belief ("I used to think", "turns out", "I now see")
- contradicting: writer holds two opposing views simultaneously
- resolved: belief is settled
If none apply, reply: unknown

Journal entry:
{text}

Reply with the single label only. No explanation."""


async def enrich_entry_continuity(
    person_id: str,
    entry_id: str,
    text: str,
    current_anchor: str | None = None,
) -> dict[str, Any]:
    """Run all enrichment passes for a single continuity entry.

    Safe to call multiple times — all writes are idempotent upserts/updates.
    Returns a summary of what was inferred.
    """
    if not text or not text.strip():
        return {}

    result: dict[str, Any] = {}

    # ── Affective scalar (no LLM needed) ─────────────────────────────────────
    affective_scalar = _compute_affective_scalar(text)
    result["affective_scalar"] = affective_scalar

    # ── Anchor inference (Phase 1.1) ──────────────────────────────────────────
    inferred_anchor: str | None = None
    anchor_is_unknown = not current_anchor or current_anchor.strip().lower() in (
        "unknown", "", "none",
    )

    if anchor_is_unknown:
        inferred_anchor = await _llm_infer_anchor(text)
        if inferred_anchor:
            result["inferred_anchor"] = inferred_anchor
            await upsert_personal_taxonomy(person_id, inferred_anchor, _anchor_to_label(inferred_anchor))
            await update_continuity_label_anchor(
                person_id,
                entry_id,
                inferred_anchor,
                affective_scalar=affective_scalar,
            )
            LOGGER.info(
                "[ContinuityEnrich] anchor inferred person=%s entry=%s anchor=%s",
                person_id, entry_id, inferred_anchor,
            )
            return result  # anchor + affective written; decision/epistemic in next pass

    # ── Decision state inference (Phase 1.2) ─────────────────────────────────
    decision_state = await _llm_infer_decision_state(text)
    if decision_state:
        result["decision_state"] = decision_state

    # ── Epistemic state inference (Phase 2.1) ────────────────────────────────
    epistemic_state = await _llm_infer_epistemic_state(text)
    if epistemic_state:
        result["epistemic_state"] = epistemic_state

    # ── Write enrichment columns ──────────────────────────────────────────────
    if decision_state or epistemic_state or affective_scalar is not None:
        await upsert_continuity_label_enrichment(
            person_id,
            entry_id,
            decision_state=decision_state,
            epistemic_state=epistemic_state,
            affective_scalar=affective_scalar,
        )
        LOGGER.info(
            "[ContinuityEnrich] enriched person=%s entry=%s decision=%s epistemic=%s affective=%.2f",
            person_id, entry_id, decision_state, epistemic_state, affective_scalar or 0.0,
        )

    return result


# ── Internal helpers ──────────────────────────────────────────────────────────

def _compute_affective_scalar(text: str) -> float:
    """Map emotion label to a -1.0 … +1.0 scalar."""
    label = extract_emotion(text)
    return _AFFECTIVE_SCALAR_MAP.get(label, 0.0)


async def _llm_infer_anchor(text: str) -> str | None:
    """Call gpt-4o-mini to infer a topic anchor. Returns None on failure/unknown."""
    try:
        raw: str = await call_llm(
            _ANCHOR_PROMPT.format(text=text[:800]),
            model="gpt-4o-mini",
        )
        candidate = canonicalise_anchor((raw or "").strip().split()[0] if raw else "")
        if not candidate or candidate == "unknown":
            return None
        return candidate
    except Exception as exc:
        LOGGER.warning("[ContinuityEnrich] anchor LLM failed: %s", exc)
        return None


async def _llm_infer_decision_state(text: str) -> str | None:
    """Call gpt-4o-mini to infer decision state. Returns None on failure/unknown."""
    try:
        raw: str = await call_llm(
            _DECISION_STATE_PROMPT.format(text=text[:800]),
            model="gpt-4o-mini",
        )
        candidate = (raw or "").strip().lower().split()[0] if raw else ""
        if candidate in _VALID_DECISION_STATES:
            return candidate
        return None
    except Exception as exc:
        LOGGER.warning("[ContinuityEnrich] decision_state LLM failed: %s", exc)
        return None


async def _llm_infer_epistemic_state(text: str) -> str | None:
    """Call gpt-4o-mini to infer epistemic state. Returns None on failure/unknown."""
    try:
        raw: str = await call_llm(
            _EPISTEMIC_STATE_PROMPT.format(text=text[:800]),
            model="gpt-4o-mini",
        )
        candidate = (raw or "").strip().lower().split()[0] if raw else ""
        if candidate in _VALID_EPISTEMIC_STATES:
            return candidate
        return None
    except Exception as exc:
        LOGGER.warning("[ContinuityEnrich] epistemic_state LLM failed: %s", exc)
        return None


def _anchor_to_label(anchor: str) -> str:
    """Convert snake_case anchor key to a readable label."""
    return anchor.replace("_", " ").title()
