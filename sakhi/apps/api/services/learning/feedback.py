"""
A.8.2 Recommendation Feedback
-----------------------------
Capture feedback signals on recommendations.

Two types of feedback:
1. Explicit: thumbs up/down, rating, text ("too spicy")
2. Implicit: was_followed, was_reordered, time_to_action

This feeds into preference_updater to adjust preference weights.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import json

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as execute

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    DISMISS = "dismiss"
    FOLLOW = "follow"           # User acted on recommendation
    REORDER = "reorder"         # User ordered again
    COMPLAINT = "complaint"     # Negative text feedback
    PRAISE = "praise"           # Positive text feedback


class AffectedDimension(BaseModel):
    """A preference dimension affected by feedback."""
    domain: str
    dimension: str
    direction: str = Field(description="increase, decrease, or neutral")
    magnitude: float = Field(default=0.1, ge=0.0, le=1.0)


class RecommendationFeedback(BaseModel):
    """Feedback on a recommendation."""
    recommendation_type: str
    recommendation_domain: Optional[str] = None
    recommendation_content: Dict[str, Any]
    feedback_type: FeedbackType
    feedback_text: Optional[str] = None
    rating: Optional[float] = None
    was_followed: Optional[bool] = None
    affected_dimensions: List[AffectedDimension] = Field(default_factory=list)


# Keywords that indicate feedback in text
POSITIVE_KEYWORDS = [
    "loved", "perfect", "great", "amazing", "delicious",
    "exactly what", "spot on", "just right", "wonderful"
]

NEGATIVE_KEYWORDS = [
    "too spicy", "too hot", "too cold", "too sweet", "too salty",
    "didn't like", "not for me", "too strong", "too weak",
    "overwhelming", "underwhelming", "not enough"
]

DIMENSION_KEYWORDS = {
    "spicy": ("food", "spiciness"),
    "hot": ("food", "temperature"),
    "cold": ("food", "temperature"),
    "sweet": ("food", "sweetness"),
    "salty": ("food", "saltiness"),
    "sour": ("food", "sourness"),
    "strong": ("fragrance", "intensity"),
    "woody": ("fragrance", "woodiness"),
    "floral": ("fragrance", "florals"),
    "loud": ("environment", "noise_tolerance"),
    "crowded": ("environment", "crowd_tolerance"),
}


async def log_recommendation_feedback(
    person_id: str,
    recommendation_type: str,
    recommendation_content: Dict[str, Any],
    feedback_type: FeedbackType,
    feedback_text: Optional[str] = None,
    rating: Optional[float] = None,
    was_followed: bool = False,
    was_reordered: bool = False,
    time_to_action_seconds: Optional[int] = None,
    recommendation_domain: Optional[str] = None,
    conversation_id: Optional[str] = None,
    choice_id: Optional[str] = None,
) -> Optional[str]:
    """
    Log feedback on a recommendation.

    Args:
        person_id: User ID
        recommendation_type: Type (product, food, activity, wellness)
        recommendation_content: The recommendation details
        feedback_type: Type of feedback
        feedback_text: Optional text feedback
        rating: Optional numeric rating
        was_followed: Did they act on it?
        was_reordered: Did they order again?
        time_to_action_seconds: How long before acting
        recommendation_domain: Preference domain
        conversation_id: Conversation context
        choice_id: Link to user_choices

    Returns:
        Feedback ID or None
    """
    try:
        # Extract affected dimensions from feedback
        affected_dims = []
        if feedback_text:
            affected_dims = _extract_affected_dimensions(
                feedback_text, feedback_type, recommendation_domain
            )

        result = await dbfetch(
            """
            INSERT INTO recommendation_feedback (
                person_id, recommendation_type, recommendation_domain,
                recommendation_content, feedback_type, feedback_text,
                rating, was_followed, was_reordered, time_to_action_seconds,
                affected_dimensions, conversation_id, choice_id,
                acted_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id
            """,
            person_id,
            recommendation_type,
            recommendation_domain,
            json.dumps(recommendation_content),
            feedback_type.value,
            feedback_text,
            rating,
            was_followed,
            was_reordered,
            time_to_action_seconds,
            json.dumps([d.model_dump() for d in affected_dims]),
            conversation_id,
            choice_id,
            datetime.utcnow() if was_followed else None,
            one=True,
        )

        feedback_id = str(result["id"]) if result else None

        logger.info(
            "[feedback] Logged: %s type=%s feedback=%s dims=%d",
            person_id[:8], recommendation_type, feedback_type.value, len(affected_dims)
        )

        # Trigger preference update if we have affected dimensions
        if affected_dims and feedback_id:
            from sakhi.apps.api.services.learning.preference_updater import apply_feedback_to_preferences
            await apply_feedback_to_preferences(
                person_id=person_id,
                feedback_id=feedback_id,
                feedback_type=feedback_type,
                affected_dimensions=affected_dims,
            )

        return feedback_id

    except Exception as e:
        logger.warning(f"Failed to log recommendation feedback: {e}")
        return None


def _extract_affected_dimensions(
    text: str,
    feedback_type: FeedbackType,
    domain: Optional[str],
) -> List[AffectedDimension]:
    """Extract which preference dimensions are affected by this feedback."""
    affected = []
    text_lower = text.lower()

    # Check for dimension keywords
    for keyword, (dim_domain, dimension) in DIMENSION_KEYWORDS.items():
        if keyword in text_lower:
            # Determine direction based on feedback type and context
            is_negative = feedback_type in [
                FeedbackType.THUMBS_DOWN, FeedbackType.COMPLAINT, FeedbackType.DISMISS
            ]

            # Check if text says "too X" or "not enough X"
            is_too_much = f"too {keyword}" in text_lower
            is_not_enough = f"not enough {keyword}" in text_lower or f"more {keyword}" in text_lower

            if is_too_much:
                direction = "decrease"
            elif is_not_enough:
                direction = "increase"
            elif is_negative:
                direction = "decrease"
            else:
                direction = "increase"

            affected.append(AffectedDimension(
                domain=domain or dim_domain,
                dimension=dimension,
                direction=direction,
                magnitude=0.15 if is_too_much or is_not_enough else 0.1,
            ))

    # If no specific dimensions found, apply general feedback
    if not affected and domain:
        direction = "increase" if feedback_type in [
            FeedbackType.THUMBS_UP, FeedbackType.PRAISE, FeedbackType.FOLLOW, FeedbackType.REORDER
        ] else "decrease"

        affected.append(AffectedDimension(
            domain=domain,
            dimension="general_preference",
            direction=direction,
            magnitude=0.05,
        ))

    return affected


async def extract_feedback_from_text(
    person_id: str,
    text: str,
    recent_recommendation: Optional[Dict[str, Any]] = None,
) -> Optional[RecommendationFeedback]:
    """
    Extract feedback from conversational text.

    Looks for patterns like:
    - "That was too spicy"
    - "Loved the restaurant"
    - "Not really my thing"

    Args:
        person_id: User ID
        text: Conversation text
        recent_recommendation: Context about recent recommendation

    Returns:
        Extracted feedback or None
    """
    text_lower = text.lower()

    # Quick check for feedback indicators
    has_positive = any(kw in text_lower for kw in POSITIVE_KEYWORDS)
    has_negative = any(kw in text_lower for kw in NEGATIVE_KEYWORDS)

    if not has_positive and not has_negative:
        return None

    # Determine feedback type
    if has_positive and not has_negative:
        feedback_type = FeedbackType.PRAISE
    elif has_negative and not has_positive:
        feedback_type = FeedbackType.COMPLAINT
    else:
        # Mixed - use LLM to clarify
        from sakhi.apps.api.core.llm import call_llm, extract_json_from_llm_response

        prompt = f"""Analyze this text for feedback sentiment:

Text: "{text}"

Is this positive or negative feedback? Return JSON:
{{"sentiment": "positive" or "negative", "about": "what the feedback is about"}}"""

        try:
            response = await call_llm(prompt=prompt, max_tokens=100)
            data = extract_json_from_llm_response(response)
            feedback_type = FeedbackType.PRAISE if data.get("sentiment") == "positive" else FeedbackType.COMPLAINT
        except Exception:
            feedback_type = FeedbackType.COMPLAINT  # Default to negative for safety

    # Build feedback object
    domain = recent_recommendation.get("domain") if recent_recommendation else None
    affected = _extract_affected_dimensions(text, feedback_type, domain)

    return RecommendationFeedback(
        recommendation_type=recent_recommendation.get("type", "unknown") if recent_recommendation else "unknown",
        recommendation_domain=domain,
        recommendation_content=recent_recommendation or {},
        feedback_type=feedback_type,
        feedback_text=text,
        affected_dimensions=affected,
    )


async def get_feedback_summary(
    person_id: str,
    domain: Optional[str] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """Get summary of feedback patterns for a user."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        query = """
            SELECT feedback_type, recommendation_domain,
                   COUNT(*) as count,
                   AVG(rating) as avg_rating
            FROM recommendation_feedback
            WHERE person_id = $1 AND created_at > $2
        """
        params: List[Any] = [person_id, cutoff]

        if domain:
            query += " AND recommendation_domain = $3"
            params.append(domain)

        query += " GROUP BY feedback_type, recommendation_domain"

        results = await dbfetch(query, *params)

        summary = {
            "total_feedback": 0,
            "by_type": {},
            "by_domain": {},
            "avg_rating": None,
        }

        ratings = []
        for r in (results or []):
            count = r["count"]
            summary["total_feedback"] += count

            fb_type = r["feedback_type"]
            if fb_type not in summary["by_type"]:
                summary["by_type"][fb_type] = 0
            summary["by_type"][fb_type] += count

            fb_domain = r["recommendation_domain"]
            if fb_domain:
                if fb_domain not in summary["by_domain"]:
                    summary["by_domain"][fb_domain] = 0
                summary["by_domain"][fb_domain] += count

            if r["avg_rating"]:
                ratings.append(float(r["avg_rating"]))

        if ratings:
            summary["avg_rating"] = round(sum(ratings) / len(ratings), 2)

        return summary

    except Exception as e:
        logger.warning(f"Failed to get feedback summary: {e}")
        return {"error": str(e)}
