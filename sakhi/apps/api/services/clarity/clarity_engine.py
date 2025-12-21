from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from sakhi.apps.worker.utils.llm import sentiment_score
from sakhi.libs.embeddings import embed_text

DEFAULT_THEMES = ("work", "health", "family", "finance", "energy", "focus", "relationships", "growth")


def _detect_themes(text: str, *, themes: Sequence[str]) -> List[str]:
    lowered = text.lower()
    return [theme for theme in themes if theme in lowered]


async def compute_clarity_features(text: str) -> Dict[str, Any]:
    """
    Lightweight clarity feature extractor.
    Returns sentiment, a normalized clarity score, embedding vector, and detected themes.
    """

    normalized = (text or "").strip()
    if not normalized:
        return {
            "clarity": 0.5,
            "sentiment": 0.0,
            "vector": [0.0] * 1536,
            "themes": [],
        }

    sentiment = float(sentiment_score(normalized))
    vector = await embed_text(normalized)
    if isinstance(vector, list) and vector and isinstance(vector[0], list):
        vector = vector[0]

    word_count = max(1, len(normalized.split()))
    length_factor = min(1.0, word_count / 40.0)
    clarity = min(1.0, max(0.05, (sentiment + 1.0) / 2.0 * length_factor))

    detected = _detect_themes(normalized, themes=DEFAULT_THEMES)

    return {
        "clarity": round(clarity, 4),
        "sentiment": round(sentiment, 4),
        "vector": vector,
        "themes": detected,
    }


__all__ = ["compute_clarity_features"]
