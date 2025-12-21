from __future__ import annotations

from datetime import datetime, timezone

from sakhi.apps.worker.utils.db import db_upsert
from sakhi.apps.worker.utils.emotion import extract_emotion


async def update_emotional_context(person_id: str, text: str) -> None:
    """
    Extracts emotion from user's last message and updates continuity state.
    """
    emotion = extract_emotion(text) or "neutral"
    db_upsert(
        "session_continuity",
        {
            "person_id": person_id,
            "last_emotion": emotion,
            "last_interaction_ts": datetime.now(timezone.utc).isoformat(),
        },
    )


__all__ = ["update_emotional_context"]
