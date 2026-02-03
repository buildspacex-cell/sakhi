"""
Sensory Preferences Service
---------------------------
Deep preference tracking for how someone experiences the world.

Unlike basic "likes/dislikes", this tracks HOW someone likes things:
- Temperature preferences (hot drinks, cold food)
- Texture preferences (crunchy, smooth, chewy)
- Spice tolerance (mild, medium, hot)
- Presentation preferences (plated, family style)
- Ambiance preferences (quiet, lively, romantic)

This is what makes Sakhi truly "know you" - understanding not just
WHAT you like, but HOW you like it.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Sensory Preference Models
# =============================================================================

class SensoryCategory(str, Enum):
    """Categories of sensory preferences."""
    TEMPERATURE = "temperature"
    TEXTURE = "texture"
    SPICE = "spice"
    FLAVOR = "flavor"
    VISUAL = "visual"
    AMBIANCE = "ambiance"
    PORTION = "portion"
    SERVICE = "service"


class PreferenceStrength(str, Enum):
    """How strongly someone feels about a preference."""
    SLIGHT = "slight"  # Nice to have
    MODERATE = "moderate"  # Prefer this
    STRONG = "strong"  # Really want this
    MUST_HAVE = "must_have"  # Deal breaker


class SensoryPreference(BaseModel):
    """A single sensory preference."""
    category: SensoryCategory
    preference: str
    strength: PreferenceStrength = PreferenceStrength.MODERATE
    context: Optional[str] = None  # When this applies (e.g., "breakfast", "winter")
    source: Optional[str] = None  # How we learned this
    learned_at: Optional[datetime] = None
    confidence: float = 0.5


class SensoryProfile(BaseModel):
    """Complete sensory profile for a person."""
    person_id: str
    temperature: Dict[str, Any] = Field(default_factory=dict)
    texture: Dict[str, Any] = Field(default_factory=dict)
    spice: Dict[str, Any] = Field(default_factory=dict)
    flavor: Dict[str, Any] = Field(default_factory=dict)
    visual: Dict[str, Any] = Field(default_factory=dict)
    ambiance: Dict[str, Any] = Field(default_factory=dict)
    portion: Dict[str, Any] = Field(default_factory=dict)
    service: Dict[str, Any] = Field(default_factory=dict)
    last_updated: Optional[datetime] = None


# =============================================================================
# Sensory Preference Storage
# =============================================================================

async def get_sensory_profile(person_id: str) -> SensoryProfile:
    """
    Get the complete sensory profile for a person.

    Creates an empty profile if none exists.
    """
    row = await dbfetch(
        """
        SELECT * FROM sensory_preferences WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    if row:
        return SensoryProfile(
            person_id=person_id,
            temperature=_parse_json(row.get("temperature")),
            texture=_parse_json(row.get("texture")),
            spice=_parse_json(row.get("spice")),
            flavor=_parse_json(row.get("flavor")),
            visual=_parse_json(row.get("visual")),
            ambiance=_parse_json(row.get("ambiance")),
            portion=_parse_json(row.get("portion")),
            service=_parse_json(row.get("service")),
            last_updated=row.get("updated_at"),
        )

    # Create empty profile
    await dbexec(
        """
        INSERT INTO sensory_preferences (person_id)
        VALUES ($1)
        ON CONFLICT (person_id) DO NOTHING
        """,
        person_id,
    )

    return SensoryProfile(person_id=person_id)


async def update_sensory_preference(
    person_id: str,
    category: SensoryCategory,
    preference: str,
    value: Any,
    *,
    strength: PreferenceStrength = PreferenceStrength.MODERATE,
    context: Optional[str] = None,
    source: str = "conversation",
) -> None:
    """
    Update a specific sensory preference.

    Args:
        person_id: User's ID
        category: Which sensory category
        preference: The specific preference (e.g., "drinks_hot", "texture_crunchy")
        value: The preference value (e.g., True, "high", "avoid")
        strength: How strong the preference is
        context: When this applies (e.g., "morning", "summer")
        source: How we learned this (e.g., "conversation", "observation")
    """
    pref_data = {
        "value": value,
        "strength": strength.value,
        "context": context,
        "source": source,
        "learned_at": datetime.utcnow().isoformat(),
    }

    # Update the specific category's preferences
    await dbexec(
        f"""
        INSERT INTO sensory_preferences (person_id, {category.value})
        VALUES ($1, $2::jsonb)
        ON CONFLICT (person_id) DO UPDATE
        SET {category.value} = sensory_preferences.{category.value} || $2::jsonb,
            updated_at = NOW()
        """,
        person_id,
        json.dumps({preference: pref_data}),
    )

    LOGGER.info(
        "[sensory] Updated %s.%s for %s: %s",
        category.value,
        preference,
        person_id[:8],
        value,
    )


