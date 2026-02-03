"""
Sakhi Memory Services
---------------------
Multi-tier memory system that enables Sakhi to truly "know you".

Memory Architecture:
- Short-term Memory (STM): Recent conversation context
- Long-term Memory: Persistent facts, preferences, relationships
- Episodic Memory: Specific events and experiences
- Memory Graph: Interconnected knowledge about the person
- Sensory Preferences: How you experience the world
- Food Memory: What you eat, where, and how you felt

This is what makes Sakhi more than a chatbot - it remembers,
learns, and builds understanding over time.
"""

# Core memory operations
from sakhi.apps.api.services.memory.recall import (
    recall_advanced,
    recall_with_keyword_boost,
    recall_semantic_only,
)

from sakhi.apps.api.services.memory.bm25 import (
    bm25_search_journals,
    bm25_search_reflections,
    bm25_search_memory_nodes,
    bm25_search_facts,
    bm25_search_all,
    merge_hybrid_scores,
)

# Sensory preferences - how you experience things
from sakhi.apps.api.services.memory.sensory_preferences import (
    SensoryCategory,
    PreferenceStrength,
    SensoryPreference,
    SensoryProfile,
    get_sensory_profile,
    update_sensory_preference,
    get_preference,
    set_temperature_preference,
    get_temperature_preferences,
    set_texture_preference,
    get_texture_preferences,
    set_spice_tolerance,
    get_spice_tolerance,
    set_ambiance_preference,
    get_ambiance_preferences,
    learn_preference_from_text,
    get_dining_sensory_context,
)

# Food memory - what you eat
from sakhi.apps.api.services.memory.food_memory import (
    MealType,
    DiningContext,
    Rating,
    FoodExperience,
    RestaurantMemory,
    CuisineExperience,
    record_meal,
    get_recent_meals,
    get_experiences_at_restaurant,
    get_experiences_with_dish,
    get_restaurant_memory,
    get_favorite_restaurants,
    get_cuisine_experience,
    get_cuisine_breakdown,
    get_dishes_to_try_again,
    get_loved_dishes,
    search_food_memory,
    last_time_ate,
    last_time_at_restaurant,
    get_food_context_for_recommendations,
)

# "Last time" queries across all memory sources
from sakhi.apps.api.services.memory.last_time import (
    LastTimeResult,
    last_time,
    last_time_with_person,
    last_time_at_place,
    last_time_doing,
    days_since,
)

__all__ = [
    # Recall
    "recall_advanced",
    "recall_with_keyword_boost",
    "recall_semantic_only",
    # BM25
    "bm25_search_journals",
    "bm25_search_reflections",
    "bm25_search_memory_nodes",
    "bm25_search_facts",
    "bm25_search_all",
    "merge_hybrid_scores",
    # Sensory Preferences
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
    # Food Memory
    "MealType",
    "DiningContext",
    "Rating",
    "FoodExperience",
    "RestaurantMemory",
    "CuisineExperience",
    "record_meal",
    "get_recent_meals",
    "get_experiences_at_restaurant",
    "get_experiences_with_dish",
    "get_restaurant_memory",
    "get_favorite_restaurants",
    "get_cuisine_experience",
    "get_cuisine_breakdown",
    "get_dishes_to_try_again",
    "get_loved_dishes",
    "search_food_memory",
    "last_time_ate",
    "last_time_at_restaurant",
    "get_food_context_for_recommendations",
    # Last Time Lookup
    "LastTimeResult",
    "last_time",
    "last_time_with_person",
    "last_time_at_place",
    "last_time_doing",
    "days_since",
]
