"""
Personalized Recommendation Generator
-------------------------------------
Generates truly personalized recommendations by:
1. Using Ayurvedic knowledge graph as the base
2. Boosting/filtering based on personal patterns
3. Incorporating historical effectiveness
4. Generating natural language explanations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sakhi.apps.api.services.recommendations.context_builder import (
    RecommendationContext,
    PersonalPattern,
)
from sakhi.apps.api.services.ayurveda.graph_reasoning import (
    query_foods_for_dosha,
    query_practices_for_dosha,
    query_symptoms_for_dosha,
)
from sakhi.apps.api.core.db import q as dbfetch

logger = logging.getLogger(__name__)


# =============================================================================
# Herb Query Functions
# =============================================================================

async def query_herbs_for_dosha(dosha: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Query herbs that pacify a specific dosha."""
    import json
    results = await dbfetch(
        """
        SELECT n.name, n.name_sanskrit, n.display_name, n.attrs, n.citations,
               n.confidence, e.weight
        FROM ay_nodes n
        JOIN ay_edges e ON n.id = e.src
        JOIN ay_nodes d ON e.dst = d.id
        WHERE n.kind = 'herb'
          AND d.kind = 'dosha'
          AND d.name = $1
          AND e.rel = 'PACIFIES'
        ORDER BY e.weight DESC
        LIMIT $2
        """,
        dosha,
        limit,
    )

    herbs = []
    for r in results or []:
        attrs = r.get("attrs") or {}
        if isinstance(attrs, str):
            attrs = json.loads(attrs)

        citations = r.get("citations") or []
        if isinstance(citations, str):
            citations = json.loads(citations)

        herbs.append({
            "name": r["name"],
            "name_sanskrit": r.get("name_sanskrit"),
            "display_name": r.get("display_name") or r["name"].replace("_", " ").title(),
            "weight": float(r.get("weight") or 0.8),
            "rasa": attrs.get("rasa"),
            "virya": attrs.get("virya"),
            "therapeutic_uses": attrs.get("therapeutic_uses", []),
            "citations": citations[:1] if citations else [],
        })
    return herbs


async def check_contraindications(item_name: str) -> List[str]:
    """Check for contraindications for an item."""
    import json
    results = await dbfetch(
        """
        SELECT d.name, d.display_name, e.context
        FROM ay_nodes n
        JOIN ay_edges e ON n.id = e.src
        JOIN ay_nodes d ON e.dst = d.id
        WHERE n.name ILIKE $1
          AND e.rel = 'CONTRAINDICATED_WITH'
        LIMIT 5
        """,
        f"%{item_name}%",
    )

    contraindications = []
    for r in results or []:
        context = r.get("context") or {}
        if isinstance(context, str):
            context = json.loads(context)
        reason = context.get("reason", "")
        target = r.get("display_name") or r.get("name", "")
        if reason:
            contraindications.append(f"Avoid with {target}: {reason}")
        else:
            contraindications.append(f"Avoid combining with {target}")

    return contraindications


def _format_citation(citations: List[Dict[str, Any]]) -> Optional[str]:
    """Format citation reference from knowledge graph."""
    if not citations:
        return None
    cite = citations[0] if citations else None
    if not cite or not isinstance(cite, dict):
        return None
    source = cite.get("source", "").replace("_", " ").title()
    chapter = cite.get("chapter", "")
    if source and chapter:
        return f"{source}, {chapter}"
    return source if source else None


# =============================================================================
# Pydantic Models
# =============================================================================

class PersonalizedRecommendation(BaseModel):
    """A single personalized recommendation."""
    name: str
    name_sanskrit: Optional[str] = None
    category: str = Field(description="food, practice, herb, immediate_action")
    score: float = Field(ge=0.0, le=1.0)

    # Personalization
    is_personally_effective: bool = False
    personal_relevance: Optional[str] = None

    # Ayurvedic basis
    ayurvedic_reason: str
    ayurvedic_source: Optional[str] = None  # Citation from classical text
    dosha_effect: Optional[str] = None

    # Metadata
    duration_minutes: Optional[int] = None
    time_of_day: Optional[str] = None
    season_appropriate: bool = True
    contraindications: List[str] = Field(default_factory=list)


