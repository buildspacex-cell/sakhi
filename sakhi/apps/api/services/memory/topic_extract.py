from __future__ import annotations

from sakhi.apps.worker.utils.llm import extract_entities


async def extract_topics_for_entry(entry_id: str | None, text: str):
    """
    Lightweight stand-in for topic/theme extraction.
    Uses proper noun extraction as proto-themes.
    """

    entities = extract_entities(text or "")
    return entities or []


__all__ = ["extract_topics_for_entry"]