async def get_preference(
    person_id: str,
    category: SensoryCategory,
    preference: str,
) -> Optional[Dict[str, Any]]:
    """Get a specific sensory preference."""
    profile = await get_sensory_profile(person_id)
    category_prefs = getattr(profile, category.value, {})
    return category_prefs.get(preference)


# =============================================================================
# Temperature Preferences
# =============================================================================

async def set_temperature_preference(
    person_id: str,
    item_type: str,  # "drinks", "food", "soup"
    preference: str,  # "hot", "warm", "room_temp", "cold", "iced"
    **kwargs,
) -> None:
    """
    Set temperature preference for a type of item.

    Examples:
        - ("drinks", "hot") - Prefers hot drinks
        - ("soup", "very_hot") - Likes soup extra hot
        - ("salad", "cold") - Prefers cold salads
    """
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.TEMPERATURE,
        preference=f"{item_type}_temp",
        value=preference,
        **kwargs,
    )


async def get_temperature_preferences(person_id: str) -> Dict[str, Any]:
    """Get all temperature preferences."""
    profile = await get_sensory_profile(person_id)
    return profile.temperature


# =============================================================================
# Texture Preferences
# =============================================================================

async def set_texture_preference(
    person_id: str,
    texture: str,  # "crunchy", "smooth", "chewy", "crispy", "tender"
    preference: str,  # "love", "like", "neutral", "dislike", "avoid"
    **kwargs,
) -> None:
    """
    Set preference for a texture.

    Examples:
        - ("crunchy", "love") - Loves crunchy textures
        - ("mushy", "avoid") - Avoids mushy textures
    """
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.TEXTURE,
        preference=texture,
        value=preference,
        **kwargs,
    )


async def get_texture_preferences(person_id: str) -> Dict[str, Any]:
    """Get all texture preferences."""
    profile = await get_sensory_profile(person_id)
    return profile.texture


# =============================================================================
# Spice Preferences
# =============================================================================

async def set_spice_tolerance(
    person_id: str,
    level: str,  # "none", "mild", "medium", "hot", "very_hot", "extreme"
    *,
    cuisine_context: Optional[str] = None,  # e.g., "thai", "indian", "mexican"
    **kwargs,
) -> None:
    """
    Set spice tolerance level.

    Can be general or specific to a cuisine:
        - General: ("medium", None) - Medium spice across the board
        - Specific: ("hot", "thai") - Can handle hot Thai food
    """
    pref_name = f"tolerance_{cuisine_context}" if cuisine_context else "tolerance_general"

    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.SPICE,
        preference=pref_name,
        value=level,
        context=cuisine_context,
        **kwargs,
    )


async def get_spice_tolerance(
    person_id: str,
    cuisine: Optional[str] = None,
) -> str:
    """
    Get spice tolerance, optionally for a specific cuisine.

    Falls back to general tolerance if cuisine-specific not set.
    """
    profile = await get_sensory_profile(person_id)
    spice = profile.spice

    # Try cuisine-specific first
    if cuisine:
        specific = spice.get(f"tolerance_{cuisine}")
        if specific:
            return specific.get("value", "medium")

    # Fall back to general
    general = spice.get("tolerance_general")
    if general:
        return general.get("value", "medium")

    return "medium"  # Default


# =============================================================================
# Ambiance Preferences
# =============================================================================

async def set_ambiance_preference(
    person_id: str,
    aspect: str,  # "noise", "lighting", "seating", "crowd", "vibe"
    preference: str,  # varies by aspect
    **kwargs,
) -> None:
    """
    Set ambiance preference.

    Examples:
        - ("noise", "quiet") - Prefers quiet restaurants
        - ("lighting", "dim") - Likes dim lighting
        - ("seating", "booth") - Prefers booth seating
        - ("vibe", "romantic") - Likes romantic ambiance
    """
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.AMBIANCE,
        preference=aspect,
        value=preference,
        **kwargs,
    )


async def get_ambiance_preferences(person_id: str) -> Dict[str, Any]:
    """Get all ambiance preferences."""
    profile = await get_sensory_profile(person_id)
    return profile.ambiance


