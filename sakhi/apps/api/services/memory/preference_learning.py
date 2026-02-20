"""
Preference Learning Module
--------------------------
Auto-extracts preferences from conversation text across ANY domain.

Integrates with the turn processing pipeline to learn preferences
from natural language like:
- "I love woody scents" → fragrance/woodiness
- "I prefer spicy food" → food/spiciness
- "Can't stand mushy textures" → food/texture_creaminess
- "I'm more of a quiet restaurant person" → environment/noise_tolerance
- "I like traveling light" → travel/adventure_level
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.services.memory.preference_framework import (
    PreferenceDomain,
    EvidenceType,
    PreferenceValue,
    PreferenceStrength,
    PersonPreferences,
    get_or_create_preferences,
    store_preferences,
    log_preference_event,
    STANDARD_DIMENSIONS,
)
from sakhi.apps.api.core.llm import call_llm

LOGGER = logging.getLogger(__name__)

# Minimum text length to consider for preference extraction
MIN_TEXT_LENGTH = 15

# Keywords that indicate potential preference statements
PREFERENCE_INDICATORS = [
    "i like", "i love", "i prefer", "i enjoy", "i want",
    "i hate", "i don't like", "i can't stand", "i dislike", "i avoid",
    "my favorite", "my preference", "i'm into", "i'm not into",
    "too spicy", "too hot", "too cold", "too loud", "too quiet",
    "not enough", "just right", "perfect amount",
    "always order", "never order", "usually get", "always choose",
    "reminds me of", "like the way", "how i like",
    "prefer it when", "makes me feel", "i tend to",
    "never wear", "always wear", "can't travel without",
]

# Domain detection keywords
DOMAIN_KEYWORDS = {
    "food": [
        "food", "eat", "taste", "flavor", "spicy", "sweet", "salty", "cuisine",
        "restaurant", "meal", "dish", "cook", "dinner", "lunch", "breakfast",
        "snack", "hungry", "delicious", "yummy", "bitter", "umami", "crunchy",
        "creamy", "portion", "appetizer", "dessert",
    ],
    "fragrance": [
        "scent", "smell", "fragrance", "perfume", "cologne", "aroma", "woody",
        "floral", "citrus", "musk", "notes", "fresh", "spray", "incense",
        "candle", "diffuser", "essential oil", "aftershave",
    ],
    "travel": [
        "travel", "trip", "vacation", "hotel", "flight", "destination", "explore",
        "adventure", "tourism", "backpack", "resort", "beach", "mountain",
        "city", "countryside", "cultural", "local", "booking", "itinerary",
    ],
    "fashion": [
        "wear", "clothes", "outfit", "style", "fashion", "dress", "shirt",
        "pants", "shoes", "accessory", "color", "pattern", "fit", "brand",
        "comfortable", "formal", "casual", "trendy",
    ],
    "wellness": [
        "exercise", "workout", "meditation", "yoga", "sleep", "health",
        "nutrition", "supplement", "stress", "energy", "relax", "gym",
        "running", "fitness", "diet", "mental", "therapy",
    ],
    "environment": [
        "room", "temperature", "lighting", "noise", "quiet", "loud",
        "atmosphere", "ambiance", "decor", "clean", "clutter", "cozy",
        "minimalist", "plants", "natural light", "air",
    ],
    "social": [
        "people", "group", "alone", "introvert", "extrovert", "party",
        "gathering", "conversation", "friends", "social", "crowd",
        "networking", "meeting", "small talk",
    ],
    "media": [
        "movie", "film", "show", "series", "book", "music", "podcast",
        "game", "documentary", "comedy", "drama", "thriller", "genre",
        "watch", "read", "listen", "play", "entertainment",
    ],
}


def _has_preference_indicators(text: str) -> bool:
    """Check if text contains preference-indicating phrases."""
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in PREFERENCE_INDICATORS)


def _detect_domains(text: str) -> List[str]:
    """Detect which domains the text might relate to."""
    text_lower = text.lower()
    domains = []

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            domains.append(domain)

    return domains if domains else ["custom"]


async def extract_preferences_from_text(
    person_id: str,
    text: str,
    context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Use LLM to extract preferences from natural language.

    Returns list of extracted preferences with domain, dimension, and sentiment.
    """
    detected_domains = _detect_domains(text)

    # Build prompt with relevant dimensions
    dimension_hints = {}
    for domain in detected_domains:
        if domain in STANDARD_DIMENSIONS:
            dimension_hints[domain] = STANDARD_DIMENSIONS[domain]

    prompt = f"""Analyze this text for user preferences. Extract any stated or implied preferences.

Text: "{text}"
{f'Context: {context}' if context else ''}

Detected domains: {', '.join(detected_domains)}
Available dimensions per domain: {json.dumps(dimension_hints, indent=2)}

For each preference found, return:
- domain: which category (food, fragrance, travel, fashion, wellness, environment, social, media, or custom)
- dimension: the specific aspect (use standard dimensions when possible, or create a new descriptive one)
- value: sentiment from -1.0 (strongly dislike) to 1.0 (strongly love)
- confidence: how certain (0.0 to 1.0) based on clarity of statement
- source_text: the exact phrase that indicates this preference

Return JSON array of preferences. If no preferences found, return empty array.

Example output:
[
  {{"domain": "fragrance", "dimension": "woodiness", "value": 0.8, "confidence": 0.9, "source_text": "I love woody scents"}},
  {{"domain": "food", "dimension": "spiciness", "value": -0.6, "confidence": 0.7, "source_text": "too spicy for me"}}
]"""

    try:
        content = await call_llm(
            prompt=prompt,
            model=os.getenv("MODEL_CHAT", "gpt-4o-mini"),
        )

        # Handle potential markdown wrapping
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        preferences = json.loads(content.strip())
        return preferences if isinstance(preferences, list) else []

    except Exception as e:
        LOGGER.warning("[preference_learning] LLM extraction failed: %s", e)
        return []