class RecommendationSet(BaseModel):
    """Complete set of personalized recommendations."""
    person_id: str
    friction_state: str
    urgency_level: str
    personalization_confidence: float

    # Recommendations by category
    immediate_actions: List[PersonalizedRecommendation] = Field(default_factory=list)
    foods: List[PersonalizedRecommendation] = Field(default_factory=list)
    practices: List[PersonalizedRecommendation] = Field(default_factory=list)
    herbs: List[PersonalizedRecommendation] = Field(default_factory=list)

    # Explanations
    why_this_state: str
    personal_insight: Optional[str] = None

    # Warnings
    watch_for: List[str] = Field(default_factory=list)


# =============================================================================
# Scoring and Ranking
# =============================================================================

def score_recommendation(
    item: Dict[str, Any],
    context: RecommendationContext,
    item_type: str,
) -> float:
    """
    Score a recommendation based on personal and contextual factors.

    Factors:
    - Base Ayurvedic weight
    - Personal effectiveness (from history)
    - Pattern relevance
    - Temporal appropriateness
    - Seasonal match
    """
    base_score = float(item.get("weight", 0.7))

    # Personal effectiveness boost
    effectiveness_boost = 0.0
    item_name = item.get("name", "")

    if item_type == "practice":
        if item_name in context.historical_effectiveness.effective_practices:
            effectiveness_boost = 0.2
    elif item_type == "food":
        if item_name in context.historical_effectiveness.effective_foods:
            effectiveness_boost = 0.2

    # Penalty for historically ineffective
    if item_name in context.historical_effectiveness.ineffective_or_avoided:
        effectiveness_boost = -0.3

    # Pattern relevance
    pattern_boost = 0.0
    for pattern in context.personal_patterns:
        # If this item counters a known problematic behavior
        if pattern.correlation_strength > 0.6:
            pattern_boost += 0.05

    # Temporal appropriateness
    time_boost = 0.0
    item_time = item.get("time", "any")
    current_time = context.temporal.time_window
    if item_time == "any" or item_time == current_time:
        time_boost = 0.1

    # Seasonal match
    season_boost = 0.0
    item_season = item.get("season", "all")
    current_season = context.temporal.season
    if item_season == "all" or item_season == current_season:
        season_boost = 0.1
    elif item_season != current_season:
        season_boost = -0.05

    # Combine
    final_score = (
        base_score +
        effectiveness_boost +
        pattern_boost +
        time_boost +
        season_boost
    )

    # Urgency amplification
    if context.urgency_level == "critical":
        final_score *= 1.2
    elif context.urgency_level == "high":
        final_score *= 1.1

    return max(0.1, min(0.99, final_score))


def get_personal_relevance(
    item_name: str,
    context: RecommendationContext,
) -> Optional[str]:
    """Generate personal relevance explanation if applicable."""
    # Check if historically effective
    if item_name in context.historical_effectiveness.effective_practices:
        return "This has worked well for you before"
    if item_name in context.historical_effectiveness.effective_foods:
        return "You've found this helpful in the past"

    # Check pattern connections
    for pattern in context.personal_patterns:
        cause_parts = pattern.cause.split(":")
        if len(cause_parts) > 1:
            cause_value = cause_parts[1]
            # Check if this recommendation counters a known cause
            if _is_counter_recommendation(item_name, cause_value):
                return f"This may help counter your tendency toward {cause_value.replace('_', ' ')}"

    return None


def _is_counter_recommendation(recommendation: str, cause: str) -> bool:
    """Check if a recommendation counters a known problematic cause."""
    counter_map = {
        "late_dinner": ["early_dinner", "light_evening_meal", "digestive_tea"],
        "skipped_exercise": ["gentle_walk", "stretching", "yoga"],
        "irregular_schedule": ["morning_routine", "consistent_meals"],
        "caffeine": ["herbal_tea", "warm_water", "chai"],
        "overwork": ["break", "meditation", "walk"],
    }

    counters = counter_map.get(cause, [])
    return any(c in recommendation.lower() for c in counters)


# =============================================================================
# Explanation Generation
# =============================================================================

