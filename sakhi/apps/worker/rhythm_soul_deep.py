from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.rhythm.rhythm_soul_engine import compute_deep_rhythm_soul


async def run_rhythm_soul_deep(person_id: str) -> Dict[str, Any]:
    # load episodic snapshots
    episodic = await q(
        """
        SELECT soul, soul_shadow, soul_light, rhythm_state, ts
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY ts DESC
        LIMIT 50
        """,
        person_id,
    )
    pm_row = await q("SELECT rhythm_state, soul_state FROM personal_model WHERE person_id = $1", person_id, one=True)
    rhythm_state = (pm_row or {}).get("rhythm_state") or {}
    soul_state = (pm_row or {}).get("soul_state") or {}

    deep = await compute_deep_rhythm_soul(person_id, episodic or [], rhythm_state, soul_state)
    await dbexec("UPDATE personal_model SET rhythm_soul_state = $2 WHERE person_id = $1", person_id, deep)
    return deep

