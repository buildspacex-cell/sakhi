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
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# Module Registry — descriptions for future local-model routing
# =============================================================================

MODULE_REGISTRY: Dict[str, str] = {
    "identity": (
        "User explores who they are, values, purpose, growth, or transformation. "
        "Loads narrative_trace, alignment, rhythm_soul, identity_momentum, identity_timeline."
    ),
    "emotional_depth": (
        "User is in emotional distress, sharing feelings, or needs deep support. "
        "Loads inner_dialogue, empathy_state, microreg_state, nudge_state."
    ),
    "moment": (
        "User is at a decision point, weighing options, or facing a crossroads. "
        "Loads evidence_pack, deliberation_scaffold, reflection_trace."
    ),
    "recommendations": (
        "User wants wellness advice, feels off-balance, or asks what to do. "
        "Loads friction state, personalized Ayurvedic food/practice/herb recommendations."
    ),
    "scheduling": (
        "User wants to schedule, check calendar, plan time, or mentions meetings. "
        "Loads calendar events, scheduling pipeline, relationship nudges."
    ),
    "email": (
        "User asks about email, inbox, messages, or communication patterns. "
        "Loads email context, contact preferences."
    ),
    "causal": (
        "User asks WHY they feel a certain way or what's causing a symptom. "
        "Loads causal reasoning: personal patterns, behaviors, Ayurvedic knowledge, seasonal influence."
    ),
    "micro_flow": (
        "User needs focus help, feels stuck, wants next steps, or asks where to start. "
        "Generates focus_path, mini_flow scaffolds on demand."
    ),
    "vision": (
        "User has shared an image or document in the conversation. "
        "Loads image processing context."
    ),
    "agentic": (
        "User wants web search, research, or has a pending agent task. "
        "Loads agent task context."
    ),
    "body": (
        "User mentions sleep, tiredness, exercise, heart rate, physical symptoms, or health. "
        "Loads body state, health trends, symptom-based causal reasoning."
    ),
}

CONTEXT_MODULES = set(MODULE_REGISTRY.keys())

# All modules — used by turn_v2 to load everything unconditionally.
# Future: replaced by local model selection from MODULE_REGISTRY descriptions.
ALL_MODULES = frozenset(CONTEXT_MODULES)


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
_AGENTIC_KEYWORDS = [
    "search for", "look up", "find out", "research",
    "google", "browse", "find me",
]
_BODY_KEYWORDS = [
    "sleep", "slept", "tired", "exhausted", "energy", "heart rate", "hrv",
    "exercise", "workout", "steps", "digestion", "body", "physical",
    "fatigue", "restless", "insomnia", "health", "resting heart",
    "weight", "muscle", "pain", "ache", "nausea",
    # Health symptoms
    "headache", "migraine", "dizzy", "dizziness", "fever", "sick",
    "symptom", "stomach", "chest", "throat", "sore", "cramp",
    "stiff", "tense", "tension", "inflammation", "swollen",
    "burning", "throbbing", "numb", "cold", "hot",
]


# =============================================================================
# Intent Policy Map — declarative intent-name → module mapping
# =============================================================================

INTENT_POLICY: Dict[str, Dict[str, Any]] = {
    # Existing intent routing (was ad-hoc if-chain)
    "schedule":  {"modules": {"scheduling"}, "confidence": 0.8},
    "calendar":  {"modules": {"scheduling"}, "confidence": 0.8},
    "email":     {"modules": {"email"}, "confidence": 0.8},
    "inbox":     {"modules": {"email"}, "confidence": 0.8},
    "health":    {"modules": {"recommendations", "causal"}, "confidence": 0.8},
    "ayurved":   {"modules": {"recommendations", "causal"}, "confidence": 0.8},
    "dosha":     {"modules": {"recommendations", "causal"}, "confidence": 0.8},
    "identity":  {"modules": {"identity"}, "confidence": 0.8},
    "purpose":   {"modules": {"identity"}, "confidence": 0.8},
    "growth":    {"modules": {"identity"}, "confidence": 0.8},
    "decision":  {"modules": {"moment"}, "confidence": 0.8},
    "choice":    {"modules": {"moment"}, "confidence": 0.8},
    # New entries
    "body":      {"modules": {"body"}, "confidence": 0.8},
    "sleep":     {"modules": {"body"}, "confidence": 0.8},
    "emotion":   {"modules": {"emotional_depth"}, "confidence": 0.8},
    "reflect":   {"modules": {"emotional_depth"}, "confidence": 0.8},
    # Triage-derived intent hints (from map_triage_to_intents)
    "action_intent":      {"modules": {"micro_flow"}, "confidence": 0.7},
    "emotion_reflection": {"modules": {"emotional_depth"}, "confidence": 0.7},
    "finance_planning":   {"modules": {"micro_flow"}, "confidence": 0.7},
    "goal_pursuit":       {"modules": {"micro_flow", "identity"}, "confidence": 0.7},
    "schedule_planning":  {"modules": {"scheduling"}, "confidence": 0.8},
    "emotion_support":    {"modules": {"emotional_depth"}, "confidence": 0.7},
}


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

    if _match(_AGENTIC_KEYWORDS):
        modules.add("agentic")
        confidence = max(confidence, 0.8)

    if _match(_BODY_KEYWORDS):
        modules.add("body")
        confidence = max(confidence, 0.8)

    # --- Structural triggers ---

    if has_image:
        modules.add("vision")
        confidence = max(confidence, 0.9)

    if has_pending_task:
        modules.add("agentic")
        confidence = max(confidence, 0.8)

    # --- Intent-based routing (declarative policy map) ---

    for intent in (intents or []):
        intent_name = intent.get("name", "") if isinstance(intent, dict) else str(intent)
        intent_lower = intent_name.lower()
        for keyword, policy in INTENT_POLICY.items():
            if keyword in intent_lower:
                modules.update(policy["modules"])
                confidence = max(confidence, policy["confidence"])

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
# Intent Helpers — triage mapping + DB-backed intent evolution
# =============================================================================


def map_triage_to_intents(triage: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Convert inline triage signals to intent hints for the router.
    Zero LLM cost — uses the deterministic extractor output.
    """
    hints: List[Dict[str, str]] = []
    for signal in triage.get("triage", []):
        sig_type = signal.get("type", "")
        if sig_type == "intent_action":
            hints.append({"name": "action_intent"})
        elif sig_type == "reflection_observation":
            hints.append({"name": "emotion_reflection"})
        elif sig_type == "finance":
            hints.append({"name": "finance_planning"})

    slots = triage.get("slots", {})
    if slots.get("goal"):
        hints.append({"name": "goal_pursuit"})
    if slots.get("time_window"):
        hints.append({"name": "schedule_planning"})
    if slots.get("mood_affect"):
        hints.append({"name": "emotion_support"})

    return hints


async def load_recent_intent_evolution(
    person_id: str,
    limit: int = 5,
    min_strength: float = 0.3,
) -> List[Dict[str, Any]]:
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
