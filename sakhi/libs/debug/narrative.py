from __future__ import annotations

import os
from typing import Any, Dict, Optional


def _enabled() -> bool:
    """Check if the narrative debug trace should be emitted."""
    return os.getenv("SAKHI_DEBUG_NARRATIVE", "false").lower() == "true"


def build_narrative_trace(
    *,
    user_text: str,
    interpretation: Optional[Dict[str, Any]] = None,
    memory: Optional[Dict[str, Any]] = None,
    context_used: Optional[str] = None,
    reasoning: Optional[str] = None,
    llm_prompt: Optional[str] = None,
    llm_reply: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce a human-friendly, non-technical narrative explaining
    what Sakhi understood, recalled, and reasoned about for a turn.
    """
    if not _enabled():
        return {}

    return {
        "what_you_said": user_text,
        "how_sakhi_understood_it": (
            interpretation.get("summary") if isinstance(interpretation, dict) else interpretation
        ),
        "memory_referenced": memory.get("summary") if isinstance(memory, dict) else memory,
        "context_used_for_llm": context_used,
        "sakhis_reasoning_story": reasoning,
        "summary_of_llm_prompt": llm_prompt,
        "summary_of_llm_reply": llm_reply,
    }


def build_narrative_debug(*, user_text: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Legacy compatibility wrapper used by older routes.
    """
    return build_narrative_trace(user_text=user_text, **kwargs)


__all__ = ["build_narrative_trace", "build_narrative_debug"]
