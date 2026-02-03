"""
Dosha-Aware Food Recommendations

Combines Ayurvedic principles with user's:
- Current friction state (chaos/intensity/stagnation/balanced)
- Personal food preferences (from preference framework)
- Dietary restrictions and allergies

Food Principles by Dosha:
- Vata (Chaos): Warm, grounding, oily, sweet/sour/salty - avoid cold, dry, raw
- Pitta (Intensity): Cooling, moderate, sweet/bitter/astringent - avoid spicy, sour, fermented
- Kapha (Stagnation): Light, warming, dry, pungent/bitter/astringent - avoid heavy, oily, sweet
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from sakhi.apps.api.services.ayurveda.vikriti import (
    get_full_friction_state,
    FRICTION_STATES,
)
from sakhi.apps.api.services.memory.preference_framework import (
    load_preferences,
    PreferenceDomain,
)

LOGGER = logging.getLogger(__name__)


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class FoodCategory(str, Enum):
    GRAINS = "grains"
    PROTEINS = "proteins"
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    DAIRY = "dairy"
    BEVERAGES = "beverages"
    SPICES = "spices"
    OILS = "oils"
    SWEETENERS = "sweeteners"


class FoodRecommendation(BaseModel):
    """A single food recommendation."""
    name: str
    category: FoodCategory
    why: str  # Ayurvedic reasoning
    qualities: List[str] = Field(default_factory=list)  # warm, grounding, light, etc.
    best_for: List[str] = Field(default_factory=list)  # meal types
    avoid_if: Optional[str] = None  # dietary restriction warning


class MealGuidance(BaseModel):
    """Guidance for a specific meal type."""
    meal_type: MealType
    focus: str  # What this meal should emphasize
    timing: str  # When to eat
    portion: str  # How much
    recommendations: List[str] = Field(default_factory=list)


class DoshaFoodProfile(BaseModel):
    """Complete food profile based on dosha state."""
    friction_state: str
    dosha_context: str
    general_guidance: str
    favor_qualities: List[str] = Field(default_factory=list)
    reduce_qualities: List[str] = Field(default_factory=list)
    best_tastes: List[str] = Field(default_factory=list)
    reduce_tastes: List[str] = Field(default_factory=list)
    meal_guidance: List[MealGuidance] = Field(default_factory=list)
    recommended_foods: List[FoodRecommendation] = Field(default_factory=list)
    foods_to_avoid: List[str] = Field(default_factory=list)


# ============================================================================
# Ayurvedic Food Knowledge Base
# ============================================================================

DOSHA_FOOD_PROFILES = {
    "chaos": {  # Vata elevated
        "general_guidance": "Your energy is scattered. Focus on warm, grounding, nourishing foods that bring stability and calmness.",
        "favor_qualities": ["warm", "oily", "grounding", "smooth", "soft", "moist"],
        "reduce_qualities": ["cold", "dry", "light", "raw", "rough", "hard"],
        "best_tastes": ["sweet", "sour", "salty"],
        "reduce_tastes": ["bitter", "pungent", "astringent"],
        "meal_guidance": [
            {
                "meal_type": "breakfast",
                "focus": "Warm, grounding start",
                "timing": "Before 8am - don't skip!",
                "portion": "Moderate, satisfying",
                "recommendations": [
                    "Warm oatmeal with ghee and cinnamon",
                    "Rice porridge with dates",
                    "Warm milk with turmeric",
                    "Scrambled eggs with avocado",
                ],
            },
            {
                "meal_type": "lunch",
                "focus": "Largest meal of the day",
                "timing": "Between 12-1pm when digestion is strongest",
                "portion": "Full, satisfying meal",
                "recommendations": [
                    "Warm grain bowl with roasted vegetables",
                    "Soup or stew with bread",
                    "Pasta with olive oil and vegetables",
                    "Rice with dal and ghee",
                ],
            },
            {
                "meal_type": "dinner",
                "focus": "Light but warm",
                "timing": "Before 7pm",
                "portion": "Smaller than lunch",
                "recommendations": [
                    "Warm soup",
                    "Khichdi (rice and lentils)",
                    "Steamed vegetables with quinoa",
                    "Warm milk before bed",
                ],
            },
        ],
        "recommended_foods": [
            {"name": "Oats (cooked)", "category": "grains", "why": "Warm and grounding", "qualities": ["warm", "grounding"]},
            {"name": "Rice", "category": "grains", "why": "Easy to digest, calming", "qualities": ["grounding", "soft"]},
            {"name": "Sweet potato", "category": "vegetables", "why": "Sweet, grounding, nourishing", "qualities": ["warm", "sweet", "grounding"]},
            {"name": "Avocado", "category": "vegetables", "why": "Oily, grounding, satisfying", "qualities": ["oily", "grounding"]},
            {"name": "Bananas (ripe)", "category": "fruits", "why": "Sweet, grounding, easy to digest", "qualities": ["sweet", "grounding"]},
            {"name": "Warm milk", "category": "dairy", "why": "Calming, nourishing for Vata", "qualities": ["warm", "nourishing"]},
            {"name": "Ghee", "category": "oils", "why": "Best oil for Vata - grounding and lubricating", "qualities": ["oily", "grounding"]},
            {"name": "Ginger tea", "category": "beverages", "why": "Warming, aids digestion", "qualities": ["warm", "stimulating"]},
            {"name": "Dates", "category": "sweeteners", "why": "Natural sweetness, grounding energy", "qualities": ["sweet", "grounding"]},
            {"name": "Cinnamon", "category": "spices", "why": "Warming, calming", "qualities": ["warm", "sweet"]},
        ],
        "foods_to_avoid": [
            "Raw salads (too cold and dry)",
            "Crackers and chips (dry, rough)",
            "Iced drinks",
            "Popcorn (dry, light)",
            "Dried fruits in excess",
            "Caffeine in excess (increases anxiety)",
            "Very spicy food",
        ],
    },
    "intensity": {  # Pitta elevated
        "general_guidance": "You're running hot. Focus on cooling, calming foods that reduce heat and intensity without dampening your fire completely.",
        "favor_qualities": ["cool", "dense", "dry", "mild"],
        "reduce_qualities": ["hot", "oily", "light", "sharp"],
        "best_tastes": ["sweet", "bitter", "astringent"],
        "reduce_tastes": ["sour", "salty", "pungent"],
        "meal_guidance": [
            {
                "meal_type": "breakfast",
                "focus": "Cool, substantial start",
                "timing": "Before 8am",
                "portion": "Moderate",
                "recommendations": [
                    "Sweet fruit with coconut",
                    "Cool oatmeal with maple syrup",
                    "Toast with almond butter",
                    "Smoothie with sweet fruits",
                ],
            },
            {
                "meal_type": "lunch",
                "focus": "Largest meal - cooling proteins",
                "timing": "Between 12-1pm",
                "portion": "Satisfying but not heavy",
                "recommendations": [
                    "Salad with grilled chicken",
                    "Buddha bowl with cooling vegetables",
                    "Rice with mild curry",
                    "Pasta with pesto (not spicy)",
                ],
            },
            {
                "meal_type": "dinner",
                "focus": "Light and cooling",
                "timing": "Before 7pm",
                "portion": "Light",
                "recommendations": [
                    "Steamed vegetables with rice",
                    "Cool cucumber soup",
                    "Light grain salad",
                    "Coconut milk dessert",
                ],
            },
        ],
        "recommended_foods": [
            {"name": "Basmati rice", "category": "grains", "why": "Cooling, easy to digest", "qualities": ["cool", "light"]},
            {"name": "Oats", "category": "grains", "why": "Cooling when not served too hot", "qualities": ["cool", "grounding"]},
            {"name": "Cucumber", "category": "vegetables", "why": "Very cooling, hydrating", "qualities": ["cool", "moist"]},
            {"name": "Leafy greens", "category": "vegetables", "why": "Bitter taste reduces Pitta", "qualities": ["cool", "bitter"]},
            {"name": "Sweet fruits", "category": "fruits", "why": "Mangoes, grapes, melons - cooling and sweet", "qualities": ["cool", "sweet"]},
            {"name": "Coconut", "category": "fruits", "why": "Very cooling, balances Pitta", "qualities": ["cool", "sweet"]},
            {"name": "Milk", "category": "dairy", "why": "Cooling and calming", "qualities": ["cool", "sweet"]},
            {"name": "Coconut oil", "category": "oils", "why": "Cooling oil for Pitta", "qualities": ["cool", "mild"]},
            {"name": "Mint tea", "category": "beverages", "why": "Cooling, refreshing", "qualities": ["cool", "calming"]},
            {"name": "Coriander", "category": "spices", "why": "Cooling spice, aids digestion", "qualities": ["cool", "mild"]},
        ],
        "foods_to_avoid": [
            "Very spicy food",
            "Sour foods (vinegar, citrus in excess)",
            "Fermented foods (kimchi, sauerkraut)",
            "Alcohol",
            "Fried foods",
            "Red meat in excess",
            "Coffee in excess",
            "Hot peppers",
        ],
    },
    "stagnation": {  # Kapha elevated
        "general_guidance": "Energy feels stuck and heavy. Focus on light, stimulating foods that get things moving without overwhelming your system.",
        "favor_qualities": ["light", "warm", "dry", "stimulating"],
        "reduce_qualities": ["heavy", "cold", "oily", "dense"],
        "best_tastes": ["pungent", "bitter", "astringent"],
        "reduce_tastes": ["sweet", "sour", "salty"],
        "meal_guidance": [
            {
                "meal_type": "breakfast",
                "focus": "Light or skip - Kapha doesn't need big breakfast",
                "timing": "After 9am if hungry",
                "portion": "Small or none",
                "recommendations": [
                    "Hot ginger tea",
                    "Light fruit (apple, pear)",
                    "Small portion of warm cereal",
                    "Skip if not hungry!",
                ],
            },
            {
                "meal_type": "lunch",
                "focus": "Main meal of the day",
                "timing": "Between 12-1pm",
                "portion": "Moderate - don't overeat",
                "recommendations": [
                    "Large salad with light protein",
                    "Soup with lots of vegetables",
                    "Stir-fry with minimal oil",
                    "Grain bowl with spices",
                ],
            },
            {
                "meal_type": "dinner",
                "focus": "Very light",
                "timing": "Before 6pm if possible",
                "portion": "Small",
                "recommendations": [
                    "Vegetable soup",
                    "Steamed vegetables",
                    "Light salad",
                    "Can skip if not hungry",
                ],
            },
        ],
        "recommended_foods": [
            {"name": "Millet", "category": "grains", "why": "Light, dry grain perfect for Kapha", "qualities": ["light", "dry"]},
            {"name": "Buckwheat", "category": "grains", "why": "Stimulating, not heavy", "qualities": ["light", "warming"]},
            {"name": "Leafy greens", "category": "vegetables", "why": "Light, bitter, stimulating", "qualities": ["light", "bitter"]},
            {"name": "Cruciferous vegetables", "category": "vegetables", "why": "Broccoli, cauliflower - light and cleansing", "qualities": ["light", "dry"]},
            {"name": "Apples", "category": "fruits", "why": "Astringent, light, cleansing", "qualities": ["light", "astringent"]},
            {"name": "Berries", "category": "fruits", "why": "Light, not too sweet", "qualities": ["light", "astringent"]},
            {"name": "Honey (in moderation)", "category": "sweeteners", "why": "Only sweetener that reduces Kapha", "qualities": ["warming", "light"]},
            {"name": "Ginger", "category": "spices", "why": "Stimulating, aids digestion", "qualities": ["warming", "stimulating"]},
            {"name": "Black pepper", "category": "spices", "why": "Stimulates metabolism", "qualities": ["warming", "stimulating"]},
            {"name": "Green tea", "category": "beverages", "why": "Stimulating without being harsh", "qualities": ["light", "stimulating"]},
        ],
        "foods_to_avoid": [
            "Heavy, creamy foods",
            "Excessive dairy",
            "Fried foods",
            "Sweet desserts",
            "White sugar",
            "Cold foods and drinks",
            "Excessive bread/pasta",
            "Red meat",
            "Excessive oil/butter",
        ],
    },
    "balanced": {
        "general_guidance": "You're in good balance! Focus on seasonal eating and maintaining variety. All six tastes in moderation.",
        "favor_qualities": ["fresh", "seasonal", "varied", "moderate"],
        "reduce_qualities": ["processed", "stale", "extreme"],
        "best_tastes": ["all in balance"],
        "reduce_tastes": ["none specifically - maintain variety"],
        "meal_guidance": [
            {
                "meal_type": "breakfast",
                "focus": "Nourishing, seasonal",
                "timing": "When hungry, before 9am",
                "portion": "According to hunger",
                "recommendations": [
                    "Seasonal fresh fruit",
                    "Whole grain toast or oatmeal",
                    "Eggs with vegetables",
                    "Smoothie with seasonal produce",
                ],
            },
            {
                "meal_type": "lunch",
                "focus": "Largest meal with variety",
                "timing": "Between 12-1pm",
                "portion": "Satisfying",
                "recommendations": [
                    "Balanced plate with protein, grain, vegetables",
                    "Variety of colors and tastes",
                    "Seasonal ingredients",
                ],
            },
            {
                "meal_type": "dinner",
                "focus": "Lighter than lunch",
                "timing": "Before 7pm",
                "portion": "Moderate",
                "recommendations": [
                    "Light protein with vegetables",
                    "Soup or salad",
                    "Easy to digest options",
                ],
            },
        ],
        "recommended_foods": [
            {"name": "Seasonal vegetables", "category": "vegetables", "why": "Nature provides what you need each season", "qualities": ["fresh", "vital"]},
            {"name": "Whole grains", "category": "grains", "why": "Sustained energy", "qualities": ["grounding", "nourishing"]},
            {"name": "Fresh fruits", "category": "fruits", "why": "Natural sweetness, vitamins", "qualities": ["fresh", "vital"]},
            {"name": "Variety of proteins", "category": "proteins", "why": "Balanced nutrition", "qualities": ["nourishing"]},
            {"name": "Healthy fats", "category": "oils", "why": "Ghee, olive oil, avocado", "qualities": ["nourishing"]},
            {"name": "Herbal teas", "category": "beverages", "why": "Hydrating without stimulants", "qualities": ["calming", "hydrating"]},
        ],
        "foods_to_avoid": [
            "Processed foods",
            "Excessive sugar",
            "Very stale or leftover food",
            "Eating the same thing repeatedly",
        ],
    },
}


# ============================================================================
# Main Functions
# ============================================================================

async def get_food_recommendations(
    person_id: str,
    meal_type: Optional[MealType] = None,
) -> DoshaFoodProfile:
    """
    Get personalized food recommendations based on current dosha state.

    Args:
        person_id: The person's ID
        meal_type: Optional specific meal type to focus on

    Returns:
        Complete food profile with recommendations
    """
    # Get current friction state
    try:
        full_state = await get_full_friction_state(person_id)
        friction_state = full_state.get("friction", {}).get("state", "balanced")
        dosha = full_state.get("friction", {}).get("dosha")
        drift = full_state.get("drift", {}).get("drift_percentage", 0)
    except Exception as e:
        LOGGER.warning("[food_recommendations] Failed to get friction state: %s", e)
        friction_state = "balanced"
        dosha = None
        drift = 0

    # Get food profile for this state
    profile_data = DOSHA_FOOD_PROFILES.get(friction_state, DOSHA_FOOD_PROFILES["balanced"])

    # Build context string
    if friction_state == "balanced":
        dosha_context = "You're in balance. Eat seasonally and maintain variety."
    else:
        dosha_name = {"chaos": "Vata", "intensity": "Pitta", "stagnation": "Kapha"}.get(friction_state, "")
        dosha_context = f"{dosha_name} is elevated ({drift:.0f}% drift from baseline). Food can help restore balance."

    # Build meal guidance
    meal_guidance = []
    for mg in profile_data.get("meal_guidance", []):
        guidance = MealGuidance(
            meal_type=MealType(mg["meal_type"]),
            focus=mg["focus"],
            timing=mg["timing"],
            portion=mg["portion"],
            recommendations=mg["recommendations"],
        )
        # If specific meal requested, only include that one
        if meal_type is None or guidance.meal_type == meal_type:
            meal_guidance.append(guidance)

    # Build food recommendations
    recommended_foods = []
    for food in profile_data.get("recommended_foods", []):
        rec = FoodRecommendation(
            name=food["name"],
            category=FoodCategory(food["category"]),
            why=food["why"],
            qualities=food.get("qualities", []),
        )
        recommended_foods.append(rec)

    # Check user preferences and filter/adjust
    try:
        preferences = await load_preferences(person_id)
        if preferences and "food" in preferences.domains:
            food_prefs = preferences.domains["food"]
            # Could filter out foods that conflict with strong dislikes
            # For now, just log that we have preferences
            LOGGER.info(
                "[food_recommendations] User has %d food preferences stored",
                len(food_prefs.dimensions),
            )
    except Exception as e:
        LOGGER.debug("[food_recommendations] No preferences loaded: %s", e)

    return DoshaFoodProfile(
        friction_state=friction_state,
        dosha_context=dosha_context,
        general_guidance=profile_data["general_guidance"],
        favor_qualities=profile_data["favor_qualities"],
        reduce_qualities=profile_data["reduce_qualities"],
        best_tastes=profile_data["best_tastes"],
        reduce_tastes=profile_data["reduce_tastes"],
        meal_guidance=meal_guidance,
        recommended_foods=recommended_foods,
        foods_to_avoid=profile_data["foods_to_avoid"],
    )


async def get_quick_food_suggestion(
    person_id: str,
    meal_type: MealType,
) -> Dict[str, Any]:
    """
    Get a quick food suggestion for a specific meal.

    Returns just the essential info for the given meal type.
    """
    profile = await get_food_recommendations(person_id, meal_type)

    meal = next((m for m in profile.meal_guidance if m.meal_type == meal_type), None)

    if not meal:
        return {
            "meal_type": meal_type.value,
            "suggestion": "Eat according to your hunger",
            "state": profile.friction_state,
        }

    # Pick relevant food recommendations
    relevant_foods = [
        f.name for f in profile.recommended_foods[:5]
    ]

    return {
        "meal_type": meal_type.value,
        "state": profile.friction_state,
        "focus": meal.focus,
        "timing": meal.timing,
        "portion": meal.portion,
        "suggestions": meal.recommendations[:3],
        "good_foods": relevant_foods,
        "context": profile.dosha_context,
    }


async def score_food_for_dosha(
    person_id: str,
    food_name: str,
    food_qualities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Score how appropriate a specific food is for the person's current state.

    Args:
        person_id: The person's ID
        food_name: Name of the food to score
        food_qualities: Optional list of qualities (warm, cold, dry, oily, etc.)

    Returns:
        Score (0-1), reasoning, and recommendation
    """
    profile = await get_food_recommendations(person_id)

    # Simple scoring based on quality matching
    score = 0.5  # Neutral start

    if food_qualities:
        # Check favored qualities
        favored_matches = len(set(food_qualities) & set(profile.favor_qualities))
        # Check reduce qualities
        reduce_matches = len(set(food_qualities) & set(profile.reduce_qualities))

        score += favored_matches * 0.15
        score -= reduce_matches * 0.15

    # Clamp to 0-1
    score = max(0.0, min(1.0, score))

    # Generate recommendation
    if score >= 0.7:
        recommendation = "Great choice for your current state!"
    elif score >= 0.5:
        recommendation = "This is okay in moderation."
    elif score >= 0.3:
        recommendation = "Not ideal right now, but occasional is fine."
    else:
        recommendation = "Consider alternatives that better match your current needs."

    return {
        "food": food_name,
        "score": round(score, 2),
        "recommendation": recommendation,
        "current_state": profile.friction_state,
        "favor_qualities": profile.favor_qualities,
        "your_food_qualities": food_qualities or [],
    }


__all__ = [
    "get_food_recommendations",
    "get_quick_food_suggestion",
    "score_food_for_dosha",
    "DoshaFoodProfile",
    "FoodRecommendation",
    "MealGuidance",
    "MealType",
    "FoodCategory",
]
