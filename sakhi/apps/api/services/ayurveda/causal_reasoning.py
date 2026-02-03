"""
Causal Reasoning Service
------------------------
Answers "Why am I feeling X?" by tracing back through:
1. Ayurvedic knowledge graph (general causes)
2. Personal patterns (user-specific causes)
3. Recent behaviors (likely triggers)

This is the "why" engine that makes Sakhi's recommendations meaningful.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.ayurveda.graph_reasoning import (
    query_symptoms_for_dosha,
    get_current_season,
    get_seasonal_amplification,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class CausalFactor(BaseModel):
    """A factor that may have caused the current state."""
    factor_type: str = Field(description="Type: behavior, pattern, seasonal, constitutional")
    description: str = Field(description="Human-readable description")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    ayurvedic_link: Optional[str] = Field(default=None, description="Ayurvedic explanation")
    evidence: Optional[str] = Field(default=None, description="Evidence supporting this")
    related_dosha: Optional[str] = Field(default=None)


class CausalExplanation(BaseModel):
    """Full causal explanation for a symptom or state."""
    symptom: str
    dosha_context: Optional[str] = None
    primary_causes: List[CausalFactor] = Field(default_factory=list)
    contributing_factors: List[CausalFactor] = Field(default_factory=list)
    seasonal_influence: Optional[str] = None
    personal_pattern_match: bool = False
    explanation_text: str = Field(description="Natural language explanation")


class LastTimeEpisode(BaseModel):
    """A past episode similar to current situation."""
    episode_id: str
    occurred_at: datetime
    symptom: str
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    duration_hours: Optional[float] = None
    what_helped: List[str] = Field(default_factory=list)
    what_didnt_help: List[str] = Field(default_factory=list)
    resolution_summary: Optional[str] = None
    similarity_score: float = Field(default=0.5, ge=0.0, le=1.0)


class LastTimeLookup(BaseModel):
    """Result of looking up similar past episodes."""
    current_symptom: str
    found_episodes: List[LastTimeEpisode] = Field(default_factory=list)
    best_interventions: List[str] = Field(default_factory=list)
    average_resolution_time: Optional[str] = None
    summary: str = Field(description="Natural language summary")


# =============================================================================
# Symptom to Dosha Mapping
# =============================================================================

SYMPTOM_DOSHA_MAP = {
    # Vata symptoms (air/space - chaos, anxiety, scattered)
    "anxiety": "vata",
    "anxious": "vata",
    "scattered": "vata",
    "restless": "vata",
    "insomnia": "vata",
    "dry_skin": "vata",
    "constipation": "vata",
    "bloating": "vata",
    "worry": "vata",
    "overwhelmed": "vata",
    "racing_thoughts": "vata",
    "forgetful": "vata",
    "indecisive": "vata",
    "cold": "vata",
    "fatigue": "vata",  # Can also be kapha

    # Pitta symptoms (fire/water - intensity, irritation)
    "irritable": "pitta",
    "angry": "pitta",
    "frustrated": "pitta",
    "impatient": "pitta",
    "heartburn": "pitta",
    "inflammation": "pitta",
    "acne": "pitta",
    "overheated": "pitta",
    "competitive": "pitta",
    "critical": "pitta",
    "perfectionist": "pitta",
    "intense": "pitta",
    "burnout": "pitta",

    # Kapha symptoms (earth/water - stagnation, heaviness)
    "lethargic": "kapha",
    "heavy": "kapha",
    "sluggish": "kapha",
    "unmotivated": "kapha",
    "depressed": "kapha",
    "congestion": "kapha",
    "weight_gain": "kapha",
    "attachment": "kapha",
    "possessive": "kapha",
    "stuck": "kapha",
    "resistant": "kapha",
    "foggy": "kapha",
}


def map_symptom_to_dosha(symptom: str) -> Optional[str]:
    """Map a symptom/state to its likely dosha imbalance."""
    symptom_lower = symptom.lower().replace(" ", "_")
    return SYMPTOM_DOSHA_MAP.get(symptom_lower)


# =============================================================================
# Query Functions
# =============================================================================

async def get_personal_patterns_for_effect(
    person_id: str,
    effect_type: str,
    effect_value: str,
    min_confidence: float = 0.3,
) -> List[Dict[str, Any]]:
    """Get personal patterns that could explain an effect."""
    results = await dbfetch(
        """
        SELECT cause_type, cause_value, correlation_strength, confidence,
               observation_count, ayurvedic_explanation, related_dosha,
               last_observed_at
        FROM personal_patterns
        WHERE person_id = $1
          AND effect_type = $2
          AND effect_value = $3
          AND confidence >= $4
        ORDER BY correlation_strength DESC, observation_count DESC
        LIMIT 5
        """,
        person_id,
        effect_type,
        effect_value,
        min_confidence,
    )
    return list(results) if results else []


async def get_recent_behaviors(
    person_id: str,
    hours_back: int = 48,
) -> List[Dict[str, Any]]:
    """Get recent behaviors for correlation."""
    results = await dbfetch(
        """
        SELECT behavior_type, behavior_name, occurred_at, dosha_effect,
               effect_direction, intensity, source_text
        FROM behavior_log
        WHERE person_id = $1
          AND occurred_at > now() - ($2 || ' hours')::INTERVAL
        ORDER BY occurred_at DESC
        LIMIT 20
        """,
        person_id,
        str(hours_back),
    )
    return list(results) if results else []


async def get_ayurvedic_causes_for_symptom(
    symptom: str,
    dosha: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query Ayurvedic knowledge graph for causes of a symptom."""
    # First, try to find the symptom in the graph
    symptom_node = await dbfetch(
        """
        SELECT id, name, attrs FROM ay_nodes
        WHERE kind = 'symptom' AND name ILIKE $1
        """,
        f"%{symptom}%",
        one=True,
    )

    if not symptom_node:
        # Fall back to dosha-based lookup
        if dosha:
            symptoms = await query_symptoms_for_dosha(dosha)
            return [
                {
                    "source": "dosha_symptoms",
                    "dosha": dosha,
                    "related_symptoms": symptoms[:5],
                }
            ]
        return []

    # Find what AGGRAVATES this symptom (behaviors/foods that worsen it)
    causes = await dbfetch(
        """
        SELECT n.name, n.kind, n.attrs, e.weight
        FROM ay_nodes n
        JOIN ay_edges e ON n.id = e.src
        WHERE e.dst = $1
          AND e.rel IN ('AGGRAVATES', 'CAUSES', 'INDICATES')
        ORDER BY e.weight DESC
        LIMIT 10
        """,
        symptom_node["id"],
    )

    return list(causes) if causes else []


