import re


def detect_activation(text: str) -> float:
    """Rough proxy for motivational energy 0–1."""

    patterns = [
        r"\b(want|will|going to|plan|aim|dream|build|create|start|become|lead|win|achieve|play|launch)\b",
        r"\b(excited|eager|driven|motivated|pumped|ready)\b",
    ]
    lowered = text.lower()
    hits = sum(bool(re.search(pattern, lowered)) for pattern in patterns)
    return min(hits * 0.3, 1.0)
