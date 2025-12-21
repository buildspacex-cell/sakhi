from __future__ import annotations

import re


def extract_emotion(text: str) -> str:
    """
    Lightweight regex-based emotion inference fallback.
    """
    normalized = (text or "").lower()
    if re.search(r"(tired|exhausted|drained)", normalized):
        return "tired"
    if re.search(r"(happy|excited|joy)", normalized):
        return "happy"
    if re.search(r"(anxious|nervous|worried)", normalized):
        return "anxious"
    if re.search(r"(sad|down|low)", normalized):
        return "sad"
    if re.search(r"(angry|frustrated)", normalized):
        return "frustrated"
    return "neutral"


__all__ = ["extract_emotion"]
