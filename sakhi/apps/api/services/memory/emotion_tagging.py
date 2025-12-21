from __future__ import annotations

from sakhi.apps.worker.utils.emotion import extract_emotion


async def detect_emotion_for_entry(entry_id: str | None, text: str):
    """
    Simple wrapper to extract a labeled emotion.
    """

    label = extract_emotion(text or "")
    return {"emotion": label}


__all__ = ["detect_emotion_for_entry"]
