"""
Recommendation Context Builder
------------------------------
Builds a comprehensive context for making personalized recommendations.

Gathers:
- User's prakruti (constitution)
- Current vikriti (friction state)
- Personal patterns learned over time
- Recent behaviors and symptoms
- Seasonal/temporal context
- Historical effectiveness of recommendations
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.ayurveda.vikriti import (
    compute_current_vikriti,
    compute_baseline_drift,
    classify_friction_state,
)
from sakhi.apps.api.services.ayurveda.graph_reasoning import (
    get_current_season,
    get_current_time_window,
    get_seasonal_amplification,
)
from sakhi.apps.api.services.ayurveda.pattern_learning import get_learned_patterns
from sakhi.apps.api.services.ayurveda.causal_reasoning import (
    get_recent_behaviors,
    get_personal_patterns_for_effect,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================

class ConstitutionContext(BaseModel):
    """User's Ayurvedic constitution (Prakruti)."""
    type: str = Field(default="unknown", description="Constitution type")
    primary_dosha: Optional[str] = None
    secondary_dosha: Optional[str] = None
    dosha_percentages: Dict[str, float] = Field(default_factory=dict)


class CurrentStateContext(BaseModel):
    """User's current state (Vikriti)."""
    friction_state: str = Field(default="Balanced")
    friction_description: Optional[str] = None
    drift_percentage: float = 0.0
    drift_direction: Optional[str] = None
    primary_imbalance: Optional[str] = None


class TemporalContext(BaseModel):
    """Temporal and seasonal context."""
    season: str
    time_window: str
    seasonal_amplification: float = 1.0
    is_transition_period: bool = False


class PersonalPattern(BaseModel):
    """A learned personal pattern."""
    cause: str
    effect: str
    correlation_strength: float
    observation_count: int
    ayurvedic_explanation: Optional[str] = None


class RecentActivity(BaseModel):
    """Recent activity that may influence current state."""
    behavior_type: str
    behavior_name: str
    occurred_at: datetime
    dosha_effect: Optional[str] = None


class HistoricalEffectiveness(BaseModel):
    """Track what's worked for this user before."""
    effective_practices: List[str] = Field(default_factory=list)
    effective_foods: List[str] = Field(default_factory=list)
    ineffective_or_avoided: List[str] = Field(default_factory=list)


class RecommendationContext(BaseModel):
    """
    Complete context for making personalized recommendations.

    This is the central data structure that feeds into the recommendation generator.
    """
    person_id: str
    constitution: ConstitutionContext
    current_state: CurrentStateContext
    temporal: TemporalContext
    personal_patterns: List[PersonalPattern] = Field(default_factory=list)
    recent_activities: List[RecentActivity] = Field(default_factory=list)
    historical_effectiveness: HistoricalEffectiveness = Field(
        default_factory=HistoricalEffectiveness
    )

    # Computed fields
    urgency_level: str = Field(
        default="normal",
        description="How urgent is intervention: low, normal, high, critical"
    )
    personalization_confidence: float = Field(
        default=0.5,
        description="How confident we are in personalizing (based on data available)"
    )


# =============================================================================
# Context Building Functions
# =============================================================================

async def get_constitution_context(person_id: str) -> ConstitutionContext:
    """Get user's constitution (Prakruti) context."""
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
        return ConstitutionContext()

    os_data = personal_model.get("operating_system") or {}

    # Extract dosha percentages
    doshas = os_data.get("doshas", {})
    if isinstance(doshas, dict):
        sorted_doshas = sorted(
            doshas.items(),
            key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
            reverse=True,
        )
        primary = sorted_doshas[0][0] if sorted_doshas else None
        secondary = sorted_doshas[1][0] if len(sorted_doshas) > 1 else None
    else:
        primary = None
        secondary = None

    return ConstitutionContext(
        type=os_data.get("type", "unknown"),
        primary_dosha=primary,
        secondary_dosha=secondary,
        dosha_percentages=doshas if isinstance(doshas, dict) else {},
    )


