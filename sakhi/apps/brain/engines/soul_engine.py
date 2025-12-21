from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Sequence

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.libs.embeddings import embed_normalized, to_pgvector

VALUE_KEYWORDS = {
    "growth": ["learn", "improve", "practice", "better", "grow"],
    "balance": ["balance", "balanced", "well-being"],
    "health": ["health", "energy", "tired", "rest"],
    "connection": ["friends", "family", "partner", "relationship"],
    "discipline": ["discipline", "routine", "consistency"],
    "creativity": ["music", "guitar", "creative", "art"],
}

LONGING_KEYS = ["want to be", "wish", "hope to", "dream of"]
AVERSION_KEYS = ["hate", "avoid", "draining", "exhausting"]
COMMIT_KEYS = ["commit", "commitment", "promise", "will keep", "continue to"]
SHADOW_KEYS = ["stuck", "avoid", "fear", "anxious"]
LIGHT_KEYS = ["excited", "joy", "meaningful", "energized"]


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def _extract_values(texts: Sequence[str]) -> List[str]:
    hits = []
    for text in texts:
        for value, keys in VALUE_KEYWORDS.items():
            if any(k in text for k in keys):
                hits.append(value)
    return list(dict.fromkeys(hits))[:5]


def _extract_list(texts: Sequence[str], keywords: Sequence[str]) -> List[str]:
    results = []
    for text in texts:
        for k in keywords:
            if k in text:
                results.append(text)
    return list(dict.fromkeys(results))[:5]


def _mean_vectors(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []
    length = min(len(v) for v in vectors if v) or 0
    if length == 0:
        return []
    acc = [0.0] * length
    for vec in vectors:
        for i in range(length):
            acc[i] += float(vec[i])
    return [v / len(vectors) for v in acc]


async def update_soul_state(person_id: str, observations: List[str], embeddings: List[List[float]] | None = None) -> Dict[str, Any]:
    texts = [_normalize(t) for t in observations if t]
    values = _extract_values(texts)
    identity_themes = [t for t in texts if "i am" in t or "i want to be" in t][:5]
    core_themes = []
    for theme in ("music/guitar", "health", "planning", "discipline", "learning"):
        if any(key in " ".join(texts) for key in theme.split("/")):
            core_themes.append(theme)
    meaning_map = {}
    for key in ("guitar", "music", "health", "learning", "planning", "purpose", "meaning"):
        score = 0.0
        for t in texts:
            if key in t:
                score += 0.3
        if score > 0:
            meaning_map[key] = round(min(1.0, score), 2)

    direction_vec = _mean_vectors(embeddings or [])

    soul_state = {
        "core_values": values,
        "longing": _extract_list(texts, LONGING_KEYS),
        "aversions": _extract_list(texts, AVERSION_KEYS),
        "identity_themes": identity_themes,
        "commitments": _extract_list(texts, COMMIT_KEYS),
        "shadow_patterns": _extract_list(texts, SHADOW_KEYS),
        "light_patterns": _extract_list(texts, LIGHT_KEYS),
        "meaning_map": meaning_map,
        "direction_vector": direction_vec,
        "alignment_score": 0.0,
        "confidence": min(0.9, 0.5 + 0.05 * (len(values) + len(core_themes))),
        "updated_at": dt.datetime.utcnow().isoformat(),
    }
    return soul_state


__all__ = ["update_soul_state"]
