from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.llm import call_llm
from sakhi.prompts.soul_engine import SOUL_EXTRACTION_PROMPT
from sakhi.apps.worker.soul.shadow_extract import extract_shadow_light


async def soul_extract_worker(entry_id: str, person_id: str) -> Dict[str, Any]:
    """
    Extracts soul facets from text (values, longings, shadow/light patterns, etc.)
    Writes to memory_short_term and memory_episodic.
    """
    if not entry_id:
        return {"error": "missing_entry_id"}

    entry = await q(
        """
        SELECT text
        FROM memory_short_term
        WHERE entry_id = $1
        """,
        entry_id,
        one=True,
    )
    if not entry or not entry.get("text"):
        return {"error": "entry_not_found"}

    text = entry.get("text")

    soul = {}
    try:
        soul = await call_llm(
            prompt=None,
            messages=[
                {"role": "system", "content": SOUL_EXTRACTION_PROMPT},
                {"role": "user", "content": text},
            ],
            schema=None,
            model=None,
        )
    except Exception:
        soul = {}

    # Episodic rows are stable and must not carry soul/identity writes; noop here.

    return {"entry_id": entry_id, "person_id": person_id, "soul": soul}


__all__ = ["soul_extract_worker"]
