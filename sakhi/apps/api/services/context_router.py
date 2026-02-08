"""
Context Router — Intelligent context module selection for conversation turns.

Hybrid approach: deterministic keyword/signal classification first,
fast LLM fallback for ambiguous messages.

Modules gate which context sections appear in the LLM prompt:
- Tier 1 (always): Cheap computations feed a compact 360° context scan
- Tier 2 (router-gated): Expensive computations run only when the router activates them
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# Module Definitions
# =============================================================================

CONTEXT_MODULES = {
    "identity",         # narrative_trace, alignment, rhythm_soul, identity_momentum, identity_timeline
    "emotional_depth",  # inner_dialogue, empathy_state, microreg_state, nudge_state
    "moment",           # moment_model, evidence_pack, deliberation_scaffold
    "recommendations",  # friction state, personalized recommendations
    "scheduling",       # calendar, scheduling, relationship nudges
    "email",            # email context, contact preferences
    "causal",           # causal reasoning (why am I feeling X)
    "morning_ritual",   # morning_preview, morning_ask, morning_momentum
    "evening_ritual",   # evening_closure
    "micro_flow",       # micro_momentum, micro_recovery, focus_path, mini_flow, micro_journey
    "reflection",       # daily_reflection
    "vision",           # image processing
    "agentic",          # web search, agent tasks
    "body",             # health/body/sleep/exercise/physical state from HealthKit
}


# =============================================================================
# Keyword / Pattern Tables
# =============================================================================

_EMAIL_KEYWORDS = ["email", "inbox", "mail", "messages", "unread"]
_SCHEDULING_KEYWORDS = [
    "schedule", "calendar", "meeting", "book", "when am i free",
    "block time", "plan my day", "plan my week",
]
_RECOMMENDATION_KEYWORDS = [
    "recommend", "suggest", "help me", "what should i",
    "feeling off", "out of balance", "what can i do",
]
_CAUSAL_PATTERNS = [
    "why am i", "why do i feel", "what's causing", "why is my",
    "what makes me", "why does this",
]
_IDENTITY_KEYWORDS = [
    "who am i", "who i am", "my values", "my purpose", "identity", "growth",
    "becoming", "alignment", "self", "evolving", "transformation",
]
_EMOTIONAL_KEYWORDS = [
    "i feel", "hurting", "overwhelmed", "anxious", "scared",
    "need support", "lonely", "depressed", "frustrated", "angry",
    "sad", "stressed", "panicking", "crying", "breaking down",
]
_MOMENT_KEYWORDS = [
    "decision", "crossroads", "should i", "choice", "torn between",
    "weighing", "dilemma", "considering", "not sure whether",
]
_MICRO_FLOW_KEYWORDS = [
    "focus", "stuck", "momentum", "flow", "next step", "what now",
    "where do i start", "help me begin", "work on", "get started",
]
_REFLECTION_KEYWORDS = [
    "reflect", "how was my day", "journal", "look back",
    "what did i learn", "end of day", "wind down",
]
_AGENTIC_KEYWORDS = [
    "search for", "look up", "find out", "research",
    "google", "browse", "find me",
]
_BODY_KEYWORDS = [
    "sleep", "slept", "tired", "exhausted", "energy", "heart rate", "hrv",
    "exercise", "workout", "steps", "digestion", "body", "physical",
    "fatigue", "restless", "insomnia", "health", "resting heart",
    "weight", "muscle", "pain", "ache", "nausea",
]


# =============================================================================
# Deterministic Classifier
# =============================================================================


def classify_context_needs(
    text: str,
    intents: Optional[List[Any]] = None,
    topics: Optional[List[Any]] = None,
    emotion: Optional[str] = None,
    hour: int = 12,
    has_image: bool = False,
    has_pending_task: bool = False,
) -> Tuple[Set[str], float]:
    """
    Deterministic classification of which context modules are relevant.

    Returns (active_modules, confidence).
    Confidence < 0.5 triggers the LLM fallback router.
    """
    modules: Set[str] = set()
    text_lower = (text or "").lower()
    confidence = 0.0

    def _match(keywords: list[str]) -> bool:
        return any(kw in text_lower for kw in keywords)

    # --- Keyword-based routing ---

    if _match(_EMAIL_KEYWORDS):
        modules.add("email")
        confidence = max(confidence, 0.9)

    if _match(_SCHEDULING_KEYWORDS):
        modules.add("scheduling")
        confidence = max(confidence, 0.9)

    if _match(_RECOMMENDATION_KEYWORDS):
        modules.add("recommendations")
        confidence = max(confidence, 0.8)

    if _match(_CAUSAL_PATTERNS):
        modules.add("causal")
        confidence = max(confidence, 0.9)

    if _match(_IDENTITY_KEYWORDS):
        modules.add("identity")
        confidence = max(confidence, 0.8)

    if _match(_EMOTIONAL_KEYWORDS):
        modules.add("emotional_depth")
        confidence = max(confidence, 0.8)

    if _match(_MOMENT_KEYWORDS):
        modules.add("moment")
        confidence = max(confidence, 0.8)

    if _match(_MICRO_FLOW_KEYWORDS):
        modules.add("micro_flow")
        confidence = max(confidence, 0.7)

    if _match(_REFLECTION_KEYWORDS):
        modules.add("reflection")
        confidence = max(confidence, 0.8)

    if _match(_AGENTIC_KEYWORDS):
        modules.add("agentic")
        confidence = max(confidence, 0.8)

    if _match(_BODY_KEYWORDS):
        modules.add("body")
        confidence = max(confidence, 0.8)

    # --- Time-based routing ---

    if 5 <= hour <= 11:
        modules.add("morning_ritual")
        confidence = max(confidence, 0.6)

    if hour >= 20:
        modules.add("evening_ritual")
        confidence = max(confidence, 0.6)

    # --- Structural triggers ---

    if has_image:
        modules.add("vision")
        confidence = max(confidence, 0.9)

    if has_pending_task:
        modules.add("agentic")
        confidence = max(confidence, 0.8)

    # --- Intent-based routing ---

    for intent in (intents or []):
        intent_name = intent.get("name", "") if isinstance(intent, dict) else str(intent)
        intent_lower = intent_name.lower()
        if "schedule" in intent_lower or "calendar" in intent_lower:
            modules.add("scheduling")
            confidence = max(confidence, 0.8)
        if "email" in intent_lower or "inbox" in intent_lower:
            modules.add("email")
            confidence = max(confidence, 0.8)
        if "health" in intent_lower or "ayurved" in intent_lower or "dosha" in intent_lower:
            modules.add("recommendations")
            modules.add("causal")
            confidence = max(confidence, 0.8)
        if "identity" in intent_lower or "purpose" in intent_lower or "growth" in intent_lower:
            modules.add("identity")
            confidence = max(confidence, 0.8)
        if "decision" in intent_lower or "choice" in intent_lower:
            modules.add("moment")
            confidence = max(confidence, 0.8)

    # --- Confidence fallback ---

    if not modules and len((text or "").split()) > 5:
        # Substantive message but no keywords matched — low confidence triggers LLM fallback
        confidence = 0.3
    elif not modules:
        # Short greeting — no modules needed, high confidence
        confidence = 0.8

    return modules, confidence


# =============================================================================
# LLM Fallback Router
# =============================================================================


async def llm_classify_context(text: str, emotion: str) -> Set[str]:
    """
    Fast LLM call to classify which context modules are relevant.
    Used when deterministic classifier has low confidence.
    """
    try:
        from sakhi.apps.api.services.conversation_v2.llm import call_llm
    except ImportError:
        logger.warning("[context_router] Could not import call_llm, skipping LLM fallback")
        return set()

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
# Main Router Entry Point
# =============================================================================


async def route_context(
    text: str,
    intents: Optional[List[Any]] = None,
    topics: Optional[List[Any]] = None,
    emotion: Optional[str] = None,
    hour: int = 12,
    has_image: bool = False,
    has_pending_task: bool = False,
) -> Set[str]:
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


__all__ = ["classify_context_needs", "route_context", "CONTEXT_MODULES"]
