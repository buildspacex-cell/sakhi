from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional


def _enabled() -> bool:
    return os.getenv("SAKHI_DEBUG_NARRATIVE", "false").lower() == "true"


def _truncate(text: Optional[str], limit: int = 600) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _render_list(items: Iterable[Any]) -> Optional[str]:
    values = [str(item) for item in items if item]
    if not values:
        return None
    return ", ".join(values[:6])


async def build_narrative_trace(
    *,
    person_id: str,
    text: str,
    reply: str,
    memory_context: Optional[str],
    reasoning: Optional[Dict[str, Any]],
    intents: Optional[List[Any]],
    emotion: Optional[Dict[str, Any]],
    topics: Optional[List[Any]],
) -> Optional[Dict[str, Any]]:
    """
    Produce a causal, non-technical description of how a reply was formed.
    Enabled only when SAKHI_DEBUG_NARRATIVE=true.
    """

    if not _enabled():
        return None

    reasoning_summary = None
    if isinstance(reasoning, dict):
        reasoning_summary = reasoning.get("summary") or reasoning.get("context")
        if not reasoning_summary:
            insights = reasoning.get("insights")
            if isinstance(insights, list) and insights:
                reasoning_summary = "; ".join(str(item) for item in insights[:3])
        if not reasoning_summary:
            reasoning_summary = _truncate(str(reasoning))

    narrative = {
        "person_id": person_id,
        "user_text": text,
        "reply": reply,
        "memory_context_summary": _truncate(memory_context, 800),
        "reasoning_summary": _truncate(reasoning_summary, 600),
        "intents_detected": _render_list(intents or []),
        "emotion_hint": emotion or {},
        "topics_active": topics or [],
        "explanation": (
            "Sakhi combined the user message with retrieved memories, "
            "planner intents, and emotional context to craft the reply."
        ),
    }

    return narrative


__all__ = ["build_narrative_trace"]
