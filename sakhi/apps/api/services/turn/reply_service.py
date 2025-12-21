from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.services.conversation_v2.conversation_engine import generate_reply


async def build_turn_reply(
    *,
    person_id: str,
    user_text: str,
    context_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a single conversational LLM call using prepared context."""

    metadata = {
        "cache_hit": context_snapshot.get("cache_hit"),
        "rhythm": context_snapshot.get("rhythm"),
        "persona": context_snapshot.get("persona"),
        "tasks": context_snapshot.get("tasks"),
    }
    reply_bundle = await generate_reply(
        person_id=person_id,
        user_text=user_text,
        metadata=metadata,
    )
    return {
        "reply": reply_bundle.get("reply", ""),
        "metadata": metadata,
        "tone": reply_bundle.get("tone_blueprint"),
        "journaling_ai": reply_bundle.get("journaling_ai"),
    }


__all__ = ["build_turn_reply"]
