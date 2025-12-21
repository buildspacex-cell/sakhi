"""
Trigger Engine (Patch S)
------------------------
Inspect intents, journaling signals, and mood to decide which background jobs
should be considered. This module only returns trigger flags—schedulers decide
what to do with them.
"""

from __future__ import annotations

from typing import Any, Dict, List


async def compute_triggers(
    person_id: str,  # included for future use/logging
    intents: List[Dict[str, Any]] | None = None,
    journal_entry: Dict[str, Any] | None = None,
    mood: str | None = None,
) -> Dict[str, bool]:
    """
    Determine which subsystems should refresh.
    Does NOT enqueue jobs; downstream schedulers consume these hints.
    """

    triggers: Dict[str, bool] = {
        "rhythm": False,
        "meta_reflection": False,
        "planner_summarizer": False,
        "persona_tuning": False,
        "memory_consolidation": False,
    }

    intents = intents or []
    intent_labels = {
        (intent.get("intent_type") or intent.get("kind") or intent.get("title") or "").lower()
        for intent in intents
        if intent
    }

    normalized_mood = (mood or "").strip().lower()
    content = ((journal_entry or {}).get("content") or "").lower()
    entry_kind = ((journal_entry or {}).get("kind") or "").lower()

    # Rhythm triggers fire on explicit intents or certain mood dips.
    if {"review_week", "energy_check", "rhythm"}.intersection(intent_labels):
        triggers["rhythm"] = True
    if normalized_mood in {"tired", "anxious", "stuck", "overwhelmed"}:
        triggers["rhythm"] = True

    # Meta reflection triggers on deeper intent keywords or weekly prompts.
    if "reflect_deep" in intent_labels:
        triggers["meta_reflection"] = True
    if any(keyword in content for keyword in ("how was this week", "weekly summary", "what did i learn")):
        triggers["meta_reflection"] = True

    # Planner summarizer when tasks/objectives show up.
    if {"plan", "task", "objective"}.intersection(intent_labels):
        triggers["planner_summarizer"] = True

    # Persona tuning for identity-oriented intents.
    if any(keyword in intent_labels for keyword in {"identity", "self_expression", "persona"}):
        triggers["persona_tuning"] = True

    # Memory consolidation when reflections or emotional swings appear.
    if entry_kind == "daily" or "reflection" in content:
        triggers["memory_consolidation"] = True
    if normalized_mood in {"sad", "happy", "excited"}:
        triggers["memory_consolidation"] = True

    return triggers


__all__ = ["compute_triggers"]