def generate_state_explanation(context: RecommendationContext) -> str:
    """Generate explanation for current state."""
    state = context.current_state.friction_state
    drift = context.current_state.drift_percentage
    dosha = context.current_state.primary_imbalance

    if state == "Balanced":
        return "You're in a balanced state. These recommendations help maintain your equilibrium."

    state_explanations = {
        "Chaos Friction": (
            "You're experiencing elevated Vata energy, which manifests as scattered thoughts, "
            "anxiety, or restlessness. This is common during busy or transitional periods."
        ),
        "Intensity Friction": (
            "You're experiencing elevated Pitta energy, showing up as intensity, irritation, "
            "or drive. While productive, this can lead to burnout if unchecked."
        ),
        "Stagnation Friction": (
            "You're experiencing elevated Kapha energy, manifesting as heaviness, resistance to change, "
            "or low motivation. This is common during winter or periods of routine."
        ),
    }

    base = state_explanations.get(state, f"You're experiencing {state}.")

    # Add drift context
    if drift > 30:
        base += f" Your drift from baseline is significant ({drift:.0f}%), so gentle intervention is recommended."
    elif drift > 15:
        base += f" There's a moderate shift from your baseline ({drift:.0f}%)."

    # Add seasonal context
    if context.temporal.seasonal_amplification > 1.1:
        base += f" {context.temporal.season.title()} naturally amplifies {dosha}, making this a good time to be mindful."

    return base


def generate_personal_insight(context: RecommendationContext) -> Optional[str]:
    """Generate a personal insight based on patterns."""
    if not context.personal_patterns:
        return None

    # Find the strongest pattern
    strongest = max(
        context.personal_patterns,
        key=lambda p: p.correlation_strength,
        default=None,
    )

    if not strongest or strongest.correlation_strength < 0.5:
        return None

    cause = strongest.cause.split(":")[-1].replace("_", " ")
    effect = strongest.effect.split(":")[-1].replace("_", " ")

    if strongest.observation_count >= 5:
        return (
            f"I've noticed that {cause} tends to lead to {effect} for you "
            f"(seen this {strongest.observation_count} times). "
            f"Being mindful of this pattern can help."
        )
    elif strongest.observation_count >= 2:
        return (
            f"There may be a connection between {cause} and {effect} - "
            f"something to be aware of."
        )

    return None


# =============================================================================
# Main Generator
# =============================================================================

