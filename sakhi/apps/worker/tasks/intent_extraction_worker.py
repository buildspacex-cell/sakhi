"""Intent extraction worker: extracts actionable intents from journal entries and turns."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.apps.api.services.planner.extract import extract_intents

LOGGER = logging.getLogger(__name__)


async def run_intent_extraction(
    person_id: str,
    text: str,
    entry_id: Optional[str] = None,
    source_type: str = "turn",
) -> Dict[str, Any]:
    """
    Extract intents from text (turn or journal entry) and persist to intents table.

    Args:
        person_id: User ID
        text: The text to extract intents from
        entry_id: Optional source entry ID (for journal entries)
        source_type: 'turn' or 'journal'

    Returns:
        Dict with extracted intents and storage status
    """
    if not text or len(text.strip()) < 10:
        LOGGER.debug("[IntentExtraction] Skipping short text for person=%s", person_id)
        return {"status": "skipped", "reason": "text_too_short", "intents": []}

    # Extract intents using the planner service
    intents = await extract_intents(person_id, text)

    if not intents:
        LOGGER.debug("[IntentExtraction] No intents found for person=%s", person_id)
        return {"status": "success", "intents": [], "stored": 0}

    stored_count = 0
    stored_ids = []

    for intent in intents:
        intent_type = intent.get("type", "query")
        title = intent.get("title", "").strip()

        if not title:
            continue

        # Skip pure queries - they're not actionable
        if intent_type == "query":
            continue

        # Map time_window to timeline
        time_window = intent.get("time_window") or {}
        timeline = time_window.get("kind", "unspecified")
        if timeline == "unspecified":
            timeline = "none"

        # Calculate clarity score from confidence and completeness
        confidence = time_window.get("confidence", 0.5)
        has_details = bool(intent.get("details"))
        has_priority = intent.get("priority") is not None
        clarity_score = (confidence * 0.5) + (0.25 if has_details else 0) + (0.25 if has_priority else 0)

        # Build context snapshot
        context = {
            "source_type": source_type,
            "energy_hint": intent.get("energy_hint"),
            "difficulty_hint": intent.get("difficulty_hint"),
            "recurrence": intent.get("recurrence"),
            "raw_intent": intent,
        }

        try:
            result = await dbfetch(
                """
                INSERT INTO intents (
                    user_id, source_entry_id, title, raw_input, intent_type,
                    timeline, priority, status, clarity_score, context_snapshot
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'draft', $8, $9::jsonb)
                RETURNING id
                """,
                person_id,
                int(entry_id) if entry_id and entry_id.isdigit() else None,
                title,
                text[:500] if len(text) > 500 else text,
                intent_type,
                timeline,
                intent.get("priority", 3),
                clarity_score,
                json.dumps(context, ensure_ascii=False),
                one=True,
            )
            if result:
                stored_ids.append(result.get("id"))
                stored_count += 1
        except Exception as exc:
            LOGGER.warning(
                "[IntentExtraction] Failed to store intent for person=%s: %s",
                person_id,
                exc,
            )

    LOGGER.info(
        "[IntentExtraction] person=%s extracted=%s stored=%s",
        person_id,
        len(intents),
        stored_count,
    )

    return {
        "status": "success",
        "intents": intents,
        "stored": stored_count,
        "stored_ids": stored_ids,
    }


async def run_intent_extraction_for_entry(person_id: str, entry_id: str) -> Dict[str, Any]:
    """
    Extract intents from a specific journal entry.
    """
    entry = await dbfetch(
        """
        SELECT user_id, content, raw_encrypted FROM journal_entries
        WHERE id = $1 AND user_id = $2
        """,
        int(entry_id) if entry_id.isdigit() else entry_id,
        person_id,
        one=True,
    )

    if not entry:
        return {"status": "error", "reason": "entry_not_found"}

    text = entry.get("content", "")
    return await run_intent_extraction(person_id, text, entry_id=entry_id, source_type="journal")


__all__ = ["run_intent_extraction", "run_intent_extraction_for_entry"]
