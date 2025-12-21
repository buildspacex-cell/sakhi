from __future__ import annotations

import os
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.memory.recall import memory_recall
from sakhi.libs.llm_router.context_builder import build_meta_context


async def summarize_short_term(person_id: str) -> str:
    rows = await q("SELECT short_term FROM personal_model WHERE person_id = $1", person_id)
    if not rows:
        return "I don’t have recent experiences recorded yet."
    payload = rows[0]
    short_term = payload.get("short_term") if isinstance(payload, dict) else None
    if not short_term:
        return "Your short-term patterns are still forming."
    return short_term.get("summary") or "Your recent reflections suggest where your attention has been."


async def summarize_long_term(person_id: str) -> str:
    rows = await q("SELECT long_term FROM personal_model WHERE person_id = $1", person_id)
    if not rows:
        return "Long-term patterns haven’t settled yet."
    payload = rows[0]
    long_term = payload.get("long_term") if isinstance(payload, dict) else None
    if not long_term:
        return "You're still shaping your long-term direction."
    return long_term.get("summary") or "You value growth, balance, and meaningful progress."


async def summarize_recent_context(person_id: str, user_text: str) -> str:
    ctx = await build_meta_context(person_id)
    emotion = ctx.get("emotion") or {}
    mood = emotion.get("mood")
    rhythm = ctx.get("rhythm")
    tone_hint = ctx.get("tone_hint")

    pieces = []
    if mood:
        pieces.append(f"Your mood lately seems {mood}.")
    if rhythm:
        pieces.append("Your internal rhythm hints were considered.")
    if tone_hint:
        pieces.append(tone_hint)

    if not pieces:
        return "Sakhi used your recent patterns and emotional cues."
    return " ".join(pieces)


async def summarize_recall_items(person_id: str, text: str) -> List[str]:
    items = await memory_recall(person_id, text, limit=5)
    results: List[str] = []
    for item in items:
        snippet = item.get("text") or ""
        snippet = snippet.strip()
        if len(snippet) > 140:
            snippet = snippet[:137] + "..."
        results.append(snippet)
    return results


async def summarize_active_themes(person_id: str) -> List[str]:
    rows = await q(
        """
        SELECT theme
        FROM reflections
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        person_id,
    )
    ordered: List[str] = []
    for row in rows:
        theme = row.get("theme")
        if theme and theme not in ordered:
            ordered.append(theme)
    return ordered[:5]


async def summarize_emotion_trend(person_id: str) -> str:
    rows = await q(
        """
        SELECT last_emotion, energy_level
        FROM conversation_state
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        person_id,
    )
    if not rows:
        return "Emotion patterns are still forming."
    payload = rows[0]
    emotion = payload.get("last_emotion")
    energy = payload.get("energy_level")
    if emotion and energy is not None:
        try:
            return f"You seem {emotion} with an energy of {float(energy):.1f} today."
        except (TypeError, ValueError):
            return f"You seem {emotion} and your energy level is noted."
    return "Your emotional pattern is noted."


async def summarize_persona_mode(person_id: str) -> str:
    rows = await q(
        """
        SELECT mode_name
        FROM persona_modes
        WHERE person_id = $1
        ORDER BY last_activated DESC
        LIMIT 1
        """,
        person_id,
    )
    if not rows:
        return "Supportive mode."
    return f"{rows[0].get('mode_name') or 'Supportive'} mode."


async def assemble_human_debug_panel(
    person_id: str,
    input_text: str,
    reply_text: str,
) -> Dict[str, Any]:
    """
    Build a human-readable insight bundle.
    Triggered only when SAKHI_DEV_DEBUG=1.
    """

    if os.getenv("SAKHI_DEV_DEBUG") != "1":
        return {}

    short_term = await summarize_short_term(person_id)
    long_term = await summarize_long_term(person_id)
    recent = await summarize_recent_context(person_id, input_text)
    recall_items = await summarize_recall_items(person_id, input_text)
    themes = await summarize_active_themes(person_id)
    emotion = await summarize_emotion_trend(person_id)
    persona = await summarize_persona_mode(person_id)

    return {
        "short_term_memory": short_term,
        "long_term_memory": long_term,
        "recent_context": recent,
        "relevant_memories": recall_items,
        "active_themes": themes,
        "emotion_trend": emotion,
        "persona_mode": persona,
        "reason_for_reply": (
            "Sakhi responded this way because your input felt like it needed "
            "clarity, grounding, and continuity with your recent patterns."
        ),
        "final_reply": reply_text,
    }


__all__ = ["assemble_human_debug_panel"]
