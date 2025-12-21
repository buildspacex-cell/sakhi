"""
Patch T — Journaling Enrichment Pipeline
---------------------------------------
Enrich a journal entry with lightweight facets, theme tags, and a short meaning
statement. Output is returned to callers; no DB writes happen here.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm


def extract_facets(text: str) -> Dict[str, Any]:
    """Heuristic facet extraction covering emotion/energy/clarity/topics."""

    lowered = text.lower()
    facets: Dict[str, Any] = {
        "emotion": None,
        "energy": None,
        "clarity": None,
        "topics": [],
    }

    if any(token in lowered for token in ("tired", "exhausted", "drained")):
        facets["energy"] = "low"
        facets["emotion"] = facets["emotion"] or "tired"
    if any(token in lowered for token in ("happy", "excited", "grateful", "joyful")):
        facets["emotion"] = "positive"
        facets["energy"] = facets["energy"] or "high"
    if any(token in lowered for token in ("confused", "unclear", "lost", "foggy")):
        facets["clarity"] = "low"
    if any(token in lowered for token in ("focused", "clear", "centered", "balanced")):
        facets["clarity"] = "high"

    tokens = re.findall(r"[a-zA-Z]+", lowered)
    stopwords = {"i", "and", "the", "to", "a", "in", "on", "it", "is", "of", "for", "with"}
    unique_topics = []
    for token in tokens:
        if token in stopwords:
            continue
        if token not in unique_topics:
            unique_topics.append(token)
        if len(unique_topics) >= 8:
            break
    facets["topics"] = unique_topics
    return facets


def extract_themes(text: str) -> List[str]:
    """Rudimentary theme tagging so downstream planners can branch."""

    lowered = text.lower()
    themes: List[str] = []
    if any(word in lowered for word in ("work", "office", "project", "deadline", "career")):
        themes.append("work")
    if any(word in lowered for word in ("health", "sleep", "body", "exercise", "rest")):
        themes.append("health")
    if any(word in lowered for word in ("relationship", "friend", "family", "partner", "love")):
        themes.append("relationships")
    if any(word in lowered for word in ("money", "budget", "finance", "rent", "income")):
        themes.append("finance")
    if not themes:
        themes.append("general")
    return themes


async def meaning_extraction(text: str, person_id: str | None = None) -> str:
    """LLM-powered one-liner explaining why this entry matters emotionally."""

    prompt = (
        "Summarize the deeper meaning behind this journal entry in 1–2 sentences. "
        "Focus on why it matters emotionally or mentally:\n\n"
        f"{text}"
    )
    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages=messages, person_id=person_id)
    if isinstance(response, str):
        return response.strip()
    return str(response).strip()


async def enrich_journal_entry(text: str, person_id: str | None = None) -> Dict[str, Any]:
    """Main enrichment entry point."""

    facets = extract_facets(text)
    themes = extract_themes(text)
    meaning = await meaning_extraction(text, person_id=person_id)
    return {
        "facets": facets,
        "themes": themes,
        "meaning": meaning,
    }


__all__ = ["enrich_journal_entry", "extract_facets", "extract_themes", "meaning_extraction"]
