from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.soul.identity_timeline_engine import compute_deep_identity_timeline


async def run_identity_timeline_deep(person_id: str) -> Dict[str, Any]:
    episodic = await q(
        """
        SELECT soul, emotional_state, rhythm_state, ts
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY ts DESC
        LIMIT 70
        """,
        person_id,
    )
    pm_row = await q(
        "SELECT soul_state, emotion_state, rhythm_state, identity_momentum_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    soul_state = (pm_row or {}).get("soul_state") or {}
    emotion_state = (pm_row or {}).get("emotion_state") or {}
    rhythm_state = (pm_row or {}).get("rhythm_state") or {}
    identity_momentum_state = (pm_row or {}).get("identity_momentum_state") or {}

    deep = await compute_deep_identity_timeline(
        person_id,
        episodic or [],
        soul_state,
        emotion_state,
        rhythm_state,
        identity_momentum_state,
    )
    await dbexec(
        "UPDATE personal_model SET identity_timeline = $2, persona_evolution_state = $3 WHERE person_id = $1",
        person_id,
        deep,
        deep.get("persona_evolution") if isinstance(deep, dict) else {},
    )
    return deep

