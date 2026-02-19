"""
Context Classifier — Deterministic module selection for conversation turns.

Pure keyword/intent-based classification with zero external dependencies.
LLM fallback and DB-backed intent queries stay in the consuming application.
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# Module Registry — descriptions for future local-model routing
# =============================================================================

MODULE_REGISTRY: dict[str, str] = {
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

# All modules — used by turn pipelines to load everything unconditionally.
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
# Intent Policy Map — declarative intent-name -> module mapping
# =============================================================================

INTENT_POLICY: dict[str, dict[str, Any]] = {
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
    "body":      {"modules": {"body"}, "confidence": 0.8},
    "sleep":     {"modules": {"body"}, "confidence": 0.8},
    "emotion":   {"modules": {"emotional_depth"}, "confidence": 0.8},
    "reflect":   {"modules": {"emotional_depth"}, "confidence": 0.8},
    # Triage-derived intent hints
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
    intents: list[Any] | None = None,
    topics: list[Any] | None = None,
    emotion: str | None = None,
    hour: int = 12,
    has_image: bool = False,
    has_pending_task: bool = False,
) -> tuple[set[str], float]:
    """
    Deterministic classification of which context modules are relevant.

    Returns (active_modules, confidence).
    Confidence < 0.5 triggers the LLM fallback router.
    """
    modules: set[str] = set()
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
# Triage-to-Intent Mapping
# =============================================================================


def map_triage_to_intents(triage: dict[str, Any]) -> list[dict[str, str]]:
    """
    Convert inline triage signals to intent hints for the router.
    Zero LLM cost — uses the deterministic extractor output.
    """
    hints: list[dict[str, str]] = []
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


__all__ = [
    "MODULE_REGISTRY",
    "CONTEXT_MODULES",
    "ALL_MODULES",
    "INTENT_POLICY",
    "classify_context_needs",
    "map_triage_to_intents",
]
