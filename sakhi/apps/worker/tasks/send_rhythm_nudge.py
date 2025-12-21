from __future__ import annotations

import logging

from sakhi.apps.worker.utils.db import db_fetch
from sakhi.apps.worker.utils.response_composer import compose_response

LOGGER = logging.getLogger(__name__)


async def send_rhythm_nudge(person_id: str) -> None:
    """
    Sends small rhythm-aware nudges based on energy and focus trends.
    """
    rhythm = db_fetch("rhythmprint", {"person_id": person_id})
    if not rhythm:
        return

    energy = float(rhythm.get("avg_energy", 0.5))
    mood = float(rhythm.get("avg_mood", 0.5))
    context = {"energy": energy, "mood": mood}

    reply = await compose_response(
        person_id,
        intent="rhythm_nudge",
        context=context,
    )
    send_message(person_id, reply)


def send_message(person_id: str, text: str) -> None:
    LOGGER.info("rhythm_nudge message person_id=%s text=%s", person_id, text)


__all__ = ["send_rhythm_nudge"]