async def get_current_state_context(
    person_id: str,
    operating_system: Optional[Dict[str, Any]] = None,
) -> CurrentStateContext:
    """Compute current state (Vikriti) context."""
    # Get operating system if not provided
    if operating_system is None:
        personal_model = await dbfetch(
            "SELECT operating_system FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        operating_system = (personal_model or {}).get("operating_system", {})

    # Compute current vikriti
    vikriti = await compute_current_vikriti(person_id)

    # Compute drift
    drift = compute_baseline_drift(operating_system, vikriti)

    # Classify friction
    friction = classify_friction_state(drift)

    return CurrentStateContext(
        friction_state=friction.get("state", "Balanced"),
        friction_description=friction.get("description"),
        drift_percentage=drift.get("drift_percentage", 0),
        drift_direction=drift.get("direction"),
        primary_imbalance=drift.get("primary_contributor"),
    )


async def get_temporal_context(dosha: Optional[str] = None) -> TemporalContext:
    """Get seasonal and temporal context."""
    season = get_current_season()
    time_window = get_current_time_window()

    amplification = 1.0
    if dosha:
        amplification = await get_seasonal_amplification(dosha)

    # Check if we're in a seasonal transition
    month = datetime.utcnow().month
    transition_months = {3, 6, 9, 12}  # Spring/Summer/Fall/Winter transitions
    is_transition = month in transition_months

    return TemporalContext(
        season=season,
        time_window=time_window,
        seasonal_amplification=amplification,
        is_transition_period=is_transition,
    )


async def get_personal_patterns_context(
    person_id: str,
    current_state: CurrentStateContext,
) -> List[PersonalPattern]:
    """Get relevant personal patterns for current state."""
    patterns = []

    # Get patterns that explain current friction state
    if current_state.primary_imbalance:
        # Map friction to symptom for pattern lookup
        friction_symptom_map = {
            "vata": "scattered",
            "pitta": "intense",
            "kapha": "stuck",
        }
        symptom = friction_symptom_map.get(current_state.primary_imbalance, "imbalanced")

        relevant_patterns = await get_personal_patterns_for_effect(
            person_id=person_id,
            effect_type="symptom",
            effect_value=symptom,
            min_confidence=0.3,
        )

        for p in relevant_patterns:
            patterns.append(PersonalPattern(
                cause=f"{p.get('cause_type', 'behavior')}:{p.get('cause_value', 'unknown')}",
                effect=f"symptom:{symptom}",
                correlation_strength=float(p.get("correlation_strength", 0.5)),
                observation_count=int(p.get("observation_count", 1)),
                ayurvedic_explanation=p.get("ayurvedic_explanation"),
            ))

    # Also get general strong patterns for this user
    all_patterns = await get_learned_patterns(person_id, min_confidence=0.5, limit=10)
    for p in all_patterns:
        pattern = PersonalPattern(
            cause=f"{p.get('cause_type', '')}:{p.get('cause_value', '')}",
            effect=f"{p.get('effect_type', '')}:{p.get('effect_value', '')}",
            correlation_strength=float(p.get("correlation_strength", 0.5)),
            observation_count=int(p.get("observation_count", 1)),
            ayurvedic_explanation=p.get("ayurvedic_explanation"),
        )
        if pattern not in patterns:
            patterns.append(pattern)

    return patterns[:15]  # Limit to top 15 patterns


async def get_recent_activities_context(person_id: str) -> List[RecentActivity]:
    """Get recent behaviors/activities."""
    behaviors = await get_recent_behaviors(person_id, hours_back=48)

    activities = []
    for b in behaviors:
        occurred_at = b.get("occurred_at")
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        elif occurred_at is None:
            occurred_at = datetime.utcnow()

        activities.append(RecentActivity(
            behavior_type=b.get("behavior_type", "unknown"),
            behavior_name=b.get("behavior_name", "unknown"),
            occurred_at=occurred_at,
            dosha_effect=b.get("dosha_effect"),
        ))

    return activities[:20]  # Limit to most recent 20


async def get_historical_effectiveness(person_id: str) -> HistoricalEffectiveness:
    """Get what's worked (or not) for this user historically."""
    # Query feedback on recommendations
    feedback = await dbfetch(
        """
        SELECT item_name, item_type, helpful, created_at
        FROM recommendation_feedback
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        """,
        person_id,
    )

    effective_practices = []
    effective_foods = []
    ineffective = []

    for f in feedback or []:
        item = f.get("item_name", "")
        item_type = f.get("item_type", "")
        helpful = f.get("helpful")

        if helpful is True:
            if item_type == "practice":
                effective_practices.append(item)
            elif item_type == "food":
                effective_foods.append(item)
        elif helpful is False:
            ineffective.append(item)

    return HistoricalEffectiveness(
        effective_practices=effective_practices[:10],
        effective_foods=effective_foods[:10],
        ineffective_or_avoided=ineffective[:10],
    )


def compute_urgency_level(current_state: CurrentStateContext) -> str:
    """Determine how urgent intervention is needed."""
    drift = current_state.drift_percentage

    if drift >= 40:
        return "critical"
    elif drift >= 25:
        return "high"
    elif drift >= 10:
        return "normal"
    else:
        return "low"


def compute_personalization_confidence(
    patterns: List[PersonalPattern],
    activities: List[RecentActivity],
    historical: HistoricalEffectiveness,
) -> float:
    """Compute how confident we can be in personalization."""
    # More data = more confidence
    pattern_score = min(1.0, len(patterns) / 10)  # Up to 10 patterns
    activity_score = min(1.0, len(activities) / 15)  # Up to 15 activities
    feedback_score = min(1.0, (
        len(historical.effective_practices) +
        len(historical.effective_foods)
    ) / 10)

    # Weighted average
    confidence = (pattern_score * 0.4 + activity_score * 0.3 + feedback_score * 0.3)

    # Minimum confidence of 0.3 (we always have Ayurvedic knowledge)
    return max(0.3, min(0.95, confidence))


# =============================================================================
# Main Context Builder
# =============================================================================

async def build_recommendation_context(person_id: str) -> RecommendationContext:
    """
    Build a complete recommendation context for a user.

    This is the main entry point for the context builder.
    Gathers all relevant data needed to make personalized recommendations.
    """
    # Get constitution
    constitution = await get_constitution_context(person_id)

    # Get current state
    current_state = await get_current_state_context(person_id)

    # Get temporal context
    temporal = await get_temporal_context(current_state.primary_imbalance)

    # Get personal patterns
    patterns = await get_personal_patterns_context(person_id, current_state)

    # Get recent activities
    activities = await get_recent_activities_context(person_id)

    # Get historical effectiveness
    historical = await get_historical_effectiveness(person_id)

    # Compute derived fields
    urgency = compute_urgency_level(current_state)
    confidence = compute_personalization_confidence(patterns, activities, historical)

    logger.info(
        "[ContextBuilder] person=%s friction=%s urgency=%s confidence=%.2f patterns=%d",
        person_id,
        current_state.friction_state,
        urgency,
        confidence,
        len(patterns),
    )

    return RecommendationContext(
        person_id=person_id,
        constitution=constitution,
        current_state=current_state,
        temporal=temporal,
        personal_patterns=patterns,
        recent_activities=activities,
        historical_effectiveness=historical,
        urgency_level=urgency,
        personalization_confidence=confidence,
    )


__all__ = [
    "build_recommendation_context",
    "RecommendationContext",
    "ConstitutionContext",
    "CurrentStateContext",
    "TemporalContext",
    "PersonalPattern",
    "RecentActivity",
    "HistoricalEffectiveness",
]
