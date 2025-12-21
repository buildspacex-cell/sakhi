from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.soul.identity_momentum_engine import compute_deep_identity_momentum


async def run_identity_momentum_deep(person_id: str) -> Dict[str, Any]:
    episodic = await q(
        """
        SELECT soul, emotional_state, rhythm_state, ts
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY ts DESC
        LIMIT 50
        """,
        person_id,
    )
    pm_row = await q(
        "SELECT soul_state, emotion_state, rhythm_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    soul_state = (pm_row or {}).get("soul_state") or {}
    emotion_state = (pm_row or {}).get("emotion_state") or {}
    rhythm_state = (pm_row or {}).get("rhythm_state") or {}

    deep = await compute_deep_identity_momentum(person_id, episodic or [], soul_state, emotion_state, rhythm_state)
    await dbexec("UPDATE personal_model SET identity_momentum_state = $2 WHERE person_id = $1", person_id, deep)
    return deep

