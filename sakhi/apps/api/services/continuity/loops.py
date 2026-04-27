"""Open Loops Ledger — extraction, storage, resolution, and retrieval.

Two loop types:
  open_decision           Active deliberations: "should I take this role?"
  conversation_commitment Things committed to in conversation: "I'll reach out by Friday"

Explicit task management (todos, reminders set intentionally) is out of scope.
These are loops extracted from thinking-out-loud — the person didn't set them,
Sakhi witnessed them.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.core.llm import call_llm

LOGGER = logging.getLogger(__name__)

_MAX_OPEN_LOOPS = 10  # per person cap on surfaced open loops
_STALE_THRESHOLD_DAYS = 3  # loops older than this are considered stale

_DECISION_EXTRACT_PROMPT = """\
Read this conversation turn and extract any open decisions the person is still weighing.

An open decision is something they haven't resolved yet — they're still considering, still unsure, still thinking. NOT things they've already decided or completed.

Examples of open decisions:
- "whether to take the new role"
- "which investor to go with"
- "whether to hire the candidate now or wait"

Return a JSON array of short plain-English decision descriptions (1 sentence max each).
If no open decisions are present, return [].

Text:
{text}

Return JSON array only. No explanation."""

_COMMITMENT_EXTRACT_PROMPT = """\
Read this conversation turn and extract any commitments the person has made — things they explicitly said they will do, need to do, or intend to do.

A commitment sounds like: "I'll...", "I need to...", "I should...", "I'm going to...", "by [date]..."

NOT vague intentions ("I want to someday") — only concrete commitments with implied near-term action.

Examples:
- "reach out to James before the end of the week"
- "decide on the pricing model by Friday"
- "send the proposal to Sarah"

Return a JSON array of short plain-English commitment descriptions (1 sentence max each).
If no commitments are present, return [].

Text:
{text}

Return JSON array only. No explanation."""

_RESOLUTION_DETECT_PROMPT = """\
Read this conversation turn. Has the person resolved or completed any of these open items?

Open items:
{items}

A resolution sounds like: "I decided...", "we went with...", "done", "sent it", "I took the role", "I told them no."

Return a JSON array of the EXACT item strings that are now resolved.
If none are resolved, return [].

Text:
{text}

