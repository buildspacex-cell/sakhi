from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q, dbfetchrow
from sakhi.apps.api.core.llm import call_llm

LOGGER = logging.getLogger(__name__)


async def extract_topics(text: str) -> List[str]:
    """
    Use lightweight LLM to extract 1–3 key topics.
    Always returns a list (possibly empty).
    """
    prompt = (
        "Extract 1 to 3 key topics from the message below.\n"
        "Return JSON: {\"topics\": [\"topic1\", \"topic2\", ...]}\n\n"
        f"Message:\n{text}"
    )

    res = await call_llm(messages=[{"role": "user", "content": prompt}], model="gpt-4o-mini")

    if isinstance(res, dict):
        res = json.dumps(res)

    try:
        parsed = json.loads(res)
        topics = parsed.get("topics")
        if isinstance(topics, list):
            return [str(item).strip() for item in topics if item]
    except Exception:
        LOGGER.warning("[TopicManager] Failed to parse topics response.")

    return []


def classify_shift(previous: List[str], current: List[str]) -> str:
    """
    Determine whether the conversation is continuing, shifting, or returning.
    """
    if not previous:
        return "start"

    if any(topic in previous for topic in current):
        return "continue"

    if any(str(topic).lower() in ("hi", "hello", "thanks") for topic in current):
        return "light"

    overlap = set(previous) & set(current)
    if overlap:
        return "return"

    return "shift"


async def update_conversation_topics(person_id: str, text: str) -> Dict[str, Any]:
    """
    Update topic stack in dialog_states for per-session continuity.
    """
    new_topics = await extract_topics(text) or []

    row = await dbfetchrow(
        """
        SELECT state
        FROM dialog_states
        WHERE user_id = $1
          AND conversation_id = 'active'
        """,
        person_id,
    )

    state = row.get("state") if row else {}
    prev_topics: List[str] = state.get("topics", []) if isinstance(state, dict) else []
    history: List[List[str]] = state.get("history", []) if isinstance(state, dict) else []

    shift = classify_shift(prev_topics, new_topics)

    updated_state = {
        "topics": new_topics,
        "history": (history + [new_topics])[-20:],
        "shift": shift,
        "last_message": text,
    }

    await q(
        """
        INSERT INTO dialog_states (conversation_id, user_id, state)
        VALUES ('active', $1, $2::jsonb)
        ON CONFLICT (conversation_id) DO UPDATE SET
            state = EXCLUDED.state,
            updated_at = NOW()
        """,
        person_id,
        json.dumps(updated_state),
    )

    return updated_state


__all__ = ["extract_topics", "update_conversation_topics", "classify_shift"]