async def generate_personalized_recommendations(
    context: RecommendationContext,
    max_foods: int = 5,
    max_practices: int = 5,
    max_immediate: int = 3,
) -> RecommendationSet:
    """
    Generate personalized recommendations using full context.

    This is the main entry point for recommendation generation.
    """
    # Determine target dosha
    target_dosha = context.current_state.primary_imbalance or "vata"

    # Get base recommendations from knowledge graph (now includes citations)
    foods_raw = await query_foods_for_dosha(target_dosha, "PACIFIES", limit=30)
    practices_raw = await query_practices_for_dosha(target_dosha, limit=20)
    symptoms_raw = await query_symptoms_for_dosha(target_dosha, limit=10)
    herbs_raw = await query_herbs_for_dosha(target_dosha, limit=10)

    # Score and rank foods
    scored_foods = []
    for food in foods_raw:
        score = score_recommendation(food, context, "food")
        personal_relevance = get_personal_relevance(food.get("name", ""), context)

        scored_foods.append(PersonalizedRecommendation(
            name=food.get("display_name") or food.get("name", "").replace("_", " ").title(),
            name_sanskrit=food.get("name_sanskrit"),
            category="food",
            score=score,
            is_personally_effective=food.get("name", "") in context.historical_effectiveness.effective_foods,
            personal_relevance=personal_relevance,
            ayurvedic_reason=_format_food_reason(food),
            ayurvedic_source=_format_citation(food.get("citations", [])),
            dosha_effect=f"Pacifies {target_dosha}",
            season_appropriate=food.get("season", "all") in ("all", context.temporal.season),
        ))

    scored_foods.sort(key=lambda x: x.score, reverse=True)

    # Score and rank practices
    scored_practices = []
    for practice in practices_raw:
        score = score_recommendation(practice, context, "practice")
        personal_relevance = get_personal_relevance(practice.get("name", ""), context)

        scored_practices.append(PersonalizedRecommendation(
            name=practice.get("display_name") or practice.get("name", "").replace("_", " ").title(),
            name_sanskrit=practice.get("name_sanskrit"),
            category="practice",
            score=score,
            is_personally_effective=practice.get("name", "") in context.historical_effectiveness.effective_practices,
            personal_relevance=personal_relevance,
            ayurvedic_reason=_format_practice_reason(practice),
            ayurvedic_source=_format_citation(practice.get("citations", [])),
            dosha_effect=f"Pacifies {target_dosha}",
            duration_minutes=practice.get("duration_min"),
            time_of_day=practice.get("time"),
        ))

    scored_practices.sort(key=lambda x: x.score, reverse=True)

    # Score and rank herbs (new!)
    scored_herbs = []
    for herb in herbs_raw:
        score = score_recommendation(herb, context, "herb")
        personal_relevance = get_personal_relevance(herb.get("name", ""), context)

        scored_herbs.append(PersonalizedRecommendation(
            name=herb.get("display_name") or herb.get("name", "").replace("_", " ").title(),
            name_sanskrit=herb.get("name_sanskrit"),
            category="herb",
            score=score,
            is_personally_effective=False,  # Herbs tracked separately
            personal_relevance=personal_relevance,
            ayurvedic_reason=_format_herb_reason(herb),
            ayurvedic_source=_format_citation(herb.get("citations", [])),
            dosha_effect=f"Pacifies {target_dosha}",
        ))

    scored_herbs.sort(key=lambda x: x.score, reverse=True)

    # Build immediate actions (quick wins from practices)
    immediate_actions = [
        p for p in scored_practices
        if (p.duration_minutes or 15) <= 10
    ][:max_immediate]

    # If not enough immediate actions, add default breathing
    if len(immediate_actions) < 2:
        immediate_actions.append(PersonalizedRecommendation(
            name="5 min deep breathing",
            category="immediate_action",
            score=0.8,
            ayurvedic_reason=f"Calms the nervous system and balances {target_dosha}",
            dosha_effect=f"Pacifies {target_dosha}",
            duration_minutes=5,
        ))

    # Generate explanations
    why_this_state = generate_state_explanation(context)
    personal_insight = generate_personal_insight(context)

    # Symptoms to watch
    watch_for = [s.get("name", "").replace("_", " ").title() for s in symptoms_raw[:5]]

    logger.info(
        "[RecommendationGenerator] person=%s foods=%d practices=%d herbs=%d immediate=%d",
        context.person_id,
        len(scored_foods[:max_foods]),
        len(scored_practices[:max_practices]),
        len(scored_herbs[:3]),
        len(immediate_actions),
    )

    return RecommendationSet(
        person_id=context.person_id,
        friction_state=context.current_state.friction_state,
        urgency_level=context.urgency_level,
        personalization_confidence=context.personalization_confidence,
        immediate_actions=immediate_actions,
        foods=scored_foods[:max_foods],
        practices=scored_practices[:max_practices],
        herbs=scored_herbs[:3],  # Top 3 herbs
        why_this_state=why_this_state,
        personal_insight=personal_insight,
        watch_for=watch_for,
    )


def _format_food_reason(food: Dict[str, Any]) -> str:
    """Format Ayurvedic reason for food recommendation."""
    rasa = food.get("rasa", "balanced")
    virya = food.get("virya", "neutral")
    return f"{rasa.title()} taste with {virya} energy"


def _format_practice_reason(practice: Dict[str, Any]) -> str:
    """Format Ayurvedic reason for practice recommendation."""
    practice_type = practice.get("type", "practice")
    intensity = practice.get("intensity", "gentle")
    duration = practice.get("duration_min", 10)
    return f"{intensity.title()} {practice_type}, {duration} minutes"


def _format_herb_reason(herb: Dict[str, Any]) -> str:
    """Format Ayurvedic reason for herb recommendation."""
    rasa = herb.get("rasa", "balanced")
    virya = herb.get("virya", "neutral")
    uses = herb.get("therapeutic_uses", [])

    reason = f"{rasa.title()} taste with {virya} energy"
    if uses:
        reason += f". {uses[0]}" if uses[0] else ""

    return reason


__all__ = [
    "generate_personalized_recommendations",
    "PersonalizedRecommendation",
    "RecommendationSet",
]
