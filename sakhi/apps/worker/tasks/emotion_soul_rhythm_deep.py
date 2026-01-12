from __future__ import annotations

import json
import logging
from typing import Any, Dict

from sakhi.apps.api.core.db import get_db
from sakhi.core.emotion.emotion_soul_rhythm_engine import compute_emotion_soul_rhythm_state

LOGGER = logging.getLogger(__name__)


async def run_emotion_soul_rhythm_deep(person_id: str) -> Dict[str, Any] | None:
    """
    Sensemaking worker: joins emotion_state, soul_state, and rhythm_state.
    Writes personal_model.emotion_soul_rhythm_state.
    """
    LOGGER.info("[emotion_soul_rhythm] start", extra={"person_id": person_id})
    db = await get_db()

    row = await db.fetchrow(
        """
        SELECT emotion_state, soul_state, rhythm_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    )
    if not row:
        LOGGER.info("[emotion_soul_rhythm] skipped: missing personal_model row", extra={"person_id": person_id})
        return None

    def _ensure_dict(value: Any) -> Dict[str, Any]:
        if not value:
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return dict(value)

    emotion_state = _ensure_dict(row["emotion_state"])
    soul_state = _ensure_dict(row["soul_state"])
    rhythm_state = _ensure_dict(row["rhythm_state"])

    if not emotion_state or not soul_state or not rhythm_state:
        LOGGER.info(
            "[emotion_soul_rhythm] skipped: missing inputs",
            extra={"person_id": person_id},
        )
        return None

    state = compute_emotion_soul_rhythm_state(emotion_state, soul_state, rhythm_state)

    await db.execute(
        """
        UPDATE personal_model
        SET emotion_soul_rhythm_state = $2::jsonb,
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        json.dumps(state, ensure_ascii=False),
    )

    LOGGER.info(
        "[emotion_soul_rhythm] state updated",
        extra={
            "person_id": person_id,
            "alignment": state.get("alignment_level"),
            "window_days": state.get("window_days"),
        },
    )
    return state

