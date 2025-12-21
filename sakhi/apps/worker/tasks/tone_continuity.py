from __future__ import annotations

import logging
from uuid import uuid4

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert
from sakhi.libs.schemas.settings import get_settings

LOGGER = logging.getLogger(__name__)


async def run_tone_continuity(person_id: str) -> dict[str, str]:
    """
    Analyze recent reflections and infer a tone style for upcoming interactions.
    Writes result into preferences(scope='persona', key='tone').
    """
    settings = get_settings()
    if not settings.enable_reflective_state_writes:
        LOGGER.info("Worker disabled by safety gate: ENABLE_REFLECTIVE_STATE_WRITES=false")
        return {"person_id": person_id, "tone": ""}

    reflections = db_find("reflections", {"user_id": person_id})[:7]
    compiled = "\n".join(str(item.get("content") or "") for item in reflections) or "No reflections yet."

    prompt = (
        "Based on these reflections, choose an emotional tone "
        "(calm, warm, empathetic, upbeat) for the next conversation:\n"
        f"{compiled}"
    )

    response = await call_llm(
        messages=[{"role": "user", "content": prompt}],
        person_id=person_id,
    )
    tone = response.strip() if isinstance(response, str) else str(response)

    db_insert(
        "preferences",
        {
            "id": str(uuid4()),
            "person_id": person_id,
            "scope": "persona",
            "key": "tone",
            "value": {"style": tone},
            "confidence": 0.9,
        },
    )

    LOGGER.info("[Tone Continuity] %s: %s", person_id, tone)
    return {"person_id": person_id, "tone": tone}


__all__ = ["run_tone_continuity"]
