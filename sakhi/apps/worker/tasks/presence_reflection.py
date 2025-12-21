from __future__ import annotations

import logging
from typing import Any, Dict, List

from uuid import uuid4

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert

LOGGER = logging.getLogger(__name__)


async def run_presence_reflection(person_id: str) -> Dict[str, Any]:
    """Analyze recent reflections and prepare continuity / outreach insights."""
    reflections: List[Dict[str, Any]] = db_find("reflections", {"user_id": person_id})[:10]
    if not reflections:
        LOGGER.info("presence_reflection.no_reflections person_id=%s", person_id)
        return {"person_id": person_id, "summary": ""}

    compiled = "\n".join(str(item.get("content") or "") for item in reflections if item.get("content"))
    prompt = f"Summarize key continuity cues from these reflections:\n{compiled}"

    summary = await call_llm(messages=[{"role": "user", "content": prompt}], person_id=person_id)
    text_summary = summary.strip() if isinstance(summary, str) else str(summary)

    db_insert(
        "insights",
        {
            "id": str(uuid4()),
            "person_id": person_id,
            "kind": "nudge",
            "message": text_summary,
            "ts": "now",
        },
    )
    LOGGER.info("presence_reflection.stored person_id=%s", person_id)
    return {"person_id": person_id, "summary": text_summary}


__all__ = ["run_presence_reflection"]
