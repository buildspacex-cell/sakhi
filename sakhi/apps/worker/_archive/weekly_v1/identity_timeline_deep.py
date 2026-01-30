from __future__ import annotations

import json
from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.soul.identity_timeline_engine import compute_deep_identity_timeline


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
    soul_state = _ensure_dict((pm_row or {}).get("soul_state"))
    emotion_state = _ensure_dict((pm_row or {}).get("emotion_state"))
    rhythm_state = _ensure_dict((pm_row or {}).get("rhythm_state"))
    identity_momentum_state = _ensure_dict((pm_row or {}).get("identity_momentum_state"))

    deep = await compute_deep_identity_timeline(
        person_id,
        episodic or [],
        soul_state,
        emotion_state,
        rhythm_state,
        identity_momentum_state,
    )
    await dbexec(
        "UPDATE personal_model SET identity_timeline = $2::jsonb, persona_evolution_state = $3::jsonb WHERE person_id = $1",
        person_id,
        json.dumps(deep, ensure_ascii=False),
        json.dumps(deep.get("persona_evolution") if isinstance(deep, dict) else {}, ensure_ascii=False),
    )
    return deep

