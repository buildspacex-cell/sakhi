from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.soul.alignment_engine import compute_alignment


async def refresh_alignment(person_id: str) -> Dict[str, Any]:
    pm = await q("SELECT alignment_state, soul_state FROM personal_model WHERE person_id = $1", person_id, one=True)
    goals = await q("SELECT data FROM personal_model WHERE person_id = $1", person_id, one=True)  # placeholder for goals_state
    # placeholder short_term context (read memory_context_cache if needed)
    alignment = compute_alignment(None, (pm or {}).get("soul_state") or {}, (goals or {}).get("goals_state") or {})
    await dbexec("UPDATE personal_model SET alignment_state = $2 WHERE person_id = $1", person_id, alignment)
    return alignment
