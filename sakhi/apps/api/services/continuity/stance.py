"""Stance extraction and shift detection for the 'What Changed' signal.

A 'stance' is what a person is currently optimizing for on a topic.
Eight targets cover the space of meaningful shifts:

  quality        getting it right, thoroughness, depth
  speed          moving fast, shipping, momentum
  stability      reducing risk, security, predictability
  relationships  connection, trust, collaboration, people
  autonomy       independence, control, ownership, agency
  learning       exploration, understanding, growth
  impact         outcomes, results, significance
  simplicity     reducing complexity, clarity, focus

A stance shift is detected when the most recent N stances on a topic
diverge from the dominant stance in the prior window — meaning the
person has quietly changed what they care most about without explicitly
saying so.
"""

from __future__ import annotations

import logging
from typing import Any

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.core.llm import call_llm

LOGGER = logging.getLogger(__name__)

VALID_STANCES = frozenset({
    "quality",
    "speed",
    "stability",
    "relationships",
    "autonomy",
    "learning",
    "impact",
    "simplicity",
})

# Minimum stances in the prior window to make a comparison worth surfacing.
_MIN_PRIOR_WINDOW = 2
# How many recent stances must agree before we call it a shift.
_SHIFT_CONFIRM_COUNT = 2
# Days to look back for prior window comparison.
_PRIOR_WINDOW_DAYS = 14

_STANCE_PROMPT = """\
A person is writing about a topic in their life. What are they currently optimizing for?

Choose ONE from this list:
- quality      (getting it right, thoroughness, depth, doing it well)
- speed        (moving fast, shipping, momentum, getting it done)
- stability    (reducing risk, security, predictability, not breaking things)
- relationships (connection, trust, collaboration, people)
- autonomy     (independence, control, ownership, agency)
- learning     (exploration, understanding, growth, figuring things out)
- impact       (outcomes, results, significance, what it produces)
- simplicity   (reducing complexity, clarity, focus)

If no clear optimization target is present, reply: none

Text:
{text}

Reply with the single label only. No explanation."""


async def extract_stance(text: str) -> str | None:
    """Call LLM to extract optimization stance from a turn of text.

    Returns one of VALID_STANCES or None.
    """
    if not text or not text.strip():
        return None
    try:
        raw: str = await call_llm(
            _STANCE_PROMPT.format(text=text[:600]),
            model="gpt-4o-mini",
        )
        candidate = (raw or "").strip().lower().split()[0] if raw else ""
        if candidate in VALID_STANCES:
            return candidate
        return None
    except Exception as exc:
        LOGGER.warning("[Stance] LLM extraction failed: %s", exc)
        return None


async def store_stance(
    *,
    person_id: str,
    topic_key: str,
    stance: str,
    confidence: float = 0.5,
    entry_id: str | None = None,
    source_text: str = "",
) -> None:
    """Persist a stance observation to continuity_stance_history."""
    if stance not in VALID_STANCES:
        return
    preview = (source_text or "").strip()[:200]
    try:
        await dbexec(
            """
            INSERT INTO continuity_stance_history
                (person_id, topic_key, stance, confidence, entry_id, source_preview)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            person_id,
            topic_key,
            stance,
            float(confidence),
            entry_id,
            preview or None,
        )
    except Exception as exc:
        LOGGER.warning("[Stance] store failed person=%s topic=%s: %s", person_id, topic_key, exc)


async def detect_stance_shift(
    person_id: str,
    topic_key: str,
) -> dict[str, Any] | None:
    """Compare recent stances to the prior 14-day window.

    Returns a shift dict if a meaningful change is detected, otherwise None:
      {"from": "quality", "to": "speed", "confidence": 0.7, "detected_at": "..."}
    """
    try:
        rows = await dbfetch(
            """
            SELECT stance, confidence, detected_at
            FROM continuity_stance_history
            WHERE person_id = $1 AND topic_key = $2
              AND detected_at >= NOW() - INTERVAL '14 days'
            ORDER BY detected_at DESC
            LIMIT 20
            """,
            person_id,
            topic_key,
        )
    except Exception as exc:
        LOGGER.warning("[Stance] shift query failed person=%s topic=%s: %s", person_id, topic_key, exc)
        return None

    if not rows or len(rows) < _MIN_PRIOR_WINDOW + _SHIFT_CONFIRM_COUNT:
        return None

    # Most recent _SHIFT_CONFIRM_COUNT stances — these are the "current" signal
    recent = [str(r["stance"]) for r in rows[:_SHIFT_CONFIRM_COUNT]]
    # Remaining stances — the "prior window"
    prior = [str(r["stance"]) for r in rows[_SHIFT_CONFIRM_COUNT:]]

    if len(prior) < _MIN_PRIOR_WINDOW:
        return None

    # Recent must all agree (same stance) to call it a shift
    if len(set(recent)) != 1:
        return None
    current_stance = recent[0]

    # Prior window dominant stance
    prior_counts: dict[str, int] = {}
    for s in prior:
        prior_counts[s] = prior_counts.get(s, 0) + 1
    prior_dominant = max(prior_counts, key=lambda k: prior_counts[k])

    if current_stance == prior_dominant:
        return None  # No shift

    prior_majority = prior_counts[prior_dominant] / len(prior)
    if prior_majority < 0.5:
        return None  # Prior window was too mixed to make a meaningful comparison

    detected_at = str(rows[0]["detected_at"]) if rows else ""
    confidence = round(prior_majority * 0.9, 2)  # Scale slightly — prior dominance × 0.9

    return {
        "from": prior_dominant,
        "to": current_stance,
        "confidence": confidence,
        "detected_at": detected_at,
    }


async def get_morning_stance_shift(person_id: str) -> dict[str, Any] | None:
    """Return the most notable stance shift across all topics for a person.

    Queries distinct topic_keys with recent stance history, checks each for
    a shift, and returns the first one found. Used for morning review.
    """
    try:
        rows = await dbfetch(
            """
            SELECT DISTINCT topic_key
            FROM continuity_stance_history
            WHERE person_id = $1
              AND detected_at >= NOW() - INTERVAL '14 days'
            ORDER BY topic_key
            LIMIT 10
            """,
            person_id,
        )
    except Exception as exc:
        LOGGER.warning("[Stance] morning shift query failed person=%s: %s", person_id, exc)
        return None

    for row in rows:
        topic_key = str(row["topic_key"])
        shift = await detect_stance_shift(person_id, topic_key)
        if shift:
            shift["topic_key"] = topic_key
            return shift

    return None


async def extract_and_store_stance(
    *,
    person_id: str,
    topic_key: str,
    text: str,
    entry_id: str | None = None,
) -> str | None:
    """Convenience: extract stance from text and persist it. Returns detected stance."""
    stance = await extract_stance(text)
    if stance:
        await store_stance(
            person_id=person_id,
            topic_key=topic_key,
            stance=stance,
            confidence=0.6,
            entry_id=entry_id,
            source_text=text,
        )
    return stance


__all__ = [
    "VALID_STANCES",
    "extract_stance",
    "store_stance",
    "detect_stance_shift",
    "extract_and_store_stance",
]
