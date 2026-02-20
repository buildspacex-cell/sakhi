"""
Context Router — Context module definitions and selection for conversation turns.

Current strategy (Option A): Load ALL modules unconditionally.
Every turn gets full context; the conversation LLM decides what's relevant.

Future strategy: Replace with a local model that selects modules from
MODULE_REGISTRY descriptions, then load only those. The registry and
classify_context_needs() are preserved for that transition.

Module lifecycle:
- Tier 1 (always): Cheap computations feed a compact 360° context scan
- Tier 2 (all loaded): DB-backed enrichments (inner dialogue, evidence,
  recommendations, scheduling, email, causal reasoning, health trends)

Pure classification logic (keyword tables, intent policy, deterministic
classifier) lives in ``kala.context.classifier``.  This module re-exports
those symbols and adds LLM fallback + DB-backed intent loading.
"""

from __future__ import annotations

import json
import logging
from typing import Any

# Re-export pure classification from kala (single source of truth)
from kala.context.classifier import (  # noqa: F401
    ALL_MODULES,
    CONTEXT_MODULES,
    INTENT_POLICY,
    MODULE_REGISTRY,
    classify_context_needs,
    map_triage_to_intents,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LLM Fallback Router
# =============================================================================


async def llm_classify_context(text: str, emotion: str) -> set[str]:
    """
    Fast LLM call to classify which context modules are relevant.
    Used when deterministic classifier has low confidence.
    """
    from sakhi.apps.api.core.llm import call_llm

    prompt = (
        "Given this user message to their wellness companion Sakhi:\n"
        f'"{text}"\n\n'
        f"User's detected emotion: {emotion}\n\n"
        "Which context modules should be activated? Choose ONLY what's clearly relevant:\n"
        "- email: User is asking about email, inbox, messages\n"
        "- scheduling: User wants to schedule, check calendar, plan time\n"
        "- recommendations: User wants wellness advice, feels off, asks what to do\n"
        "- causal: User asks WHY they feel a certain way\n"
        "- identity: User explores who they are, values, purpose, growth\n"
        "- emotional_depth: User is in emotional distress, needs deep support\n"
        "- moment: User is at a decision point, weighing options\n"
        "- micro_flow: User needs focus help, feels stuck, wants next steps\n"
        "- body: User mentions sleep, tiredness, exercise, heart rate, physical health, energy\n"
        "- reflection: User wants to reflect on their day or experiences\n"
        "- none: Just a casual conversation, greeting, or simple question\n\n"
        'Return a JSON array of module names. Example: ["email", "recommendations"]\n'
        'If nothing specific, return: ["none"]'
    )

    try:
        result = await call_llm(prompt, max_tokens=60, model="gpt-4o-mini")
        # Parse JSON array from response
        result_text = result if isinstance(result, str) else str(result)
        # Find JSON array in response
        start = result_text.find("[")
        end = result_text.rfind("]")
        if start >= 0 and end > start:
            parsed = json.loads(result_text[start:end + 1])
            return {m for m in parsed if isinstance(m, str) and m in CONTEXT_MODULES}
        return set()
    except Exception as exc:
        logger.warning("[context_router] LLM fallback failed: %s", exc)
        return set()


# =============================================================================
# Intent Helpers — DB-backed intent evolution
# =============================================================================


async def load_recent_intent_evolution(
    person_id: str,
    limit: int = 5,
    min_strength: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Load strong recent intents from intent_evolution table.
    Returns intent-like dicts for the router.
    """
    from sakhi.apps.api.core.db import q as _q

    try:
        rows = await _q(
            """
            SELECT intent_name, strength, trend
            FROM intent_evolution
            WHERE person_id = $1 AND strength >= $2
            ORDER BY strength DESC
            LIMIT $3
            """,
            person_id, min_strength, limit,
        )
        return [{"name": r["intent_name"], "strength": r.get("strength", 0)} for r in (rows or [])]
    except Exception as exc:
        logger.warning("[context_router] Failed to load intent_evolution: %s", exc)
        return []


# =============================================================================
# Main Router Entry Point
# =============================================================================


async def route_context(
    text: str,
    intents: list[Any] | None = None,
    topics: list[Any] | None = None,
    emotion: str | None = None,
    hour: int = 12,
    has_image: bool = False,
    has_pending_task: bool = False,
) -> set[str]:
    """
    Determine which context modules to activate for this turn.

    Deterministic classification first; LLM fallback if confidence < 0.5.
    Returns a set of module names from CONTEXT_MODULES.
    """
    modules, confidence = classify_context_needs(
        text=text,
        intents=intents,
        topics=topics,
        emotion=emotion,
        hour=hour,
        has_image=has_image,
        has_pending_task=has_pending_task,
    )

    if confidence < 0.5:
        try:
            llm_modules = await llm_classify_context(text, emotion or "neutral")
            modules.update(llm_modules - {"none"})
        except Exception:
            pass  # Fall back to deterministic result

    logger.debug(
        "[context_router] text=%r modules=%s confidence=%.2f",
        text[:60], modules, confidence,
    )
    return modules


__all__ = [
    "classify_context_needs",
    "route_context",
    "CONTEXT_MODULES",
    "ALL_MODULES",
    "MODULE_REGISTRY",
    "INTENT_POLICY",
    "map_triage_to_intents",
    "load_recent_intent_evolution",
]
