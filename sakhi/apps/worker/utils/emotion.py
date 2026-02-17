from __future__ import annotations

import re


def extract_emotion(text: str) -> str:
    """
    Lightweight regex-based emotion inference fallback.
    """
    normalized = (text or "").lower()
    if re.search(r"(overwhelmed|stressed|burnout|burning out)", normalized):
        return "overwhelmed"
    if re.search(r"(tired|exhausted|drained|fatigued)", normalized):
        return "tired"
    if re.search(r"(happy|excited|joy|grateful|thankful)", normalized):
        return "happy"
    if re.search(r"(anxious|nervous|worried|panick)", normalized):
        return "anxious"
    if re.search(r"(sad|down|low|depressed|lonely|grief)", normalized):
        return "sad"
    if re.search(r"(angry|frustrated|furious|irritated|annoyed)", normalized):
        return "frustrated"
    if re.search(r"(scared|afraid|fearful|terrified)", normalized):
        return "scared"
    if re.search(r"(confused|lost|uncertain|conflicted)", normalized):
        return "confused"
    if re.search(r"(calm|peaceful|serene|content)", normalized):
        return "calm"
    return "neutral"


__all__ = ["extract_emotion"]
