from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.core.emotion.emotion_state_engine import extract_emotion_state

LOGGER = logging.getLogger(__name__)
# TODO(prod): shrink window after lab validation (e.g., 30 days). Set wide for lab data.
EMOTION_WINDOW_DAYS = 1500
MIN_EMOTION_SIGNALS = 3


async def run_emotion_state_refresh(person_id: str) -> Dict[str, Any] | None:
    """
    Deterministic emotional signal extraction over recent journals.
    Writes personal_model.emotion_state.
    """
    LOGGER.info("[esr] start", extra={"person_id": person_id})
    db = await get_db()

    entries: List[Dict[str, Any]] = await db.fetch(
        """
        SELECT id, content, created_at
        FROM journal_entries
        WHERE user_id = $1
          AND created_at >= NOW() - ($2::int || ' days')::interval
        ORDER BY created_at DESC
        LIMIT 200
        """,
        person_id,
        EMOTION_WINDOW_DAYS,
    )
    LOGGER.info(
        "[esr] signals fetched",
        extra={
            "person_id": person_id,
            "count": len(entries),
            "window_days": EMOTION_WINDOW_DAYS,
        },
    )

    if len(entries) < MIN_EMOTION_SIGNALS:
        LOGGER.info(
            "[esr] skipped: insufficient signals",
            extra={"person_id": person_id, "signals": len(entries)},
        )
        return None

    state = extract_emotion_state(entries, EMOTION_WINDOW_DAYS)
    if not state:
        LOGGER.info(
            "[esr] skipped: no tones detected",
            extra={"person_id": person_id},
        )
        return None

    await db.execute(
        """
        UPDATE personal_model
        SET emotion_state = $2::jsonb,
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        json.dumps(state, ensure_ascii=False),
    )

    LOGGER.info(
        "[esr] emotion_state updated",
        extra={
            "person_id": person_id,
            "tones": state.get("dominant_tones"),
            "window_days": EMOTION_WINDOW_DAYS,
        },
    )
    return state