Return JSON array only. No explanation."""


def _parse_llm_list(raw: str) -> list[str]:
    """Parse a JSON array from LLM output. Returns empty list on failure."""
    if not raw:
        return []
    text = raw.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return []


async def extract_decisions(text: str) -> list[str]:
    """Extract open decision descriptions from a turn of text."""
    if not text or not text.strip():
        return []
    try:
        raw = await call_llm(
            _DECISION_EXTRACT_PROMPT.format(text=text[:800]),
            model="gpt-4o-mini",
        )
        return _parse_llm_list(raw)[:5]  # cap per turn
    except Exception as exc:
        LOGGER.warning("[Loops] decision extraction failed: %s", exc)
        return []


async def extract_commitments(text: str) -> list[str]:
    """Extract conversation commitments from a turn of text."""
    if not text or not text.strip():
        return []
    try:
        raw = await call_llm(
            _COMMITMENT_EXTRACT_PROMPT.format(text=text[:800]),
            model="gpt-4o-mini",
        )
        return _parse_llm_list(raw)[:5]  # cap per turn
    except Exception as exc:
        LOGGER.warning("[Loops] commitment extraction failed: %s", exc)
        return []


async def detect_resolutions(person_id: str, text: str) -> list[str]:
    """Check if any open loops are resolved by the current turn. Returns resolved loop IDs."""
    if not text or not text.strip():
        return []

    # Load open loops as candidate items
    open_loops = await get_open_loops(person_id, status="open")
    all_loops = open_loops.get("decisions", []) + open_loops.get("commitments", [])
    if not all_loops:
        return []

    items_block = "\n".join(f"- [{loop['id']}] {loop['topic']}" for loop in all_loops)
    try:
        raw = await call_llm(
            _RESOLUTION_DETECT_PROMPT.format(items=items_block, text=text[:800]),
            model="gpt-4o-mini",
        )
        resolved_topics = _parse_llm_list(raw)
    except Exception as exc:
        LOGGER.warning("[Loops] resolution detection failed: %s", exc)
        return []

    if not resolved_topics:
        return []

    # Match resolved topics back to loop IDs
    resolved_ids: list[str] = []
    for loop in all_loops:
        loop_topic = loop["topic"].lower()
        for resolved in resolved_topics:
            # Check if resolved item text matches or contains the loop id
            if loop["id"] in resolved or loop_topic in resolved.lower() or resolved.lower() in loop_topic:
                resolved_ids.append(loop["id"])
                break

    return resolved_ids


async def upsert_loop(
    *,
    person_id: str,
    loop_type: str,
    topic: str,
    topic_key: str | None = None,
    stance: str | None = None,
    entry_id: str | None = None,
    source_text: str = "",
) -> str | None:
    """Insert a new open loop or update last_updated_at if a similar one exists.

    Returns the loop id, or None on failure.
    """
    if loop_type not in ("open_decision", "conversation_commitment"):
        return None
    topic = topic.strip()
    if not topic:
        return None

    preview = (source_text or "").strip()[:200]

    # Check for existing similar open loop to avoid duplicates.
    # "Similar" = topic starts with same 60 chars (case-insensitive).
    topic_prefix = topic[:60].lower()
    try:
        existing = await dbfetch(
            """
            SELECT id FROM open_loops
            WHERE person_id = $1
              AND loop_type = $2
              AND status = 'open'
              AND LOWER(LEFT(topic, 60)) = $3
            ORDER BY last_updated_at DESC
            LIMIT 1
            """,
            person_id,
            loop_type,
            topic_prefix,
        )
    except Exception as exc:
        LOGGER.warning("[Loops] duplicate check failed: %s", exc)
        existing = []

    if existing:
        loop_id = str(existing[0]["id"])
        try:
            await dbexec(
                """
                UPDATE open_loops
                SET last_updated_at = NOW(),
                    stance = COALESCE($2, stance),
                    source_preview = COALESCE($3, source_preview)
                WHERE id = $1::uuid
                """,
                loop_id,
                stance,
                preview or None,
            )
        except Exception as exc:
            LOGGER.warning("[Loops] update failed id=%s: %s", loop_id, exc)
        return loop_id

    # New loop
    try:
        row = await dbfetch(
            """
            INSERT INTO open_loops
                (person_id, loop_type, topic, topic_key, stance, entry_id, source_preview)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            person_id,
            loop_type,
            topic,
            topic_key,
            stance,
            entry_id,
            preview or None,
            one=True,
        )
        return str(row["id"]) if row else None
    except Exception as exc:
        LOGGER.warning("[Loops] insert failed person=%s type=%s: %s", person_id, loop_type, exc)
        return None


async def resolve_loop(loop_id: str, resolution_note: str = "") -> None:
    """Mark a loop as resolved."""
    try:
        await dbexec(
            """
            UPDATE open_loops
            SET status = 'resolved',
                resolved_at = NOW(),
                last_updated_at = NOW(),
                resolution_note = $2
            WHERE id = $1::uuid AND status = 'open'
            """,
            loop_id,
            resolution_note[:300] if resolution_note else None,
        )
    except Exception as exc:
        LOGGER.warning("[Loops] resolve failed id=%s: %s", loop_id, exc)


