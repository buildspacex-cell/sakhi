from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import Any, Dict

from sakhi.apps.worker.utils.db import db_fetch
from sakhi.apps.worker.utils.llm import llm_router

_DEFAULT_FALLBACKS: Dict[str, list[str]] = {
    "confirm_task_creation": [
        "Would you like me to note this as a task?",
        "Shall I add this to your plan?",
    ],
    "ask_due_date": [
        "When would you like to do this?",
        "Should I remind you later this week?",
    ],
    "acknowledge_feedback": [
        "Thanks — I’ll refine my reflections from that.",
        "Appreciate it, I’ll adjust how I summarize next time.",
    ],
    "reflective_nudge": [
        "You mentioned this earlier — shall we check progress?",
        "Would you like me to revisit this plan together?",
    ],
    "acknowledge_update": [
        "Great, I’ve updated it.",
        "Done—thanks for clarifying.",
    ],
    "morning_checkin": [
        "Good morning. How’s your energy as we start today?",
        "Morning! Let’s ease into the day together.",
    ],
    "evening_summary": [
        "Let’s wind down—want to recap the day?",
        "Evening check-in: how are you feeling after today?",
    ],
    "rhythm_nudge": [
        "A gentle nudge to stay with your rhythm.",
        "Let’s keep the cadence steady—ready for a small step?",
    ],
    "reconnect_prompt": [
        "It’s been a bit—how have you been feeling?",
        "I’m here whenever you’d like to reconnect.",
    ],
}

_FALLBACKS: Dict[str, list[str]] | None = None


def _load_fallbacks() -> Dict[str, list[str]]:
    global _FALLBACKS
    if _FALLBACKS is None:
        file_path = Path(__file__).with_name("responses.json")
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                _FALLBACKS = json.load(handle)
        except (OSError, json.JSONDecodeError):
            _FALLBACKS = dict(_DEFAULT_FALLBACKS)
    return _FALLBACKS


async def compose_response(person_id: str, intent: str, context: Dict[str, Any] | None = None, system: str = "companion") -> str:
    """
    Unified message composer for Sakhi.
    Pulls tone hints from prompt_profiles and falls back to templates when needed.
    """
    context = context or {}
    tone_hint = "neutral"
    emotion_hint = "neutral"
    try:
        profile = db_fetch("prompt_profiles", {"person_id": person_id})
        if profile and profile.get("tone_weights"):
            weights = profile["tone_weights"]
            warm = float(weights.get("warm", 0.5))
            direct = float(weights.get("direct", 0.5))
            tone_hint = "gentle" if warm > direct else "clear"
        continuity = db_fetch("session_continuity", {"person_id": person_id})
        if continuity and continuity.get("last_emotion"):
            emotion_hint = str(continuity.get("last_emotion"))
    except Exception:
        tone_hint = "neutral"
        emotion_hint = "neutral"

    base_prompt = f"""
[Tone:{tone_hint}] Emotion context: {emotion_hint}
You are Sakhi, a clarity and rhythm companion.
Intent: {intent}
Context: {context}
Respond in a {tone_hint} tone, ~35 words, warm yet concise.
Include empathy and flow continuity if relevant.
""".strip()

    try:
        reply = await llm_router.text(base_prompt, person_id=person_id, system=system)
        reply_text = reply.strip()
    except Exception:
        fallbacks = _load_fallbacks().get(intent, _DEFAULT_FALLBACKS.get(intent, ["Okay."]))
        reply_text = random.choice(fallbacks) if fallbacks else "I'm here with you."

    if intent not in {"system_notification", "nudge"}:
        await asyncio.sleep(random.uniform(0.5, 1.5))

    return reply_text


__all__ = ["compose_response"]
