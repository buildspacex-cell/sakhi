from __future__ import annotations

import datetime as dt
from typing import Dict, Any

from sakhi.apps.api.core.db import q


KEYWORDS = {
    "tired": "tired",
    "exhausted": "tired",
    "sleepy": "tired",
    "stressed": "stressed",
    "anxious": "stressed",
    "anxiety": "stressed",
    "overwhelmed": "stressed",
    "motivated": "motivated",
    "excited": "positive",
    "happy": "positive",
    "great": "positive",
    "good": "positive",
    "energized": "energized",
}


def _score_category(text: str) -> str | None:
    for key, cat in KEYWORDS.items():
        if key in text:
            return cat
    return None


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


async def compute(person_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Lightweight rule-based emotion snapshot.
    """
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
    rows = await q(
        """
        SELECT triage, text, updated_at
        FROM memory_short_term
        WHERE person_id = $1 AND updated_at >= $2
        ORDER BY updated_at DESC
        LIMIT 200
        """,
        person_id,
        cutoff,
    )

    hits = []
    for row in rows:
        triage = row.get("triage") or {}
        if isinstance(triage, str):
            triage = {}
        slots = triage.get("slots") or {}
        sentiment = slots.get("mood_affect") if isinstance(slots, dict) else {}
        label = (sentiment or {}).get("label")
        text = _normalize_text(row.get("text") or "")
        category = label or _score_category(text)
        if category:
            hits.append(category)

    summary = "neutral"
    if hits:
        if "stressed" in hits:
            summary = "feels stressed"
        elif "tired" in hits:
            summary = "feels tired lately"
        elif "motivated" in hits:
            summary = "feels motivated"
        elif "energized" in hits:
            summary = "feels energized"
        elif "positive" in hits:
            summary = "mostly positive"

    confidence = min(1.0, 0.3 + 0.05 * len(hits))

    return {
        "summary": summary,
        "confidence": float(confidence),
        "metrics": {},
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["compute"]