# =============================================================================
# Main Causal Reasoning Functions
# =============================================================================

async def explain_symptom(
    person_id: str,
    symptom: str,
    context: Optional[Dict[str, Any]] = None,
) -> CausalExplanation:
    """
    Main causal reasoning function.

    Answers "Why am I feeling X?" by combining:
    1. Personal patterns (what's caused this for YOU before)
    2. Recent behaviors (what you've done in past 48 hours)
    3. Ayurvedic knowledge (general causes)
    4. Seasonal influence

    Args:
        person_id: User ID
        symptom: What they're experiencing (e.g., "anxious", "tired", "scattered")
        context: Additional context (time of day, recent activities, etc.)

    Returns:
        CausalExplanation with ranked causes and natural language explanation
    """
    context = context or {}
    primary_causes: List[CausalFactor] = []
    contributing_factors: List[CausalFactor] = []

    # 1. Map symptom to dosha
    dosha = map_symptom_to_dosha(symptom)
    dosha_context = None

    if dosha:
        dosha_context = _get_dosha_explanation(dosha, symptom)

    # 2. Check personal patterns (highest priority - user-specific)
    personal_patterns = await get_personal_patterns_for_effect(
        person_id=person_id,
        effect_type="symptom",
        effect_value=symptom.lower().replace(" ", "_"),
    )

    pattern_match = False
    for pattern in personal_patterns:
        pattern_match = True
        cause = CausalFactor(
            factor_type="pattern",
            description=f"Your pattern: {_format_behavior(pattern['cause_value'])} tends to cause this",
            confidence=float(pattern.get("confidence", 0.5)),
            ayurvedic_link=pattern.get("ayurvedic_explanation"),
            evidence=f"Observed {pattern.get('observation_count', 1)} times",
            related_dosha=pattern.get("related_dosha"),
        )
        if pattern.get("correlation_strength", 0) > 0.6:
            primary_causes.append(cause)
        else:
            contributing_factors.append(cause)

    # 3. Check recent behaviors
    recent_behaviors = await get_recent_behaviors(person_id, hours_back=48)

    for behavior in recent_behaviors:
        # Check if this behavior could cause the symptom
        behavior_dosha = behavior.get("dosha_effect")
        if behavior_dosha == dosha and behavior.get("effect_direction") == "aggravates":
            cause = CausalFactor(
                factor_type="behavior",
                description=f"Recent: {_format_behavior(behavior['behavior_name'])}",
                confidence=0.6,
                ayurvedic_link=f"This tends to increase {dosha} energy",
                evidence=f"Occurred {_format_time_ago(behavior.get('occurred_at'))}",
                related_dosha=behavior_dosha,
            )
            contributing_factors.append(cause)

    # 4. Check seasonal influence
    season = get_current_season()
    seasonal_influence = None

    if dosha:
        amplification = await get_seasonal_amplification(dosha)
        if amplification > 1.1:
            seasonal_influence = f"{season.title()} naturally increases {dosha} energy"
            contributing_factors.append(CausalFactor(
                factor_type="seasonal",
                description=seasonal_influence,
                confidence=0.7,
                ayurvedic_link=f"Seasonal {dosha} accumulation",
                related_dosha=dosha,
            ))

    # 5. Get general Ayurvedic causes if we don't have personal data
    if not primary_causes and not contributing_factors:
        ayurvedic_causes = await get_ayurvedic_causes_for_symptom(symptom, dosha)
        for cause_data in ayurvedic_causes[:3]:
            if isinstance(cause_data, dict) and cause_data.get("name"):
                contributing_factors.append(CausalFactor(
                    factor_type="ayurvedic",
                    description=f"Common cause: {_format_behavior(cause_data['name'])}",
                    confidence=float(cause_data.get("weight", 0.5)),
                    ayurvedic_link="From Ayurvedic knowledge",
                    related_dosha=dosha,
                ))

    # 6. Generate natural language explanation
    explanation_text = await _generate_explanation(
        symptom=symptom,
        dosha=dosha,
        dosha_context=dosha_context,
        primary_causes=primary_causes,
        contributing_factors=contributing_factors,
        seasonal_influence=seasonal_influence,
        person_id=person_id,
    )

    return CausalExplanation(
        symptom=symptom,
        dosha_context=dosha_context,
        primary_causes=primary_causes,
        contributing_factors=contributing_factors,
        seasonal_influence=seasonal_influence,
        personal_pattern_match=pattern_match,
        explanation_text=explanation_text,
    )


