"""
Sensing Layer

Classifies user messages into domains (Body/Mind/Life), extracts symptoms,
detects temporal markers, tone, and specificity.

Output: SenseFrame dataclass with all classification results.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# =============================================================================
# DOMAIN CONFIGURATION
# =============================================================================

DOMAIN_KEYWORDS = {
    "body": {
        "keywords": [
            "headache", "head", "pain", "ache", "hurt", "sore", "tired", "fatigue",
            "sleep", "insomnia", "wake", "rest", "energy", "exhausted", "digestion",
            "stomach", "nausea", "appetite", "eat", "meal", "food", "skin", "rash",
            "muscle", "tension", "back", "neck", "shoulder", "joint", "fever",
            "cold", "cough", "sick", "ill", "health", "body", "physical",
            "weight", "fitness", "exercise", "workout", "breath", "breathing",
        ],
        "sub_domains": {
            "head_neurological": ["headache", "head", "migraine", "dizzy", "vertigo"],
            "sleep": ["sleep", "insomnia", "wake", "rest", "tired", "fatigue", "exhausted"],
            "digestion": ["stomach", "digestion", "nausea", "appetite", "eat", "meal", "food", "gut"],
            "energy": ["energy", "fatigue", "tired", "exhausted", "drained", "low energy"],
            "skin": ["skin", "rash", "itch", "dry", "acne"],
            "musculoskeletal": ["muscle", "back", "neck", "shoulder", "joint", "tension", "pain", "ache"],
            "fitness": ["exercise", "workout", "fitness", "weight", "gym", "yoga", "run", "walk"],
        },
    },
    "mind": {
        "keywords": [
            "anxious", "anxiety", "worried", "worry", "stress", "stressed", "overwhelmed",
            "focus", "concentrate", "clarity", "confused", "foggy", "brain fog",
            "sad", "down", "depressed", "mood", "emotional", "feelings", "feeling",
            "panic", "fear", "scared", "nervous", "restless", "calm", "peace",
            "motivation", "motivated", "stuck", "blocked", "procrastinate", "burnout",
            "think", "thinking", "thought", "mind", "mental", "happy", "frustrated",
            "angry", "irritated", "lonely", "alone", "bored", "excited", "grateful",
        ],
        "sub_domains": {
            "anxiety": ["anxious", "anxiety", "worried", "worry", "panic", "fear", "nervous"],
            "stress": ["stress", "stressed", "overwhelmed", "burnout", "pressure"],
            "focus": ["focus", "concentrate", "clarity", "confused", "foggy", "brain fog"],
            "mood": ["sad", "down", "depressed", "mood", "emotional", "feelings", "happy", "frustrated", "angry"],
            "motivation": ["motivation", "motivated", "stuck", "blocked", "procrastinate"],
            "emotional": ["lonely", "alone", "bored", "excited", "grateful", "irritated"],
        },
    },
    "life": {
        "keywords": [
            "goal", "plan", "career", "job", "work", "relationship", "family",
            "friend", "purpose", "meaning", "decision", "choose", "choice",
            "future", "direction", "path", "growth", "change", "transition",
            "priority", "balance", "life", "time", "money", "finance",
            "boss", "colleague", "coworker", "meeting", "project", "deadline",
            "partner", "husband", "wife", "parent", "child", "kids", "mom", "dad",
            "marriage", "dating", "love", "breakup", "divorce", "wedding",
            "home", "house", "move", "travel", "vacation", "hobby", "passion",
        ],
        "sub_domains": {
            "direction": ["goal", "purpose", "meaning", "direction", "path", "future"],
            "work": ["career", "job", "work", "profession", "business", "boss", "colleague", "meeting", "project", "deadline"],
            "relationships": ["relationship", "family", "friend", "partner", "social", "husband", "wife", "parent", "child", "mom", "dad"],
            "romance": ["love", "dating", "marriage", "breakup", "divorce", "wedding", "partner"],
            "growth": ["growth", "change", "transition", "development", "learning"],
            "decisions": ["decision", "choose", "choice", "priority", "balance"],
            "lifestyle": ["home", "house", "move", "travel", "vacation", "hobby", "passion"],
        },
    },
    # General domain catches conversational messages that don't fit specific domains
    # but still benefit from personalized responses based on constitution
    "general": {
        "keywords": [
            # Greetings and conversation starters
            "hello", "hi", "hey", "morning", "afternoon", "evening", "night",
            "how", "what", "why", "when", "where", "who", "which",
            # Reflective/sharing patterns
            "today", "yesterday", "week", "month", "lately", "recently",
            "tell", "share", "update", "news", "happened", "going",
            # Meta conversation
            "thanks", "thank", "appreciate", "help", "advice", "suggest",
            "wonder", "curious", "question", "ask", "talk", "chat", "conversation",
        ],
        "sub_domains": {
            "greeting": ["hello", "hi", "hey", "morning", "afternoon", "evening"],
            "sharing": ["today", "yesterday", "week", "happened", "update", "news", "tell", "share"],
            "seeking": ["help", "advice", "suggest", "wonder", "curious", "question"],
            "meta": ["thanks", "thank", "appreciate", "talk", "chat", "conversation"],
        },
    },
}

TEMPORAL_MARKERS = {
    "recurring": ["keep", "keeps", "always", "often", "lately", "recently", "these days", "been having"],
    "acute": ["suddenly", "just now", "right now", "just started", "this moment"],
    "chronic": ["for years", "for months", "for a long time", "always had", "chronic"],
}

TONE_SIGNALS = {
    "seeking_help": ["help", "what should", "how do", "any advice", "need", "please", "can you"],
    "venting": ["just need to", "ugh", "so frustrated", "can't believe", "had enough", "tired of"],
    "exploring": ["wondering", "curious", "thinking about", "what if", "maybe", "not sure"],
}

URGENCY_SIGNALS = {
    "high": ["severe", "intense", "unbearable", "can't function", "emergency", "worst"],
    "medium": ["pretty bad", "bothering me", "affecting", "interfering"],
    "low": ["mild", "slight", "a bit", "sometimes", "occasional"],
}


# =============================================================================
# SENSEFRAME DATACLASS
# =============================================================================

@dataclass
class SenseFrame:
    """Result of sensing layer analysis."""

    domain: str = "general"  # "body", "mind", "life", "general"
    sub_domain: str = "general"  # More specific classification
    symptom: str = ""  # Primary symptom/topic extracted
    temporal: str = "unspecified"  # "recurring", "acute", "chronic", "unspecified"
    tone: str = "neutral"  # "seeking_help", "venting", "exploring", "neutral"
    specificity: str = "low"  # "low", "medium", "high"
    urgency: str = "low"  # "low", "medium", "high"
    keywords: List[str] = field(default_factory=list)  # Extracted keywords
    raw_text: str = ""  # Original user message
    confidence: float = 0.0  # Classification confidence (0-1)


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================

def _extract_keywords(text: str) -> List[str]:
    """Extract relevant keywords from text."""
    text_lower = text.lower()
    all_keywords = []

    for domain_config in DOMAIN_KEYWORDS.values():
        for kw in domain_config["keywords"]:
            if kw in text_lower:
                all_keywords.append(kw)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for kw in all_keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique


def _classify_domain(text: str, keywords: List[str]) -> Tuple[str, str, float]:
    """
    Classify the primary domain and sub-domain.

    Priority order: body > mind > life > general
    This ensures health/wellness topics take precedence over general conversation patterns.

    Returns: (domain, sub_domain, confidence)
    """
    text_lower = text.lower()
    # Score all domains including general
    domain_scores = {"body": 0, "mind": 0, "life": 0, "general": 0}

    for domain, config in DOMAIN_KEYWORDS.items():
        for kw in config["keywords"]:
            if kw in text_lower:
                domain_scores[domain] += 1

    # Prioritize specific domains over general
    # If body/mind/life has any matches, prefer them over general
    specific_domains = ["body", "mind", "life"]
    specific_max = max(domain_scores[d] for d in specific_domains)

    if specific_max > 0:
        # Use specific domain
        winning_domain = max(specific_domains, key=lambda d: domain_scores[d])
        confidence = min(1.0, specific_max / 3.0)
    elif domain_scores["general"] > 0:
        # Fall back to general domain
        winning_domain = "general"
        confidence = min(1.0, domain_scores["general"] / 3.0)
    else:
        # No keywords matched - still use "general" with low confidence
        # This ensures adaptive pipeline always runs
        return "general", "sharing", 0.3

    # Find sub-domain
    sub_domain = "general"
    max_sub_score = 0
    sub_domains = DOMAIN_KEYWORDS[winning_domain].get("sub_domains", {})

    for sub, sub_keywords in sub_domains.items():
        sub_score = sum(1 for kw in sub_keywords if kw in text_lower)
        if sub_score > max_sub_score:
            max_sub_score = sub_score
            sub_domain = sub

    return winning_domain, sub_domain, confidence


def _extract_symptom(text: str, domain: str, sub_domain: str, keywords: List[str]) -> str:
    """Extract the primary symptom or topic."""
    # Use the first matched keyword as the symptom
    if keywords:
        return keywords[0]

    # Fallback: try to extract a noun phrase
    text_lower = text.lower()

    # Common symptom patterns
    symptom_patterns = [
        r"having\s+(\w+)",
        r"getting\s+(\w+)",
        r"feeling\s+(\w+)",
        r"(\w+)\s+pain",
        r"(\w+)\s+ache",
    ]

    for pattern in symptom_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1)

    return sub_domain if sub_domain != "general" else domain


def _classify_temporal(text: str) -> str:
    """Classify the temporal nature of the concern."""
    text_lower = text.lower()

    for temporal_type, markers in TEMPORAL_MARKERS.items():
        for marker in markers:
            if marker in text_lower:
                return temporal_type

    return "unspecified"


def _classify_tone(text: str) -> str:
    """Classify the emotional tone of the message."""
    text_lower = text.lower()

    tone_scores = {"seeking_help": 0, "venting": 0, "exploring": 0}

    for tone, signals in TONE_SIGNALS.items():
        for signal in signals:
            if signal in text_lower:
                tone_scores[tone] += 1

    max_score = max(tone_scores.values())
    if max_score == 0:
        return "neutral"

    return max(tone_scores, key=tone_scores.get)


def _assess_specificity(text: str, keywords: List[str]) -> str:
    """
    Assess how specific the user's message is.

    High specificity: location, quality, timing, triggers all mentioned
    Medium: some details provided
    Low: vague description
    """
    specificity_indicators = 0
    text_lower = text.lower()

    # Check for location/body part specifics
    location_words = ["left", "right", "front", "back", "side", "top", "bottom", "temple", "forehead"]
    if any(word in text_lower for word in location_words):
        specificity_indicators += 1

    # Check for quality descriptors
    quality_words = ["sharp", "dull", "throbbing", "pulsing", "burning", "heavy", "pressure", "tight"]
    if any(word in text_lower for word in quality_words):
        specificity_indicators += 1

    # Check for timing specifics
    timing_words = ["morning", "night", "evening", "afternoon", "after", "before", "during", "when"]
    if any(word in text_lower for word in timing_words):
        specificity_indicators += 1

    # Check for trigger mentions
    trigger_words = ["after eating", "after work", "when stressed", "after exercise", "screen", "meeting"]
    if any(phrase in text_lower for phrase in trigger_words):
        specificity_indicators += 1

    # Check message length
    if len(text) > 100:
        specificity_indicators += 1

    if specificity_indicators >= 3:
        return "high"
    elif specificity_indicators >= 1:
        return "medium"
    else:
        return "low"


def _assess_urgency(text: str) -> str:
    """Assess the urgency level of the concern."""
    text_lower = text.lower()

    for level, signals in URGENCY_SIGNALS.items():
        for signal in signals:
            if signal in text_lower:
                return level

    return "low"


# =============================================================================
# MAIN SENSING FUNCTION
# =============================================================================

def sense_message(text: str) -> SenseFrame:
    """
    Main sensing function that analyzes a user message.

    Args:
        text: The user's message

    Returns:
        SenseFrame with all classification results
    """
    text = (text or "").strip()
    if not text:
        return SenseFrame(raw_text=text)

    # Extract keywords
    keywords = _extract_keywords(text)

    # Classify domain and sub-domain
    domain, sub_domain, confidence = _classify_domain(text, keywords)

    # Extract primary symptom
    symptom = _extract_symptom(text, domain, sub_domain, keywords)

    # Classify temporal nature
    temporal = _classify_temporal(text)

    # Classify tone
    tone = _classify_tone(text)

    # Assess specificity
    specificity = _assess_specificity(text, keywords)

    # Assess urgency
    urgency = _assess_urgency(text)

    return SenseFrame(
        domain=domain,
        sub_domain=sub_domain,
        symptom=symptom,
        temporal=temporal,
        tone=tone,
        specificity=specificity,
        urgency=urgency,
        keywords=keywords,
        raw_text=text,
        confidence=confidence,
    )


__all__ = [
    "SenseFrame",
    "sense_message",
    "DOMAIN_KEYWORDS",
    "TEMPORAL_MARKERS",
    "TONE_SIGNALS",
]
