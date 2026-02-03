"""
Recommendations API

Provides personalized Ayurvedic recommendations based on user's current state,
powered by knowledge graph reasoning and personal pattern learning.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as execute
from sakhi.apps.api.services.ayurveda.graph_reasoning import (
    query_balancing_recommendations,
    get_graph_stats,
    get_current_season,
    get_current_time_window,
)
from sakhi.apps.api.services.ayurveda.vikriti import (
    compute_current_vikriti,
    compute_baseline_drift,
    classify_friction_state,
)
from sakhi.apps.api.services.recommendations import (
    build_recommendation_context,
    generate_personalized_recommendations,
)
from sakhi.apps.api.services.ayurveda.food_recommendations import (
    get_food_recommendations as get_dosha_food_recommendations,
    get_quick_food_suggestion,
    score_food_for_dosha,
    MealType,
)

LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendationRequest(BaseModel):
    """Request body for recommendations endpoint."""
    season_override: Optional[str] = None
    time_override: Optional[str] = None
    dietary_preferences: Optional[Dict[str, Any]] = None


@router.get("/now/{person_id}")
async def get_current_recommendations(
    person_id: str,
    season: Optional[str] = None,
    time_window: Optional[str] = None,
):
    """
    Get personalized recommendations for right now.

    Uses the user's current friction state (Prakruti vs Vikriti drift)
    to query the Ayurvedic knowledge graph for balancing recommendations.

    Returns:
        - friction_state: Current state (Chaos/Intensity/Stagnation Friction)
        - drift_percentage: How far off baseline
        - recommendations:
            - immediate_actions: Quick wins (under 10 min)
            - foods_now: Best foods for current state
            - practices_today: Best practices for today
        - watch_for_symptoms: Symptoms to monitor
    """
    # Get user's operating system (Prakruti)
    personal_model = await dbfetch(
        """
        SELECT operating_system
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    if not personal_model:
        raise HTTPException(status_code=404, detail="User profile not found")

    operating_system = personal_model.get("operating_system") or {}

    # Compute current state (Vikriti)
    vikriti = await compute_current_vikriti(person_id)

    # Compute drift from baseline
    drift = compute_baseline_drift(operating_system, vikriti)

    # Classify friction state
    friction = classify_friction_state(drift)
    friction_state = friction.get("state", "Balanced")

    # Query knowledge graph for recommendations
    recommendations = await query_balancing_recommendations(
        person_id=person_id,
        friction_state=friction_state,
        season=season,
        time_of_day=time_window,
    )

    LOGGER.info(
        "[Recommendations] person=%s friction=%s drift=%.1f%%",
        person_id,
        friction_state,
        drift.get("drift_percentage", 0),
    )

    return {
        "person_id": person_id,
        "operating_system": operating_system.get("type", "Unknown"),
        "friction_state": friction_state,
        "friction_description": friction.get("description"),
        "drift_percentage": drift.get("drift_percentage", 0),
        "drift_direction": drift.get("direction"),
        "primary_contributor": drift.get("primary_contributor"),
        "context": {
            "season": recommendations.get("season", get_current_season()),
            "time_window": recommendations.get("time_window", get_current_time_window()),
            "seasonal_amplification": recommendations.get("seasonal_amplification", 1.0),
        },
        "recommendations": recommendations.get("recommendations", {}),
        "watch_for_symptoms": recommendations.get("watch_for_symptoms", []),
    }