async def explain_friction_state(
    person_id: str,
    friction_state: str,
    recent_signals: Optional[List[Dict[str, Any]]] = None,
) -> CausalExplanation:
    """
    Explain why the user is in a particular friction state.

    Args:
        person_id: User ID
        friction_state: Current friction state (e.g., "Chaos Friction")
        recent_signals: Optional recent signals from memory/journal

    Returns:
        CausalExplanation
    """
    # Map friction state to symptom/dosha
    friction_map = {
        "chaos_friction": ("scattered", "vata"),
        "chaos friction": ("scattered", "vata"),
        "intensity_friction": ("intense", "pitta"),
        "intensity friction": ("intense", "pitta"),
        "stagnation_friction": ("stuck", "kapha"),
        "stagnation friction": ("stuck", "kapha"),
    }

    symptom, dosha = friction_map.get(friction_state.lower(), ("imbalanced", None))

    return await explain_symptom(
        person_id=person_id,
        symptom=symptom,
        context={"friction_state": friction_state, "recent_signals": recent_signals},
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _get_dosha_explanation(dosha: str, symptom: str) -> str:
    """Get Ayurvedic explanation for symptom based on dosha."""
    explanations = {
        "vata": f"{symptom.title()} is a classic sign of elevated Vata (air/space). "
                "When Vata increases, the mind becomes restless and scattered, "
                "like wind disturbing a still lake.",
        "pitta": f"{symptom.title()} indicates elevated Pitta (fire/water). "
                 "When Pitta increases, heat builds up causing irritation and intensity, "
                 "like a fire that needs cooling.",
        "kapha": f"{symptom.title()} suggests elevated Kapha (earth/water). "
                 "When Kapha increases, heaviness and stagnation set in, "
                 "like water becoming stagnant.",
    }
    return explanations.get(dosha, f"{symptom.title()} may indicate a dosha imbalance.")


def _format_behavior(behavior: str) -> str:
    """Format behavior string for display."""
    return behavior.replace("_", " ").title()


def _format_time_ago(dt: Optional[datetime]) -> str:
    """Format datetime as relative time."""
    if not dt:
        return "recently"

    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = now - dt

    if delta.days > 0:
        return f"{delta.days} days ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600} hours ago"
    else:
        return f"{delta.seconds // 60} minutes ago"


async def _generate_explanation(
    symptom: str,
    dosha: Optional[str],
    dosha_context: Optional[str],
    primary_causes: List[CausalFactor],
    contributing_factors: List[CausalFactor],
    seasonal_influence: Optional[str],
    person_id: str,
) -> str:
    """Generate natural language explanation combining all factors."""

    # Build explanation without LLM for speed and consistency
    parts = []

    # Start with dosha context if available
    if dosha_context:
        parts.append(dosha_context)

    # Add primary causes
    if primary_causes:
        parts.append("\n\nBased on your patterns:")
        for cause in primary_causes:
            parts.append(f"- {cause.description}")
            if cause.evidence:
                parts.append(f"  ({cause.evidence})")

    # Add contributing factors
    if contributing_factors:
        parts.append("\n\nContributing factors:")
        for factor in contributing_factors[:3]:
            parts.append(f"- {factor.description}")

    # Add seasonal note
    if seasonal_influence:
        parts.append(f"\n\nSeasonal note: {seasonal_influence}")

    # If we have no data, provide general guidance
    if not parts:
        parts.append(
            f"I notice you're experiencing {symptom}. While I'm still learning your patterns, "
            f"common causes include irregular routines, diet changes, or seasonal transitions. "
            f"As I learn more about you, I'll be able to give more personalized insights."
        )

    return " ".join(parts) if len(parts) == 1 else "\n".join(parts)


# =============================================================================
# Query Builder for Complex Causal Chains
# =============================================================================

# =============================================================================
# "Last Time" Lookup - Find Similar Past Episodes
# =============================================================================

async def find_similar_episodes(
    person_id: str,
    symptom: str,
    limit: int = 5,
) -> List[LastTimeEpisode]:
    """
    Find past episodes where user experienced similar symptoms.

    Searches:
    1. Symptom/behavior log for matching symptoms
    2. Episodic memory for related narratives
    3. Intervention outcomes to see what helped

    Args:
        person_id: User ID
        symptom: Current symptom to find similar episodes for
        limit: Max episodes to return

    Returns:
        List of past episodes with interventions and outcomes
    """
    episodes = []

    # 1. Check symptom log for direct matches
    symptom_key = symptom.lower().replace(" ", "_")
    dosha = map_symptom_to_dosha(symptom)

    symptom_rows = await dbfetch(
        """
        SELECT id, symptom_type, severity, occurred_at, resolution_time,
               interventions_tried, what_helped, what_didnt_help,
               resolution_summary
        FROM symptom_log
        WHERE person_id = $1
          AND (symptom_type = $2 OR symptom_type ILIKE $3)
        ORDER BY occurred_at DESC
        LIMIT $4
        """,
        person_id,
        symptom_key,
        f"%{symptom}%",
        limit,
    )

    for row in symptom_rows or []:
        # Calculate duration if we have resolution time
        duration = None
        if row.get("resolution_time") and row.get("occurred_at"):
            delta = row["resolution_time"] - row["occurred_at"]
            duration = delta.total_seconds() / 3600  # hours

        what_helped = row.get("what_helped") or []
        if isinstance(what_helped, str):
            what_helped = [what_helped]

        what_didnt = row.get("what_didnt_help") or []
        if isinstance(what_didnt, str):
            what_didnt = [what_didnt]

        episodes.append(LastTimeEpisode(
            episode_id=str(row.get("id", "")),
            occurred_at=row.get("occurred_at", datetime.now()),
            symptom=row.get("symptom_type", symptom),
            severity=float(row.get("severity", 0.5)),
            duration_hours=duration,
            what_helped=what_helped,
            what_didnt_help=what_didnt,
            resolution_summary=row.get("resolution_summary"),
            similarity_score=0.9,  # Direct symptom match
        ))

    # 2. Search episodic memory for related experiences
    if len(episodes) < limit:
        episodic_rows = await dbfetch(
            """
            SELECT id, summary, themes, emotion, created_at, metadata
            FROM memory_episodic
            WHERE user_id = $1
              AND (
                summary ILIKE $2
                OR themes::text ILIKE $2
                OR $3 = ANY(themes)
              )
            ORDER BY created_at DESC
            LIMIT $4
            """,
            person_id,
            f"%{symptom}%",
            symptom_key,
            limit - len(episodes),
        )

        for row in episodic_rows or []:
            metadata = row.get("metadata") or {}

            episodes.append(LastTimeEpisode(
                episode_id=str(row.get("id", "")),
                occurred_at=row.get("created_at", datetime.now()),
                symptom=symptom,
                severity=0.5,
                duration_hours=metadata.get("duration_hours"),
                what_helped=metadata.get("interventions", []),
                what_didnt_help=[],
                resolution_summary=row.get("summary"),
                similarity_score=0.6,  # Semantic match
            ))

    # 3. Check intervention outcomes for dosha-related patterns
    if dosha and len(episodes) < limit:
        intervention_rows = await dbfetch(
            """
            SELECT intervention_type, intervention_name, occurred_at,
                   was_effective, effectiveness_score, symptom_addressed,
                   notes
            FROM intervention_outcomes
            WHERE person_id = $1
              AND (
                related_dosha = $2
                OR symptom_addressed = $3
                OR symptom_addressed ILIKE $4
              )
            ORDER BY occurred_at DESC
            LIMIT $5
            """,
            person_id,
            dosha,
            symptom_key,
            f"%{symptom}%",
            limit - len(episodes),
        )

        # Group interventions by date to create pseudo-episodes
        date_groups: Dict[str, Dict[str, Any]] = {}
        for row in intervention_rows or []:
            date_key = row.get("occurred_at", datetime.now()).date().isoformat()
            if date_key not in date_groups:
                date_groups[date_key] = {
                    "occurred_at": row.get("occurred_at"),
                    "what_helped": [],
                    "what_didnt_help": [],
                }

            intervention = _format_behavior(row.get("intervention_name", ""))
            if row.get("was_effective"):
                date_groups[date_key]["what_helped"].append(intervention)
            else:
                date_groups[date_key]["what_didnt_help"].append(intervention)

        for date_key, group in date_groups.items():
            episodes.append(LastTimeEpisode(
                episode_id=f"intervention-{date_key}",
                occurred_at=group["occurred_at"],
                symptom=symptom,
                severity=0.5,
                what_helped=group["what_helped"],
                what_didnt_help=group["what_didnt_help"],
                similarity_score=0.7,
            ))

    return episodes[:limit]


async def lookup_last_time(
    person_id: str,
    symptom: str,
    limit: int = 3,
) -> LastTimeLookup:
    """
    "Last time I felt this way..." lookup.

    Finds similar past episodes and what helped.

    Args:
        person_id: User ID
        symptom: Current symptom (e.g., "anxious", "scattered", "tired")
        limit: Max episodes to return

    Returns:
        LastTimeLookup with episodes, best interventions, and summary

    Example:
        >>> result = await lookup_last_time("user-123", "anxious")
        >>> result.summary
        "Last time you felt anxious (3 days ago), walks and breathing helped in about 2 hours."
    """
    # Find similar episodes
    episodes = await find_similar_episodes(person_id, symptom, limit=limit)

    # Aggregate best interventions
    intervention_counts: Dict[str, int] = {}
    total_duration = 0.0
    duration_count = 0

    for ep in episodes:
        for intervention in ep.what_helped:
            intervention_counts[intervention] = intervention_counts.get(intervention, 0) + 1

        if ep.duration_hours:
            total_duration += ep.duration_hours
            duration_count += 1

    # Sort by frequency
    best_interventions = sorted(
        intervention_counts.keys(),
        key=lambda x: intervention_counts[x],
        reverse=True
    )[:5]

    # Calculate average resolution time
    avg_time = None
    avg_time_str = None
    if duration_count > 0:
        avg_time = total_duration / duration_count
        if avg_time < 1:
            avg_time_str = f"{int(avg_time * 60)} minutes"
        elif avg_time < 24:
            avg_time_str = f"{avg_time:.1f} hours"
        else:
            avg_time_str = f"{avg_time / 24:.1f} days"

    # Generate summary
    summary = _generate_last_time_summary(
        symptom=symptom,
        episodes=episodes,
        best_interventions=best_interventions,
        avg_time_str=avg_time_str,
    )

    return LastTimeLookup(
        current_symptom=symptom,
        found_episodes=episodes,
        best_interventions=best_interventions,
        average_resolution_time=avg_time_str,
        summary=summary,
    )


def _generate_last_time_summary(
    symptom: str,
    episodes: List[LastTimeEpisode],
    best_interventions: List[str],
    avg_time_str: Optional[str],
) -> str:
    """Generate natural language summary of past episodes."""
    if not episodes:
        return (
            f"I don't have records of you experiencing {symptom} before. "
            f"As I learn more about you, I'll be able to tell you what's helped in the past."
        )

    parts = []

    # Most recent episode
    latest = episodes[0]
    time_ago = _format_time_ago(latest.occurred_at)

    parts.append(f"Last time you felt {symptom} was {time_ago}.")

    # What helped
    if best_interventions:
        if len(best_interventions) == 1:
            parts.append(f"{best_interventions[0]} helped.")
        elif len(best_interventions) == 2:
            parts.append(f"{best_interventions[0]} and {best_interventions[1]} helped.")
        else:
            interventions_text = ", ".join(best_interventions[:2]) + f", and {best_interventions[2]}"
            parts.append(f"What's helped before: {interventions_text}.")

    # Resolution time
    if avg_time_str:
        parts.append(f"It typically resolved in about {avg_time_str}.")

    # Number of similar episodes
    if len(episodes) > 1:
        parts.append(f"I found {len(episodes)} similar episodes in your history.")

    return " ".join(parts)


async def trace_causal_chain(
    person_id: str,
    effect: str,
    depth: int = 2,
) -> List[List[Dict[str, Any]]]:
    """
    Trace multi-hop causal chains backward from an effect.

    Example: anxiety -> (pattern) late_dinner -> (pattern) work_stress

    This enables deeper "why" questions:
    - "Why am I anxious?" -> "Late dinners"
    - "Why am I eating late?" -> "Work stress"

    Args:
        person_id: User ID
        effect: The effect to trace back from
        depth: How many hops to trace

    Returns:
        List of causal chains, each chain is a list of cause-effect hops
    """
    chains = []
    current_effects = [(effect, "symptom", [])]  # (value, type, chain_so_far)

    for _ in range(depth):
        next_effects = []

        for effect_value, effect_type, chain in current_effects:
            # Find patterns where this effect is the result
            patterns = await get_personal_patterns_for_effect(
                person_id=person_id,
                effect_type=effect_type,
                effect_value=effect_value.lower().replace(" ", "_"),
                min_confidence=0.3,
            )

            for pattern in patterns:
                new_chain = chain + [{
                    "cause_type": pattern["cause_type"],
                    "cause_value": pattern["cause_value"],
                    "effect_type": effect_type,
                    "effect_value": effect_value,
                    "confidence": pattern.get("confidence", 0.5),
                }]

                # Add to results if chain is complete
                if len(new_chain) >= 1:
                    chains.append(new_chain)

                # Add cause as next effect to trace
                next_effects.append((
                    pattern["cause_value"],
                    pattern["cause_type"],
                    new_chain,
                ))

        current_effects = next_effects

    return chains


__all__ = [
    "explain_symptom",
    "explain_friction_state",
    "trace_causal_chain",
    "map_symptom_to_dosha",
    "find_similar_episodes",
    "lookup_last_time",
    "CausalExplanation",
    "CausalFactor",
    "LastTimeEpisode",
    "LastTimeLookup",
]
