from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Iterable, List

LOGGER = logging.getLogger(__name__)


async def llm_reflect(text: str, *, mode: str = "general") -> str:
    """
    Placeholder LLM reflection helper.
    """
    await asyncio.sleep(0)
    return f"[{mode}] {text}"


def extract_entities(text: str) -> List[str]:
    """
    Lightweight proper noun extractor for names.
    """
    if not text:
        return []
    candidates = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", text)
    ignore = {"I", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in ignore:
            continue
        seen.add(candidate)
    return sorted(seen)


def sentiment_score(text: str) -> float:
    """
    Naive sentiment heuristic (-1..1) for placeholder usage.
    """
    lowered = text.lower()
    positives = sum(lowered.count(word) for word in ("love", "appreciate", "grateful", "excited"))
    negatives = sum(lowered.count(word) for word in ("angry", "upset", "tired", "worried"))
    score = positives - negatives
    return max(-1.0, min(1.0, float(score)))


class _SimpleLLMRouter:
    async def json_extract(self, prompt: str) -> List[dict[str, Any]]:
        """Very small JSON-extraction shim for action suggestions."""
        await asyncio.sleep(0)
        match = re.findall(r"(?:-|\*)\s*(.+)", prompt)
        actions = [{"action": item.strip(), "confidence": 0.7} for item in match]
        return actions or [{"action": prompt.strip()[:80], "confidence": 0.5}]

    async def text(
        self,
        prompt: str,
        *,
        person_id: str | None = None,
        system: str | None = None,
        model: str | None = None,
    ) -> str:
        await asyncio.sleep(0)
        return prompt.strip() or "Ok"


llm_router = _SimpleLLMRouter()


__all__ = [
    "llm_reflect",
    "extract_entities",
    "sentiment_score",
    "llm_router",
]
