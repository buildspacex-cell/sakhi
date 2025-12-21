from __future__ import annotations

import asyncio
from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.llm import call_llm

PROMPT = """You are Sakhi's Soul Narrative engine.
Given compressed episodic memory, soul_state, and shadow/light patterns, return JSON with:
{
  "identity_arc": "...",
  "soul_archetype": "...",
  "life_phase": "...",
  "value_conflicts": [],
  "healing_direction": [],
  "narrative_tension": "low|medium|high"
}
Keep it concise and non-poetic."""


async def generate_deep_soul_narrative(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT soul_state, soul, soul_shadow, soul_light
        FROM personal_model pm
        LEFT JOIN memory_episodic me ON me.person_id = pm.person_id
        WHERE pm.person_id = $1
        LIMIT 50
        """,
        person_id,
    )
    soul_state = {}
    episodic = []
    if row:
        # q returns list of records; first contains pm columns; episode columns per row
        soul_state = row[0].get("soul_state") or {}
        episodic = [
            {
                "soul": r.get("soul") or {},
                "shadow": r.get("soul_shadow") or {},
                "light": r.get("soul_light") or {},
            }
            for r in row
        ]

    payload = {
        "soul_state": soul_state,
        "episodic": episodic,
    }
    result = await call_llm(prompt=PROMPT, messages=[{"role": "user", "content": str(payload)}])

    await dbexec(
        "UPDATE personal_model SET soul_narrative = $2 WHERE person_id = $1",
        person_id,
        result,
    )
    return result
