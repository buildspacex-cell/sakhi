from __future__ import annotations


def detect_tone(text: str) -> dict:
    lowered = (text or "").lower()
    if any(keyword in lowered for keyword in ["anxious", "overwhelmed", "tired", "sad", "stressed"]):
        return {"tone": "heavy", "mood": "low"}
    if any(keyword in lowered for keyword in ["excited", "pumped", "can't wait", "cant wait", "happy", "yay"]):
        return {"tone": "bright", "mood": "high"}
    return {"tone": "neutral", "mood": "mid"}
