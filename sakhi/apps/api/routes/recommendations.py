"""
Recommendations API

Provides personalized Ayurvedic recommendations based on user's current state,
powered by knowledge graph reasoning.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch
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


__all__ = ["router"]