@router.post("/now/{person_id}")
async def get_recommendations_with_preferences(
    person_id: str,
    request: RecommendationRequest,
):
    """
    Get recommendations with custom preferences.

    Allows overriding season, time, and specifying dietary restrictions.
    """
    # Get user's operating system
    personal_model = await dbfetch(
        """
        SELECT operating_system
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    if not personal_model:
        raise HTTPException(status_code=404, detail="User profile not found")

    operating_system = personal_model.get("operating_system") or {}

    # Compute current state
    vikriti = await compute_current_vikriti(person_id)
    drift = compute_baseline_drift(operating_system, vikriti)
    friction = classify_friction_state(drift)
    friction_state = friction.get("state", "Balanced")

    # Query with preferences
    recommendations = await query_balancing_recommendations(
        person_id=person_id,
        friction_state=friction_state,
        season=request.season_override,
        time_of_day=request.time_override,
        dietary_preferences=request.dietary_preferences,
    )

    return {
        "person_id": person_id,
        "friction_state": friction_state,
        "drift_percentage": drift.get("drift_percentage", 0),
        "applied_preferences": {
            "season": request.season_override,
            "time": request.time_override,
            "dietary": request.dietary_preferences,
        },
        "recommendations": recommendations.get("recommendations", {}),
    }


@router.get("/foods/{person_id}")
async def get_food_recommendations(
    person_id: str,
    dosha: Optional[str] = None,
    limit: int = 10,
):
    """
    Get food recommendations for a specific dosha or current state.

    If dosha is not specified, uses current friction state to determine.
    """
    from sakhi.apps.api.services.ayurveda.graph_reasoning import query_foods_for_dosha

    # If no dosha specified, compute from current state
    if not dosha:
        personal_model = await dbfetch(
            "SELECT operating_system FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        vikriti = await compute_current_vikriti(person_id)
        drift = compute_baseline_drift(
            (personal_model or {}).get("operating_system", {}),
            vikriti,
        )
        dosha = drift.get("primary_contributor", "vata")

    foods = await query_foods_for_dosha(dosha, "PACIFIES", limit=limit)

    return {
        "dosha": dosha,
        "pacifying_foods": foods,
        "season": get_current_season(),
    }


@router.get("/foods/dosha-aware/{person_id}")
async def get_dosha_aware_food_recommendations(
    person_id: str,
    meal: Optional[str] = None,
):
    """
    Get comprehensive dosha-aware food recommendations.

    Uses Ayurvedic principles combined with the user's current friction state
    to provide detailed food guidance including:
    - Qualities to favor/reduce
    - Tastes to emphasize
    - Meal-specific guidance
    - Recommended foods with Ayurvedic reasoning
    - Foods to avoid

    Args:
        person_id: The person's ID
        meal: Optional meal type (breakfast, lunch, dinner, snack)
    """
    meal_type = None
    if meal:
        try:
            meal_type = MealType(meal.lower())
        except ValueError:
            pass

    profile = await get_dosha_food_recommendations(person_id, meal_type)

    return {
        "status": "ok",
        "person_id": person_id,
        "friction_state": profile.friction_state,
        "dosha_context": profile.dosha_context,
        "general_guidance": profile.general_guidance,
        "qualities": {
            "favor": profile.favor_qualities,
            "reduce": profile.reduce_qualities,
        },
        "tastes": {
            "best": profile.best_tastes,
            "reduce": profile.reduce_tastes,
        },
        "meal_guidance": [
            {
                "meal": m.meal_type.value,
                "focus": m.focus,
                "timing": m.timing,
                "portion": m.portion,
                "suggestions": m.recommendations,
            }
            for m in profile.meal_guidance
        ],
        "recommended_foods": [
            {
                "name": f.name,
                "category": f.category.value,
                "why": f.why,
                "qualities": f.qualities,
            }
            for f in profile.recommended_foods
        ],
        "foods_to_avoid": profile.foods_to_avoid,
    }


@router.get("/foods/quick/{person_id}/{meal}")
async def get_quick_meal_suggestion(
    person_id: str,
    meal: str,
):
    """
    Get a quick food suggestion for a specific meal.

    Fast endpoint for getting meal recommendations without full context.

    Args:
        person_id: The person's ID
        meal: Meal type (breakfast, lunch, dinner, snack)
    """
    try:
        meal_type = MealType(meal.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid meal type: {meal}. Use: breakfast, lunch, dinner, snack")

    suggestion = await get_quick_food_suggestion(person_id, meal_type)

    return {
        "status": "ok",
        **suggestion,
    }


class FoodScoreRequest(BaseModel):
    """Request to score a food for current dosha state."""
    food_name: str
    qualities: Optional[List[str]] = None


@router.post("/foods/score/{person_id}")
async def score_food(
    person_id: str,
    request: FoodScoreRequest,
):
    """
    Score how appropriate a food is for the user's current state.

    Returns a 0-1 score and recommendation based on whether the food's
    qualities align with what the user needs right now.

    Args:
        person_id: The person's ID
        request: Food name and optional qualities
    """
    result = await score_food_for_dosha(
        person_id=person_id,
        food_name=request.food_name,
        food_qualities=request.qualities,
    )

    return {
        "status": "ok",
        **result,
    }


@router.get("/practices/{person_id}")
async def get_practice_recommendations(
    person_id: str,
    dosha: Optional[str] = None,
    limit: int = 10,
):
    """
    Get practice recommendations for a specific dosha or current state.
    """
    from sakhi.apps.api.services.ayurveda.graph_reasoning import query_practices_for_dosha

    if not dosha:
        personal_model = await dbfetch(
            "SELECT operating_system FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        vikriti = await compute_current_vikriti(person_id)
        drift = compute_baseline_drift(
            (personal_model or {}).get("operating_system", {}),
            vikriti,
        )
        dosha = drift.get("primary_contributor", "vata")

    practices = await query_practices_for_dosha(dosha, limit=limit)

    return {
        "dosha": dosha,
        "pacifying_practices": practices,
        "time_window": get_current_time_window(),
    }


@router.get("/graph/stats")
async def get_knowledge_graph_stats():
    """
    Get statistics about the Ayurvedic knowledge graph.

    Useful for verifying graph population.
    """
    stats = await get_graph_stats()
    return {
        "graph_stats": stats,
        "status": "populated" if stats.get("total_nodes", 0) > 100 else "needs_population",
    }


# =============================================================================
# Personalized Recommendations (Phase 1.4)
# =============================================================================

class FeedbackRequest(BaseModel):
    """Request to provide feedback on a recommendation."""
    item_name: str = Field(..., description="Name of the recommended item")
    item_type: str = Field(..., description="Type: food, practice, immediate_action")
    helpful: bool = Field(..., description="Was it helpful?")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="1-5 star rating")
    notes: Optional[str] = Field(default=None, description="Optional notes")


@router.get("/personalized/{person_id}")
async def get_personalized_recommendations(
    person_id: str,
    max_foods: int = 5,
    max_practices: int = 5,
):
    """
    Get truly personalized recommendations.

    This endpoint uses:
    - Ayurvedic knowledge graph as the base
    - Personal patterns (what's caused issues for YOU)
    - Historical effectiveness (what's worked for YOU)
    - Current state and seasonal context

    Returns recommendations with personal relevance explanations.
    """
    try:
        # Build full context
        context = await build_recommendation_context(person_id)

        # Generate personalized recommendations
        recommendations = await generate_personalized_recommendations(
            context=context,
            max_foods=max_foods,
            max_practices=max_practices,
        )

        return {
            "person_id": person_id,
            "friction_state": recommendations.friction_state,
            "urgency_level": recommendations.urgency_level,
            "personalization_confidence": recommendations.personalization_confidence,
            "why_this_state": recommendations.why_this_state,
            "personal_insight": recommendations.personal_insight,
            "recommendations": {
                "immediate_actions": [r.model_dump() for r in recommendations.immediate_actions],
                "foods": [r.model_dump() for r in recommendations.foods],
                "practices": [r.model_dump() for r in recommendations.practices],
            },
            "watch_for": recommendations.watch_for,
            "context": {
                "constitution": context.constitution.model_dump(),
                "temporal": context.temporal.model_dump(),
                "patterns_used": len(context.personal_patterns),
                "recent_activities": len(context.recent_activities),
            },
        }

    except Exception as e:
        LOGGER.error(f"[PersonalizedRecs] Error for {person_id}: {e}")
        # Fall back to basic recommendations
        return await get_current_recommendations(person_id)


@router.get("/personalized/{person_id}/context")
async def get_recommendation_context(person_id: str) -> Dict[str, Any]:
    """
    Get the full context used for personalization.

    Useful for debugging and understanding what data influences recommendations.
    """
    context = await build_recommendation_context(person_id)

    return {
        "person_id": person_id,
        "constitution": context.constitution.model_dump(),
        "current_state": context.current_state.model_dump(),
        "temporal": context.temporal.model_dump(),
        "personal_patterns": [p.model_dump() for p in context.personal_patterns],
        "recent_activities": [a.model_dump() for a in context.recent_activities],
        "historical_effectiveness": context.historical_effectiveness.model_dump(),
        "urgency_level": context.urgency_level,
        "personalization_confidence": context.personalization_confidence,
    }


@router.post("/personalized/{person_id}/feedback")
async def record_feedback(
    person_id: str,
    request: FeedbackRequest,
) -> Dict[str, Any]:
    """
    Record feedback on a recommendation.

    This feedback is used to improve future personalization.
    """
    try:
        # Record the feedback
        result = await dbfetch(
            """
            INSERT INTO recommendation_feedback (
                person_id, item_name, item_type,
                helpful, rating, notes,
                friction_state, season, time_of_day,
                feedback_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, now()
            )
            RETURNING id
            """,
            person_id,
            request.item_name,
            request.item_type,
            request.helpful,
            request.rating,
            request.notes,
            None,  # friction_state - could be passed in
            get_current_season(),
            get_current_time_window(),
            one=True,
        )

        LOGGER.info(
            "[Feedback] person=%s item=%s helpful=%s",
            person_id,
            request.item_name,
            request.helpful,
        )

        return {
            "status": "recorded",
            "feedback_id": str(result["id"]) if result else None,
        }

    except Exception as e:
        LOGGER.error(f"[Feedback] Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")


@router.get("/personalized/{person_id}/effectiveness")
async def get_effectiveness_report(person_id: str) -> Dict[str, Any]:
    """
    Get a report on what's been effective for this user.

    Based on feedback history.
    """
    # Get effective foods
    effective_foods = await dbfetch(
        """
        SELECT item_name, COUNT(*) FILTER (WHERE helpful = TRUE) as helpful_count,
               COUNT(*) as total_count
        FROM recommendation_feedback
        WHERE person_id = $1 AND item_type = 'food' AND helpful IS NOT NULL
        GROUP BY item_name
        HAVING COUNT(*) >= 2
        ORDER BY (COUNT(*) FILTER (WHERE helpful = TRUE)::FLOAT / COUNT(*)) DESC
        LIMIT 10
        """,
        person_id,
    )

    # Get effective practices
    effective_practices = await dbfetch(
        """
        SELECT item_name, COUNT(*) FILTER (WHERE helpful = TRUE) as helpful_count,
               COUNT(*) as total_count
        FROM recommendation_feedback
        WHERE person_id = $1 AND item_type = 'practice' AND helpful IS NOT NULL
        GROUP BY item_name
        HAVING COUNT(*) >= 2
        ORDER BY (COUNT(*) FILTER (WHERE helpful = TRUE)::FLOAT / COUNT(*)) DESC
        LIMIT 10
        """,
        person_id,
    )

    # Get items that haven't worked
    ineffective = await dbfetch(
        """
        SELECT item_name, item_type, COUNT(*) as times_tried
        FROM recommendation_feedback
        WHERE person_id = $1 AND helpful = FALSE
        GROUP BY item_name, item_type
        HAVING COUNT(*) >= 2
        ORDER BY COUNT(*) DESC
        LIMIT 10
        """,
        person_id,
    )

    return {
        "person_id": person_id,
        "effective_foods": list(effective_foods or []),
        "effective_practices": list(effective_practices or []),
        "ineffective_items": list(ineffective or []),
        "total_feedback_count": await _get_feedback_count(person_id),
    }


async def _get_feedback_count(person_id: str) -> int:
    """Get total feedback count for a user."""
    result = await dbfetch(
        "SELECT COUNT(*) as count FROM recommendation_feedback WHERE person_id = $1",
        person_id,
        one=True,
    )
    return result["count"] if result else 0


__all__ = ["router"]
