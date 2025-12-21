from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.emotion.emotion_soul_rhythm_engine import compute_deep_esr


async def run_esr_deep(person_id: str) -> Dict[str, Any]:
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
    emotion_state = (pm_row or {}).get("emotion_state") or {}
    soul_state = (pm_row or {}).get("soul_state") or {}
    rhythm_state = (pm_row or {}).get("rhythm_state") or {}

    deep = await compute_deep_esr(person_id, episodic or [], emotion_state, soul_state, rhythm_state)
    await dbexec("UPDATE personal_model SET emotion_soul_rhythm_state = $2 WHERE person_id = $1", person_id, deep)
    return deep