async def extract_preferences_from_turn(
    person_id: str,
    user_text: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extract preferences from a conversation turn.

    Called asynchronously after each turn to learn preferences
    from the user's natural language.

    Args:
        person_id: User's ID
        user_text: The user's message text
        context: Optional context (activity, topic, etc.)

    Returns:
        List of preferences that were learned

    Examples:
        >>> await extract_preferences_from_turn(
        ...     person_id="user-123",
        ...     user_text="I really love woody scents in my car"
        ... )
        [{"domain": "fragrance", "dimension": "woodiness", "value": 0.8, ...}]
    """
    # Skip short messages
    if not user_text or len(user_text.strip()) < MIN_TEXT_LENGTH:
        return []

    # Quick check for preference indicators (avoid unnecessary LLM calls)
    if not _has_preference_indicators(user_text):
        LOGGER.debug("[preference_learning] No preference indicators in text, skipping")
        return []

    LOGGER.info(
        "[preference_learning] Analyzing text for preferences: %s...",
        user_text[:50]
    )

    # Extract context string if provided
    context_str = None
    if context:
        if "activity" in context:
            context_str = context["activity"]
        elif "topic" in context:
            context_str = context["topic"]

    try:
        # Extract preferences using LLM
        extracted = await extract_preferences_from_text(
            person_id=person_id,
            text=user_text,
            context=context_str,
        )

        if not extracted:
            return []

        # Load and update preference profile
        prefs = await get_or_create_preferences(person_id)

        for pref_data in extracted:
            domain = pref_data.get("domain", "custom")
            dimension = pref_data.get("dimension", "general")
            value = pref_data.get("value", 0.0)
            confidence = pref_data.get("confidence", 0.5)
            source_text = pref_data.get("source_text")

            # Determine strength from value
            if value <= -0.75:
                strength = PreferenceStrength.STRONG_DISLIKE
            elif value <= -0.25:
                strength = PreferenceStrength.DISLIKE
            elif value >= 0.75:
                strength = PreferenceStrength.STRONG_LIKE
            elif value >= 0.25:
                strength = PreferenceStrength.LIKE
            else:
                strength = PreferenceStrength.NEUTRAL

            # Create preference value
            pref_value = PreferenceValue(
                value=value,
                strength=strength,
                confidence=confidence,
                evidence_type=EvidenceType.INFERRED,
                source_text=source_text,
            )

            # Update profile
            prefs.set_preference(domain, dimension, pref_value)

            # Log event for audit
            await log_preference_event(
                person_id=person_id,
                domain=domain,
                dimension=dimension,
                value=value,
                evidence_type=EvidenceType.INFERRED,
                source_text=source_text,
                context={"full_text": user_text, "context": context_str},
            )

            LOGGER.info(
                "[preference_learning]   - %s/%s = %.2f (confidence: %.2f)",
                domain,
                dimension,
                value,
                confidence,
            )

        # Store updated profile
        await store_preferences(prefs)

        LOGGER.info(
            "[preference_learning] Learned %d preferences for %s",
            len(extracted),
            person_id[:8],
        )

        return extracted

    except Exception as e:
        LOGGER.exception("[preference_learning] Failed to extract preferences: %s", e)
        return []


async def should_learn_preferences(user_text: str) -> bool:
    """
    Quick check if text might contain learnable preferences.

    Use this for fast filtering before the async job.
    """
    if not user_text or len(user_text.strip()) < MIN_TEXT_LENGTH:
        return False
    return _has_preference_indicators(user_text)


async def get_learned_preferences_summary(person_id: str) -> Dict[str, Any]:
    """
    Get a summary of learned preferences for a person.

    Useful for debugging and showing users what Sakhi has learned.
    """
    prefs = await get_or_create_preferences(person_id)

    domain_summaries = {}
    total = 0

    for domain_name, domain_pref in prefs.domains.items():
        dimension_count = len(domain_pref.dimensions)
        total += dimension_count

        top_likes = domain_pref.get_top_preferences(3)
        top_dislikes = domain_pref.get_top_dislikes(3)

        domain_summaries[domain_name] = {
            "count": dimension_count,
            "top_likes": [
                {"dimension": k, "value": v.value}
                for k, v in top_likes if v.value > 0
            ],
            "top_dislikes": [
                {"dimension": k, "value": v.value}
                for k, v in top_dislikes
            ],
        }

    return {
        "domains": domain_summaries,
        "total_preferences": total,
        "domain_count": len(prefs.domains),
        "traits": [
            {"name": t.trait_name, "value": t.value}
            for t in prefs.traits
        ],
    }


async def learn_explicit_preference(
    person_id: str,
    domain: str,
    dimension: str,
    value: float,
    source_text: Optional[str] = None,
) -> bool:
    """
    Record an explicitly stated preference.

    Use this when the user directly tells us a preference,
    rather than inferring it from conversation.
    """
    prefs = await get_or_create_preferences(person_id)

    # Determine strength from value
    if value <= -0.75:
        strength = PreferenceStrength.STRONG_DISLIKE
    elif value <= -0.25:
        strength = PreferenceStrength.DISLIKE
    elif value >= 0.75:
        strength = PreferenceStrength.STRONG_LIKE
    elif value >= 0.25:
        strength = PreferenceStrength.LIKE
    else:
        strength = PreferenceStrength.NEUTRAL

    pref_value = PreferenceValue(
        value=value,
        strength=strength,
        confidence=0.9,  # High confidence for explicit statements
        evidence_type=EvidenceType.EXPLICIT,
        source_text=source_text,
    )

    prefs.set_preference(domain, dimension, pref_value)
    await store_preferences(prefs)

    await log_preference_event(
        person_id=person_id,
        domain=domain,
        dimension=dimension,
        value=value,
        evidence_type=EvidenceType.EXPLICIT,
        source_text=source_text,
    )

    return True


__all__ = [
    "extract_preferences_from_turn",
    "should_learn_preferences",
    "get_learned_preferences_summary",
    "learn_explicit_preference",
    "extract_preferences_from_text",
]