# =============================================================================
# Preference Learning from Conversation
# =============================================================================

async def learn_preference_from_text(
    person_id: str,
    text: str,
    context: Optional[str] = None,
) -> List[SensoryPreference]:
    """
    Extract and store sensory preferences from natural language.

    Uses LLM to identify preferences mentioned in conversation.

    Args:
        person_id: User's ID
        text: Text to analyze (e.g., "I hate when my coffee is lukewarm")
        context: Additional context

    Returns:
        List of preferences that were identified and stored
    """
    from sakhi.apps.api.core.llm import get_router

    prompt = f"""Analyze this text for sensory preferences:

"{text}"

Extract any preferences about:
- Temperature (hot/cold drinks, food temperature)
- Texture (crunchy, smooth, chewy, etc.)
- Spice level (mild, medium, hot)
- Flavors (sweet, salty, sour, bitter, umami)
- Visual presentation
- Ambiance (noise, lighting, crowd level)
- Portion sizes
- Service style

For each preference found, return JSON:
{{
    "preferences": [
        {{
            "category": "temperature|texture|spice|flavor|visual|ambiance|portion|service",
            "preference": "specific preference name",
            "value": "the preference value",
            "strength": "slight|moderate|strong|must_have",
            "context": "when this applies (optional)"
        }}
    ]
}}

If no sensory preferences are found, return: {{"preferences": []}}

Return ONLY the JSON."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-20250514",
            max_tokens=500,
        )

        content = response.content[0].text if response.content else "{}"
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        preferences = result.get("preferences", [])

        learned = []
        for pref in preferences:
            try:
                cat = SensoryCategory(pref.get("category"))
                strength = PreferenceStrength(pref.get("strength", "moderate"))

                await update_sensory_preference(
                    person_id=person_id,
                    category=cat,
                    preference=pref["preference"],
                    value=pref["value"],
                    strength=strength,
                    context=pref.get("context") or context,
                    source="conversation",
                )

                learned.append(SensoryPreference(
                    category=cat,
                    preference=pref["preference"],
                    strength=strength,
                    context=pref.get("context"),
                    source="conversation",
                    learned_at=datetime.utcnow(),
                ))
            except (ValueError, KeyError) as e:
                LOGGER.warning("[sensory] Failed to process preference: %s", e)
                continue

        LOGGER.info("[sensory] Learned %d preferences from text", len(learned))
        return learned

    except Exception as e:
        LOGGER.exception("[sensory] Failed to learn preferences: %s", e)
        return []


# =============================================================================
# Preference Retrieval for Context
# =============================================================================

async def get_dining_sensory_context(person_id: str) -> Dict[str, Any]:
    """
    Get sensory preferences formatted for dining recommendations.

    This is what gets used when Sakhi is helping choose a restaurant
    or order food.
    """
    profile = await get_sensory_profile(person_id)

    return {
        "temperature": {
            "drinks": _extract_value(profile.temperature, "drinks_temp", "any"),
            "food": _extract_value(profile.temperature, "food_temp", "any"),
        },
        "texture": {
            "loves": [k for k, v in profile.texture.items() if _extract_value(v, "value") == "love"],
            "avoids": [k for k, v in profile.texture.items() if _extract_value(v, "value") == "avoid"],
        },
        "spice_tolerance": await get_spice_tolerance(person_id),
        "ambiance": {
            k: _extract_value(v, "value")
            for k, v in profile.ambiance.items()
        },
        "portion": _extract_value(profile.portion, "size", "regular"),
    }


def _parse_json(value: Any) -> Dict[str, Any]:
    """Parse JSON field."""
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _extract_value(data: Any, key: str, default: Any = None) -> Any:
    """Extract value from preference data."""
    if isinstance(data, dict):
        if key in data:
            if isinstance(data[key], dict):
                return data[key].get("value", default)
            return data[key]
        return data.get("value", default)
    return default


__all__ = [
    "SensoryCategory",
    "PreferenceStrength",
    "SensoryPreference",
    "SensoryProfile",
    "get_sensory_profile",
    "update_sensory_preference",
    "get_preference",
    "set_temperature_preference",
    "get_temperature_preferences",
    "set_texture_preference",
    "get_texture_preferences",
    "set_spice_tolerance",
    "get_spice_tolerance",
    "set_ambiance_preference",
    "get_ambiance_preferences",
    "learn_preference_from_text",
    "get_dining_sensory_context",
]
