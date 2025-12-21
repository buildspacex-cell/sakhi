from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q


VALUE_MAP = {
    "growth": ["learn", "improve", "practice", "grow", "better"],
    "health": ["balance", "well-being", "tired", "energy", "healthy"],
    "connection": ["friends", "family", "partner", "relationship"],
    "achievement": ["goals", "plan", "career", "progress"],
    "stability": ["routine", "discipline", "consistency", "structure"],
}

THEME_MAP = {
    "music/guitar": ["guitar", "music"],
    "health": ["health", "workout", "exercise", "fitness", "sleep"],
    "learning": ["learn", "study", "course"],
    "discipline": ["discipline", "consistency", "routine"],
    "peace": ["peace", "calm"],
    "balance": ["balance", "balanced"],
    "planning": ["plan", "planning", "schedule"],
    "creativity": ["creative", "creativity"],
}


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


async def _fetch_observations(person_id: str) -> List[Dict[str, Any]]:
    row = await q(
        "SELECT long_term FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    if not row:
        return []
    long_term = row.get("long_term") or {}
    observations = long_term.get("observations") if isinstance(long_term, dict) else []
    if not isinstance(observations, list):
        return []
    cleaned: List[Dict[str, Any]] = []
    for obs in observations:
        if not isinstance(obs, dict):
            continue
        text = _normalize_text(obs.get("text") or "")
        if not text:
            continue
        cleaned.append(
            {
                "text": text,
                "created_at": obs.get("created_at"),
            }
        )
    return cleaned


def _detect_values(texts: List[str]) -> List[str]:
    counter = Counter()
    for text in texts:
        for value, keywords in VALUE_MAP.items():
            if any(k in text for k in keywords):
                counter[value] += 1
    if not counter:
        return []
    return [v for v, _ in counter.most_common(3)]


def _detect_identity(texts: List[str]) -> List[str]:
    anchors = []
    phrases = ["kind of person who", "trying to become", "want to be", "see myself as", "i am trying to"]
    for text in texts:
        for phrase in phrases:
            if phrase in text:
                tail = text.split(phrase, 1)[1].strip()
                if tail:
                    anchors.append(tail)
    return anchors[:3]


def _detect_themes(observations: List[Dict[str, Any]]) -> List[str]:
    counter = Counter()
    date_map: Dict[str, set] = {}
    for obs in observations:
        text = obs.get("text") or ""
        date_key = None
        ts = obs.get("created_at")
        if ts:
            try:
                date_key = dt.datetime.fromisoformat(ts).date().isoformat()
            except Exception:
                date_key = None
        for theme, keywords in THEME_MAP.items():
            if any(k in text for k in keywords):
                counter[theme] += 1
                if date_key:
                    date_map.setdefault(theme, set()).add(date_key)
    themes = []
    for theme, count in counter.items():
        days = len(date_map.get(theme, []))
        if count >= 3 or days >= 3:
            themes.append(theme)
    return themes[:5]


def _build_summary(values: List[str], anchors: List[str], themes: List[str]) -> str:
    top_values = ", ".join(values[:2]) if values else "unknown"
    top_anchors = ", ".join(anchors[:2]) if anchors else "uncertain"
    top_themes = ", ".join(themes[:2]) if themes else "unspecified"
    return f"Values centered on {top_values}. Identity leaning toward {top_anchors}. Life themes around {top_themes}."


async def compute(person_id: str) -> Dict[str, Any]:
    observations = await _fetch_observations(person_id)
    texts = [obs.get("text") for obs in observations if obs.get("text")]

    values = _detect_values(texts)
    anchors = _detect_identity(texts)
    themes = _detect_themes(observations)

    signals = len(values) + len(anchors) + len(themes)
    confidence = min(0.9, 0.5 + 0.05 * signals)

    summary = _build_summary(values, anchors, themes)

    return {
        "summary": summary,
        "confidence": float(confidence),
        "metrics": {
            "values": values,
            "identity_anchors": anchors,
            "life_themes": themes,
        },
        "updated_at": dt.datetime.utcnow().isoformat(),
        "signal_count": signals,
    }


__all__ = ["compute"]
