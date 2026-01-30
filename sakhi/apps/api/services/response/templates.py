"""
Response Templates

Contains response template structures and formatting utilities
for different response modes and domains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sakhi.apps.api.services.response.strategy import ResponseMode


# =============================================================================
# TEMPLATE STRUCTURES
# =============================================================================

@dataclass
class ResponseTemplate:
    """Structure for a response template."""
    mode: str  # ResponseMode
    structure: List[str]  # Template sections in order
    word_target: int  # Target word count
    example: str  # Example response


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================

TEMPLATES: Dict[str, ResponseTemplate] = {
    ResponseMode.INQUIRE: ResponseTemplate(
        mode=ResponseMode.INQUIRE,
        structure=[
            "ACKNOWLEDGE",  # Brief acknowledgment
            "FRAME",  # Constitution framing
            "ASK",  # 1-2 targeted questions
        ],
        word_target=40,
        example=(
            "Headaches can tell us a lot. Given your nature, I'd want to understand "
            "a bit more. Is the pain more sharp and concentrated, or dull and heavy? "
            "And does it tend to come on after intense work or when you're feeling scattered?"
        ),
    ),
    ResponseMode.CONNECT_AND_INQUIRE: ResponseTemplate(
        mode=ResponseMode.CONNECT_AND_INQUIRE,
        structure=[
            "ACKNOWLEDGE",  # Brief acknowledgment
            "CONNECT",  # Reference known facts
            "ASK",  # 1 targeted question
        ],
        word_target=45,
        example=(
            "Headaches again... I'm noticing you mentioned sleep has been rough, "
            "and you've been skipping meals during busy stretches. For your system, "
            "that combination often shows up as head tension. Is the pain more sharp, "
            "or more of a dull pressure?"
        ),
    ),
    ResponseMode.RESPOND: ResponseTemplate(
        mode=ResponseMode.RESPOND,
        structure=[
            "ACKNOWLEDGE",  # Brief acknowledgment
            "INSIGHT",  # Constitution-specific insight
            "SUGGESTION",  # Practical suggestion
            "CHECK",  # Quick check-in
        ],
        word_target=60,
        example=(
            "Sharp pain at the temples after long meetings — that's a classic intensity "
            "pattern for your system. The combination of mental heat from focused work, "
            "plus the sleep and meal gaps you've mentioned, is likely building pressure. "
            "A few things that often help: step outside for 2 minutes between meetings "
            "for cooler air, and try not to skip lunch even if it's quick. Does that feel doable?"
        ),
    ),
}


# =============================================================================
# DOMAIN-SPECIFIC FRAMING
# =============================================================================

DOMAIN_FRAMING: Dict[str, Dict[str, str]] = {
    "body": {
        "acknowledge_prefix": [
            "{symptom} can tell us a lot.",
            "{symptom} are worth paying attention to.",
            "That {symptom} is your body communicating something.",
        ],
        "frame_prefix": [
            "Given your constitution,",
            "For your system,",
            "With your nature,",
        ],
        "insight_prefix": [
            "For someone with your pattern,",
            "Given your constitution,",
            "For your system,",
        ],
    },
    "mind": {
        "acknowledge_prefix": [
            "That feeling makes sense.",
            "I hear that.",
            "That's worth exploring.",
        ],
        "frame_prefix": [
            "Given how you're wired,",
            "For someone with your nature,",
            "With your tendencies,",
        ],
        "insight_prefix": [
            "For someone with your pattern,",
            "Given your nature,",
            "With your wiring,",
        ],
    },
    "life": {
        "acknowledge_prefix": [
            "That's a meaningful question.",
            "That deserves some reflection.",
            "Important to think through.",
        ],
        "frame_prefix": [
            "Given your values,",
            "With what matters to you,",
            "Considering your priorities,",
        ],
        "insight_prefix": [
            "Based on what you've shared,",
            "Given your situation,",
            "Considering your context,",
        ],
    },
}


# =============================================================================
# DOSHA-SPECIFIC TONE WORDS
# =============================================================================

DOSHA_TONE_WORDS: Dict[str, Dict[str, List[str]]] = {
    "vata": {
        "calming": ["gently", "steadily", "calmly", "softly"],
        "grounding": ["grounded", "anchored", "stable", "settled"],
        "reassuring": ["it's okay", "nothing urgent", "take your time"],
    },
    "pitta": {
        "cooling": ["cool", "ease", "release", "soften"],
        "measured": ["balanced", "measured", "moderated"],
        "releasing": ["let go", "release", "step back", "ease up"],
    },
    "kapha": {
        "energizing": ["spark", "ignite", "activate", "move"],
        "motivating": ["momentum", "flow", "progress", "forward"],
        "clear": ["clear", "light", "fresh", "crisp"],
    },
}


# =============================================================================
# QUESTION CONNECTORS
# =============================================================================

QUESTION_CONNECTORS = {
    "single": [
        "I'm curious —",
        "One thing that would help me understand —",
        "Quick question —",
    ],
    "double": [
        "{q1}? And {q2}?",
        "{q1}? Also — {q2}?",
        "Two things: {q1}? And {q2}?",
    ],
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_template(mode: str) -> Optional[ResponseTemplate]:
    """Get the template for a response mode."""
    return TEMPLATES.get(mode)


def get_domain_framing(domain: str) -> Dict[str, str]:
    """Get domain-specific framing phrases."""
    return DOMAIN_FRAMING.get(domain, DOMAIN_FRAMING["body"])


def get_dosha_tone_words(dosha: str) -> Dict[str, List[str]]:
    """Get dosha-specific tone words."""
    return DOSHA_TONE_WORDS.get(dosha, DOSHA_TONE_WORDS["vata"])


def format_questions(questions: List[str]) -> str:
    """
    Format 1-2 questions into a natural sentence.

    Args:
        questions: List of question strings (max 2)

    Returns:
        Formatted question string
    """
    if not questions:
        return ""

    if len(questions) == 1:
        connector = QUESTION_CONNECTORS["single"][0]
        return f"{connector} {questions[0]}"

    # Two questions
    template = QUESTION_CONNECTORS["double"][0]
    return template.format(q1=questions[0], q2=questions[1])


def estimate_word_count(text: str) -> int:
    """Estimate word count in a text."""
    return len(text.split())


def is_response_too_long(text: str, mode: str) -> bool:
    """Check if a response exceeds target length for its mode."""
    template = get_template(mode)
    if not template:
        return False

    word_count = estimate_word_count(text)
    # Allow 20% over target
    max_words = int(template.word_target * 1.2)
    return word_count > max_words


# =============================================================================
# TEMPLATE FILLERS
# =============================================================================

@dataclass
class TemplateSlots:
    """Slots for filling in a response template."""
    symptom: str = ""
    known_facts: List[str] = field(default_factory=list)
    insight: str = ""
    suggestion: str = ""
    questions: List[str] = field(default_factory=list)
    check: str = "Does that resonate?"


def fill_inquire_template(
    slots: TemplateSlots,
    domain: str = "body",
) -> str:
    """
    Fill in the INQUIRE template.

    Pattern: ACKNOWLEDGE → FRAME → ASK
    """
    framing = get_domain_framing(domain)

    # Acknowledge
    ack = framing["acknowledge_prefix"][0].format(symptom=slots.symptom)

    # Frame
    frame = framing["frame_prefix"][0]

    # Questions
    questions_text = format_questions(slots.questions)

    return f"{ack} {frame} I'd want to understand a bit more. {questions_text}"


def fill_connect_and_inquire_template(
    slots: TemplateSlots,
    domain: str = "body",
) -> str:
    """
    Fill in the CONNECT_AND_INQUIRE template.

    Pattern: ACKNOWLEDGE → CONNECT → ASK
    """
    # Acknowledge
    ack = f"{slots.symptom.capitalize()} again..."

    # Connect (reference known facts)
    if slots.known_facts:
        facts_text = " and ".join(slots.known_facts[:2])
        connect = f"I notice {facts_text}."
    else:
        connect = ""

    # Question
    questions_text = format_questions(slots.questions[:1])  # Just 1 for this mode

    parts = [ack, connect, questions_text]
    return " ".join(p for p in parts if p)


def fill_respond_template(
    slots: TemplateSlots,
    domain: str = "body",
) -> str:
    """
    Fill in the RESPOND template.

    Pattern: ACKNOWLEDGE → INSIGHT → SUGGESTION → CHECK
    """
    framing = get_domain_framing(domain)

    # Acknowledge with specifics if available
    ack = slots.symptom

    # Insight
    insight_prefix = framing["insight_prefix"][0]
    insight = f"{insight_prefix} {slots.insight}"

    # Suggestion
    suggestion = slots.suggestion

    # Check
    check = slots.check

    return f"{ack} — {insight} {suggestion} {check}"


__all__ = [
    "ResponseTemplate",
    "TEMPLATES",
    "DOMAIN_FRAMING",
    "DOSHA_TONE_WORDS",
    "get_template",
    "get_domain_framing",
    "get_dosha_tone_words",
    "format_questions",
    "estimate_word_count",
    "is_response_too_long",
    "TemplateSlots",
    "fill_inquire_template",
    "fill_connect_and_inquire_template",
    "fill_respond_template",
]
