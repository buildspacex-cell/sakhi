"""
A.7.3 Outcome Collector
-----------------------
Track intervention effectiveness to learn what actually helps.

Flow:
1. User reports symptom ("I'm feeling anxious")
2. Sakhi suggests intervention ("Try a short walk")
3. Later, user reports resolution or improvement
4. This module captures the outcome

This data feeds into causal_reasoning for "last time, X helped" responses.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as execute

logger = logging.getLogger(__name__)


class InterventionOutcome(BaseModel):
    """Record of an intervention's effectiveness."""
    intervention_type: str = Field(description="Type: activity, food, rest, social, mindfulness")
    intervention_name: str = Field(description="Specific action: walk, meditation, warm_meal")
    was_effective: bool
    effectiveness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    symptom_addressed: Optional[str] = None
    related_dosha: Optional[str] = None
    notes: Optional[str] = None


async def log_intervention_outcome(
    person_id: str,
    intervention_type: str,
    intervention_name: str,
    was_effective: bool,
    effectiveness_score: float = 0.5,
    symptom_addressed: Optional[str] = None,
    related_dosha: Optional[str] = None,
    notes: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> Optional[str]:
    """
    Log the outcome of an intervention.

    Args:
        person_id: User ID
        intervention_type: Type (activity, food, rest, social, mindfulness)
        intervention_name: Specific action (walk, meditation, warm_meal)
        was_effective: Did it help?
        effectiveness_score: 0.0-1.0 how much it helped
        symptom_addressed: What symptom this was for
        related_dosha: Which dosha context
        notes: Any additional context
        occurred_at: When the intervention happened

    Returns:
        Outcome ID or None
    """
    occurred_at = occurred_at or datetime.utcnow()

    try:
        result = await dbfetch(
            """
            INSERT INTO intervention_outcomes (
                person_id, intervention_type, intervention_name,
                was_effective, effectiveness_score,
                symptom_addressed, related_dosha, notes, occurred_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            person_id,
            intervention_type,
            intervention_name,
            was_effective,
            effectiveness_score,
            symptom_addressed,
            related_dosha,
            notes,
            occurred_at,
            one=True,
        )

        logger.info(
            "[outcomes] Logged intervention: %s/%s effective=%s for %s",
            intervention_type, intervention_name, was_effective, person_id[:8]
        )
        return str(result["id"]) if result else None

    except Exception as e:
        logger.warning(f"Failed to log intervention outcome: {e}")
        return None


async def get_effective_interventions(
    person_id: str,
    symptom: Optional[str] = None,
    dosha: Optional[str] = None,
    min_effectiveness: float = 0.5,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get interventions that have worked for this user.

    Used by causal_reasoning to suggest "last time, X helped".

    Args:
        person_id: User ID
        symptom: Filter by symptom addressed
        dosha: Filter by dosha
        min_effectiveness: Minimum score threshold
        limit: Max results

    Returns:
        List of effective interventions with stats
    """
    filters = ["person_id = $1", "was_effective = true", "effectiveness_score >= $2"]
    params: List[Any] = [person_id, min_effectiveness]
    param_idx = 3

    if symptom:
        filters.append(f"symptom_addressed = ${param_idx}")
        params.append(symptom)
        param_idx += 1

    if dosha:
        filters.append(f"related_dosha = ${param_idx}")
        params.append(dosha)
        param_idx += 1

    query = f"""
        SELECT
            intervention_type,
            intervention_name,
            COUNT(*) as times_used,
            AVG(effectiveness_score) as avg_effectiveness,
            MAX(occurred_at) as last_used,
            symptom_addressed,
            related_dosha
        FROM intervention_outcomes
        WHERE {" AND ".join(filters)}
        GROUP BY intervention_type, intervention_name, symptom_addressed, related_dosha
        ORDER BY avg_effectiveness DESC, times_used DESC
        LIMIT ${param_idx}
    """
    params.append(limit)

    try:
        results = await dbfetch(query, *params)
        return [
            {
                "intervention_type": r["intervention_type"],
                "intervention_name": r["intervention_name"],
                "times_used": r["times_used"],
                "avg_effectiveness": float(r["avg_effectiveness"]),
                "last_used": r["last_used"].isoformat() if r["last_used"] else None,
                "symptom_addressed": r["symptom_addressed"],
                "related_dosha": r["related_dosha"],
            }
            for r in (results or [])
        ]

    except Exception as e:
        logger.warning(f"Failed to get effective interventions: {e}")
        return []


async def update_symptom_resolution(
    person_id: str,
    symptom_log_id: str,
    interventions_tried: List[str],
    what_helped: List[str],
    what_didnt_help: Optional[List[str]] = None,
    resolution_summary: Optional[str] = None,
    resolution_time: Optional[datetime] = None,
) -> bool:
    """
    Update a symptom log entry with resolution information.

    Called when user reports feeling better to capture:
    - What interventions they tried
    - What actually helped
    - How long it took to resolve

    Args:
        person_id: User ID
        symptom_log_id: The symptom_log entry to update
        interventions_tried: All interventions attempted
        what_helped: Interventions that worked
        what_didnt_help: Interventions that didn't work
        resolution_summary: Optional text summary
        resolution_time: When symptom resolved

    Returns:
        Success boolean
    """
    resolution_time = resolution_time or datetime.utcnow()
    what_didnt_help = what_didnt_help or []

    try:
        import json
        await execute(
            """
            UPDATE symptom_log
            SET resolution_time = $1,
                interventions_tried = $2,
                what_helped = $3,
                what_didnt_help = $4,
                resolution_summary = $5
            WHERE id = $6 AND person_id = $7
            """,
            resolution_time,
            json.dumps(interventions_tried),
            json.dumps(what_helped),
            json.dumps(what_didnt_help),
            resolution_summary,
            symptom_log_id,
            person_id,
        )

        # Also log individual intervention outcomes
        for intervention in what_helped:
            await log_intervention_outcome(
                person_id=person_id,
                intervention_type="mixed",
                intervention_name=intervention,
                was_effective=True,
                effectiveness_score=0.8,
            )

        for intervention in what_didnt_help:
            await log_intervention_outcome(
                person_id=person_id,
                intervention_type="mixed",
                intervention_name=intervention,
                was_effective=False,
                effectiveness_score=0.2,
            )

        logger.info(
            "[outcomes] Updated symptom resolution: %s with %d helpful interventions",
            symptom_log_id[:8], len(what_helped)
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to update symptom resolution: {e}")
        return False


async def infer_outcome_from_conversation(
    person_id: str,
    conversation_text: str,
    lookback_hours: int = 48,
) -> List[InterventionOutcome]:
    """
    Infer intervention outcomes from conversation text.

    Looks for patterns like:
    - "The walk really helped"
    - "Meditation didn't do much"
    - "Feeling better after eating"

    Args:
        person_id: User ID
        conversation_text: Recent conversation
        lookback_hours: How far back to look for interventions

    Returns:
        List of inferred outcomes
    """
    from sakhi.apps.api.core.llm import call_llm

    # Get recent interventions suggested
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
    recent_interventions = await dbfetch(
        """
        SELECT DISTINCT intervention_name
        FROM intervention_outcomes
        WHERE person_id = $1 AND occurred_at > $2
        """,
        person_id,
        cutoff,
    )

    if not recent_interventions:
        return []

    intervention_names = [r["intervention_name"] for r in recent_interventions]

    prompt = f"""Analyze this conversation for feedback about interventions/activities.

Recent interventions the user tried: {intervention_names}

Conversation:
---
{conversation_text}
---

For each intervention mentioned, determine if the user indicates it helped or not.
Return JSON array:
[
  {{
    "intervention_name": "name",
    "was_effective": true/false,
    "effectiveness_score": 0.0-1.0,
    "evidence_quote": "relevant quote from text"
  }}
]

Only include interventions with clear feedback. Return [] if no feedback found."""

    try:
        from sakhi.apps.api.core.llm import extract_json_from_llm_response
        response = await call_llm(prompt=prompt, max_tokens=300)
        data = extract_json_from_llm_response(response)

        outcomes = []
        for item in data if isinstance(data, list) else []:
            if item.get("intervention_name"):
                outcomes.append(InterventionOutcome(
                    intervention_type="inferred",
                    intervention_name=item["intervention_name"],
                    was_effective=item.get("was_effective", False),
                    effectiveness_score=item.get("effectiveness_score", 0.5),
                    notes=item.get("evidence_quote"),
                ))

        return outcomes

    except Exception as e:
        logger.warning(f"Failed to infer outcomes: {e}")
        return []
