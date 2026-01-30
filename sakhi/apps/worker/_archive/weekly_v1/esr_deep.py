from __future__ import annotations

import json
from typing import Any, Dict
import logging

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.emotion.emotion_soul_rhythm_engine import compute_deep_esr

LOGGER = logging.getLogger(__name__)


def _ensure_dict(val: Any) -> Dict[str, Any]:
    """Convert value to dict, handling JSON strings."""
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}


async def run_esr_deep(person_id: str) -> Dict[str, Any]:
    LOGGER.info("[esr_deep] start person_id=%s", person_id)
    episodic = await q(
        """
        SELECT soul, soul_shadow, soul_light, rhythm_state, emotional_state, ts
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY ts DESC
        LIMIT 50
        """,
        person_id,
    )
    pm_row = await q(
        "SELECT emotion_state, soul_state, rhythm_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    emotion_state = _ensure_dict((pm_row or {}).get("emotion_state"))
    soul_state = _ensure_dict((pm_row or {}).get("soul_state"))
    rhythm_state = _ensure_dict((pm_row or {}).get("rhythm_state"))

    deep = await compute_deep_esr(person_id, episodic or [], emotion_state, soul_state, rhythm_state)
    await dbexec(
        "UPDATE personal_model SET emotion_soul_rhythm_state = $2::jsonb WHERE person_id = $1",
        person_id,
        json.dumps(deep, ensure_ascii=False),
    )
    LOGGER.info(
        "[esr_deep] updated emotion_soul_rhythm_state person_id=%s episodic_count=%s",
        person_id,
        len(episodic or []),
    )
    return deep
