from __future__ import annotations

import logging
from typing import Dict

from sakhi.apps.api.core.db import get_db
from sakhi.apps.worker.utils.emotion import extract_emotion

LOGGER = logging.getLogger(__name__)
_EMOTION_ENERGY: Dict[str, float] = {
    "tired": 0.3,
    "sad": 0.35,
    "anxious": 0.4,
    "frustrated": 0.45,
    "neutral": 0.5,
    "calm": 0.6,
    "happy": 0.75,
    "excited": 0.85,
}
NUDGES: Dict[str, str] = {
    "tired": "Let's take two deep breaths before your next task.",
    "anxious": "Maybe step away from the screen for a minute?",
    "calm": "Perfect moment to focus on something meaningful.",
}


def detect_emotion(text: str) -> Dict[str, float | str]:
    """Return a lightweight emotion + energy estimate."""

    label = extract_emotion(text or "")
    energy = _EMOTION_ENERGY.get(label, 0.55)
    return {"emotion": label, "energy": float(energy)}


async def update_conversation_state(person_id: str, latest_text: str) -> None:
    """Persist low-latency conversation emotion + energy snapshots."""

    if not person_id or not latest_text:
        return

    emo = detect_emotion(latest_text)
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO conversation_state (person_id, last_emotion, energy_level, updated_at)
            VALUES ($1, $2, $3, now())
            ON CONFLICT (person_id)
            DO UPDATE SET last_emotion = $2, energy_level = $3, updated_at = now()
            """,
            person_id,
            emo["emotion"],
            emo["energy"],
        )
    finally:
        await db.close()

    await maybe_send_nudge(person_id, str(emo["emotion"]))
    LOGGER.info("[Companion] State updated for %s → %s", person_id, emo)


async def maybe_send_nudge(person_id: str, emotion: str) -> None:
    """Send lightweight emotional nudges (log-based placeholder)."""

    message = NUDGES.get(emotion)
    if not message:
        return
    LOGGER.info("[Companion] Micro-nudge for %s (%s): %s", person_id, emotion, message)


__all__ = ["update_conversation_state", "detect_emotion", "maybe_send_nudge"]
