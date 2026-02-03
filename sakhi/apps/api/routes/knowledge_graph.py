"""
Knowledge Graph API Routes
--------------------------
Endpoints for Ayurvedic knowledge graph, causal reasoning, and pattern learning.

These endpoints enable:
- "Why am I feeling X?" queries (causal reasoning)
- Personal pattern detection and retrieval
- Balancing recommendations based on current state
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sakhi.apps.api.services.ayurveda import (
    # Graph reasoning
    query_balancing_recommendations,
    query_foods_for_dosha,
    query_practices_for_dosha,
    query_symptoms_for_dosha,
    get_graph_stats,
    # Causal reasoning
    explain_symptom,
    explain_friction_state,
    trace_causal_chain,
    # Pattern learning
    process_entry_for_patterns,
    get_learned_patterns,
)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Graph"])


# =============================================================================
# Request Models
# =============================================================================

class SymptomExplainRequest(BaseModel):
    """Request to explain a symptom."""
    symptom: str = Field(..., description="The symptom to explain (e.g., 'anxious', 'tired')")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (time of day, recent activities)"
    )


class FrictionExplainRequest(BaseModel):
    """Request to explain a friction state."""
    friction_state: str = Field(
        ...,
        description="The friction state (e.g., 'Chaos Friction', 'Intensity Friction')"
    )
    recent_signals: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Recent signals from memory/journal"
    )


class RecommendationRequest(BaseModel):
    """Request for balancing recommendations."""
    friction_state: str = Field(..., description="Current friction state")
    season: Optional[str] = Field(default=None, description="Override season")
    time_of_day: Optional[str] = Field(default=None, description="Override time window")
    dietary_preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dietary restrictions"
    )


class PatternProcessRequest(BaseModel):
    """Request to process entry for patterns."""
    entry_text: str = Field(..., description="Journal entry text")
    entry_id: Optional[str] = Field(default=None, description="Entry ID")
    entry_time: Optional[datetime] = Field(default=None, description="Entry timestamp")


# =============================================================================
# Causal Reasoning Endpoints
# =============================================================================

@router.post("/{person_id}/explain/symptom")
async def explain_symptom_endpoint(
    person_id: str,
    request: SymptomExplainRequest,
) -> Dict[str, Any]:
    """
    Explain why the user might be experiencing a symptom.

    This is the "Why am I feeling X?" endpoint that:
    - Checks personal patterns (what's caused this for YOU before)
    - Looks at recent behaviors
    - Incorporates Ayurvedic knowledge
    - Returns a coherent explanation

    Example symptoms: anxious, tired, scattered, irritable, stuck, heavy
    """
    explanation = await explain_symptom(
        person_id=person_id,
        symptom=request.symptom,
        context=request.context,
    )

    return {
        "person_id": person_id,
        "symptom": request.symptom,
        "dosha_context": explanation.dosha_context,
        "primary_causes": [c.model_dump() for c in explanation.primary_causes],
        "contributing_factors": [f.model_dump() for f in explanation.contributing_factors],
        "seasonal_influence": explanation.seasonal_influence,
        "has_personal_patterns": explanation.personal_pattern_match,
        "explanation": explanation.explanation_text,
    }


@router.post("/{person_id}/explain/friction")
async def explain_friction_endpoint(
    person_id: str,
    request: FrictionExplainRequest,
) -> Dict[str, Any]:
    """
    Explain why the user is in a particular friction state.

    Friction states:
    - Chaos Friction (Vata imbalance) - scattered, anxious, overwhelmed
    - Intensity Friction (Pitta imbalance) - irritable, burnout, perfectionism
    - Stagnation Friction (Kapha imbalance) - stuck, heavy, unmotivated
    """
    explanation = await explain_friction_state(
        person_id=person_id,
        friction_state=request.friction_state,
        recent_signals=request.recent_signals,
    )

    return {
        "person_id": person_id,
        "friction_state": request.friction_state,
        "dosha_context": explanation.dosha_context,
        "primary_causes": [c.model_dump() for c in explanation.primary_causes],
        "contributing_factors": [f.model_dump() for f in explanation.contributing_factors],
        "explanation": explanation.explanation_text,
    }


@router.get("/{person_id}/trace/{effect}")
async def trace_causal_chain_endpoint(
    person_id: str,
    effect: str,
    depth: int = 2,
) -> Dict[str, Any]:
    """
    Trace causal chains backward from an effect.

    Enables deeper "why" questions:
    - "Why am I anxious?" -> "Late dinners"
    - "Why am I eating late?" -> "Work stress"

    Args:
        effect: The effect to trace (e.g., "anxiety")
        depth: How many hops to trace (default 2)
    """
    chains = await trace_causal_chain(
        person_id=person_id,
        effect=effect,
        depth=depth,
    )

    return {
        "person_id": person_id,
        "effect": effect,
        "causal_chains": chains,
        "chain_count": len(chains),
    }


# =============================================================================
# Recommendation Endpoints
# =============================================================================

@router.post("/{person_id}/recommendations")
async def get_recommendations(
    person_id: str,
    request: RecommendationRequest,
) -> Dict[str, Any]:
    """
    Get personalized balancing recommendations.

    Based on:
    - Current friction state
    - Season and time of day
    - User's dietary preferences
    - Ayurvedic knowledge graph
    """
    return await query_balancing_recommendations(
        person_id=person_id,
        friction_state=request.friction_state,
        season=request.season,
        time_of_day=request.time_of_day,
        dietary_preferences=request.dietary_preferences,
    )


@router.get("/{person_id}/foods/{dosha}")
async def get_foods_for_dosha(
    person_id: str,
    dosha: str,
    relation: str = "PACIFIES",
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Get foods that pacify or aggravate a dosha.

    Args:
        dosha: 'vata', 'pitta', or 'kapha'
        relation: 'PACIFIES' or 'AGGRAVATES'
    """
    foods = await query_foods_for_dosha(dosha, relation, limit)

    return {
        "dosha": dosha,
        "relation": relation,
        "foods": foods,
    }


@router.get("/{person_id}/practices/{dosha}")
async def get_practices_for_dosha(
    person_id: str,
    dosha: str,
    limit: int = 15,
) -> Dict[str, Any]:
    """Get practices that pacify a dosha."""
    practices = await query_practices_for_dosha(dosha, limit)

    return {
        "dosha": dosha,
        "practices": practices,
    }


@router.get("/{person_id}/symptoms/{dosha}")
async def get_symptoms_for_dosha(
    person_id: str,
    dosha: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get symptoms that indicate a dosha imbalance."""
    symptoms = await query_symptoms_for_dosha(dosha, limit)

    return {
        "dosha": dosha,
        "symptoms": symptoms,
    }


# =============================================================================
# Pattern Learning Endpoints
# =============================================================================

@router.post("/{person_id}/patterns/process")
async def process_for_patterns(
    person_id: str,
    request: PatternProcessRequest,
) -> Dict[str, Any]:
    """
    Process a journal entry for pattern learning.

    This extracts behaviors and symptoms, logs them,
    and runs pattern detection to learn correlations.

    Call this during memory ingestion.
    """
    return await process_entry_for_patterns(
        person_id=person_id,
        entry_text=request.entry_text,
        entry_id=request.entry_id,
        entry_time=request.entry_time,
    )


@router.get("/{person_id}/patterns")
async def get_patterns(
    person_id: str,
    min_confidence: float = 0.4,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Get learned patterns for a user.

    Returns cause-effect patterns learned from the user's journal entries.
    """
    patterns = await get_learned_patterns(
        person_id=person_id,
        min_confidence=min_confidence,
        limit=limit,
    )

    return {
        "person_id": person_id,
        "patterns": patterns,
        "count": len(patterns),
    }


# =============================================================================
# Graph Statistics
# =============================================================================

@router.get("/stats")
async def get_knowledge_graph_stats() -> Dict[str, Any]:
    """Get knowledge graph statistics."""
    return await get_graph_stats()


__all__ = ["router"]