async def get_open_loops(
    person_id: str,
    *,
    status: str = "open",
    limit: int = _MAX_OPEN_LOOPS,
) -> dict[str, Any]:
    """Return open loops split by type, sorted by last_updated_at desc."""
    try:
        rows = await dbfetch(
            """
            SELECT id, loop_type, topic, topic_key, stance,
                   status, first_raised_at, last_updated_at, resolved_at
            FROM open_loops
            WHERE person_id = $1 AND status = $2
            ORDER BY last_updated_at DESC
            LIMIT $3
            """,
            person_id,
            status,
            limit,
        )
    except Exception as exc:
        LOGGER.warning("[Loops] get_open_loops failed person=%s: %s", person_id, exc)
        return {"decisions": [], "commitments": []}

    decisions: list[dict] = []
    commitments: list[dict] = []
    for row in (rows or []):
        item = {
            "id": str(row["id"]),
            "topic": str(row["topic"]),
            "topic_key": row.get("topic_key"),
            "stance": row.get("stance"),
            "first_raised_at": str(row["first_raised_at"]) if row.get("first_raised_at") else None,
            "last_updated_at": str(row["last_updated_at"]) if row.get("last_updated_at") else None,
        }
        if row["loop_type"] == "open_decision":
            decisions.append(item)
        else:
            commitments.append(item)

    return {"decisions": decisions, "commitments": commitments}


async def get_stale_open_loops(person_id: str) -> dict[str, Any]:
    """Return open loops that haven't been updated in > STALE_THRESHOLD_DAYS days."""
    try:
        rows = await dbfetch(
            """
            SELECT id, loop_type, topic, topic_key, stance,
                   first_raised_at, last_updated_at
            FROM open_loops
            WHERE person_id = $1
              AND status = 'open'
              AND last_updated_at < NOW() - ($2 || ' days')::INTERVAL
            ORDER BY last_updated_at ASC
            LIMIT 5
            """,
            person_id,
            str(_STALE_THRESHOLD_DAYS),
        )
    except Exception as exc:
        LOGGER.warning("[Loops] get_stale failed person=%s: %s", person_id, exc)
        return {"decisions": [], "commitments": []}

    decisions: list[dict] = []
    commitments: list[dict] = []
    for row in (rows or []):
        item = {
            "id": str(row["id"]),
            "topic": str(row["topic"]),
            "topic_key": row.get("topic_key"),
            "stance": row.get("stance"),
            "first_raised_at": str(row["first_raised_at"]) if row.get("first_raised_at") else None,
            "last_updated_at": str(row["last_updated_at"]) if row.get("last_updated_at") else None,
            "stale": True,
        }
        if row["loop_type"] == "open_decision":
            decisions.append(item)
        else:
            commitments.append(item)

    return {"decisions": decisions, "commitments": commitments}


async def run_loop_extraction(
    *,
    person_id: str,
    text: str,
    entry_id: str | None = None,
    topic_key: str | None = None,
    stance: str | None = None,
) -> dict[str, Any]:
    """Full pipeline: detect resolutions, then extract new decisions + commitments."""
    # 1. Detect resolutions first (before adding new ones)
    resolved_ids = await detect_resolutions(person_id, text)
    for loop_id in resolved_ids:
        await resolve_loop(loop_id)
    if resolved_ids:
        LOGGER.info("[Loops] resolved %d loops person=%s", len(resolved_ids), person_id)

    # 2. Extract new decisions
    decisions = await extract_decisions(text)
    decision_ids: list[str] = []
    for topic in decisions:
        loop_id = await upsert_loop(
            person_id=person_id,
            loop_type="open_decision",
            topic=topic,
            topic_key=topic_key,
            stance=stance,
            entry_id=entry_id,
            source_text=text,
        )
        if loop_id:
            decision_ids.append(loop_id)

    # 3. Extract commitments
    commitments = await extract_commitments(text)
    commitment_ids: list[str] = []
    for topic in commitments:
        loop_id = await upsert_loop(
            person_id=person_id,
            loop_type="conversation_commitment",
            topic=topic,
            topic_key=topic_key,
            stance=stance,
            entry_id=entry_id,
            source_text=text,
        )
        if loop_id:
            commitment_ids.append(loop_id)

    return {
        "resolved": resolved_ids,
        "decisions_extracted": len(decisions),
        "commitments_extracted": len(commitments),
        "decision_ids": decision_ids,
        "commitment_ids": commitment_ids,
    }


__all__ = [
    "extract_decisions",
    "extract_commitments",
    "detect_resolutions",
    "upsert_loop",
    "resolve_loop",
    "get_open_loops",
    "get_stale_open_loops",
    "run_loop_extraction",
]
