from __future__ import annotations

import datetime as dt
import re
from typing import Iterable, Optional

KEYWORD_TITLES = (
    ({"gym", "fitness", "workout", "training"}, "Gym momentum"),
    ({"health", "doctor", "therapy", "sleep"}, "Health focus"),
    ({"budget", "emi", "loan", "money", "finance"}, "Money planning"),
    ({"job", "career", "interview", "resume", "offer"}, "Career moves"),
    ({"trip", "travel", "flight", "itinerary"}, "Travel plans"),
    ({"study", "course", "class", "learn", "exam"}, "Learning journey"),
)

SLUG_TITLES = {
    "career": "Career moves",
    "health": "Health & energy",
    "learning": "Learning journey",
    "travel": "Travel plans",
}


def infer_slug(user_text: str) -> str:
    text = (user_text or "").lower()
    if any(keyword in text for keyword in ("job", "role", "career", "interview", "resume")):
        return "career"
    if any(keyword in text for keyword in ("gym", "fitness", "workout", "yoga")):
        return "health"
    if any(keyword in text for keyword in ("piano", "music", "guitar", "tutor", "class")):
        return "learning"
    if any(keyword in text for keyword in ("trip", "flight", "hotel", "travel")):
        return "travel"
    return f"journal-{dt.datetime.now():%Y%m%d}"


def _clean_snippet(text: str) -> Optional[str]:
    snippet = re.sub(r"\s+", " ", (text or "").strip())
    snippet = re.sub(r"[^\w\s']", " ", snippet).strip()
    if not snippet:
        return None
    words = snippet.split()
    if len(words) == 1 and len(words[0]) < 3:
        return None
    limited = " ".join(words[:6])
    if len(limited) < 3:
        return None
    return limited.title()


def infer_title_from_candidates(candidates: Iterable[str], slug: str | None = None) -> Optional[str]:
    slug_key = (slug or "").split(":")[0] if slug else None
    lowered_candidates = [(candidate or "").lower() for candidate in candidates if candidate]

    for keywords, title in KEYWORD_TITLES:
        if any(any(word in text for word in keywords) for text in lowered_candidates):
            return title.title()

    if slug_key:
        slug_title = SLUG_TITLES.get(slug_key)
        if slug_title:
            return slug_title.title()

    for candidate in candidates:
        snippet = _clean_snippet(candidate or "")
        if snippet:
            return snippet

    return None
