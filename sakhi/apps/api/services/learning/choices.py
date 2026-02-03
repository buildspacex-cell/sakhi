"""
A.8.1 Choice Logger
-------------------
Track when user picks option A over B.

When Sakhi presents options (restaurants, products, activities),
this logs which one the user chose. This implicit signal helps
learn preferences without explicit feedback.

Example:
- Sakhi offers 3 restaurants
- User picks the spicy Indian one
- We infer: user likely prefers spicier food
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as execute

logger = logging.getLogger(__name__)


class ChoiceOption(BaseModel):
    """A single option presented to user."""
    name: str
    description: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class UserChoice(BaseModel):
    """Record of a user choice."""
    choice_context: str = Field(description="Context: restaurant, product, activity, food")
    options_presented: List[ChoiceOption]
    chosen_option: Optional[ChoiceOption] = None
    chosen_index: Optional[int] = None
    inferred_reasons: List[str] = Field(default_factory=list)


async def log_user_choice(
    person_id: str,
    choice_context: str,
    options_presented: List[Dict[str, Any]],
    chosen_option: Dict[str, Any],
    chosen_index: int,
    conversation_id: Optional[str] = None,
    recommendation_id: Optional[str] = None,
) -> Optional[str]:
    """
    Log a user's choice between options.

    Args:
        person_id: User ID
        choice_context: What kind of choice (restaurant, product, activity)
        options_presented: All options shown
        chosen_option: The option they picked
        chosen_index: Position of chosen option (0-indexed)
        conversation_id: Optional conversation context
        recommendation_id: Optional link to recommendation_feedback

    Returns:
        Choice ID or None
    """
    try:
        # Infer why they might have chosen this
        inferred_reasons = await _infer_choice_reasons(
            options_presented, chosen_option, chosen_index
        )

        result = await dbfetch(
            """
            INSERT INTO user_choices (
                person_id, choice_context, options_presented, option_count,
                chosen_option, chosen_index, inferred_reasons,
                conversation_id, recommendation_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            person_id,
            choice_context,
            json.dumps(options_presented),
            len(options_presented),
            json.dumps(chosen_option),
            chosen_index,
            json.dumps(inferred_reasons),
            conversation_id,
            recommendation_id,
            one=True,
        )

        logger.info(
            "[choices] Logged choice: %s context=%s index=%d of %d",
            person_id[:8], choice_context, chosen_index, len(options_presented)
        )

        # Trigger preference update
        await _apply_choice_to_preferences(
            person_id, choice_context, options_presented, chosen_option, inferred_reasons
        )

        return str(result["id"]) if result else None

    except Exception as e:
        logger.warning(f"Failed to log user choice: {e}")
        return None


async def _infer_choice_reasons(
    options: List[Dict[str, Any]],
    chosen: Dict[str, Any],
    chosen_index: int,
) -> List[str]:
    """
    Infer why the user might have chosen this option.

    Compares chosen option attributes against others.
    """
    reasons = []

    if not options or not chosen:
        return reasons

    chosen_attrs = chosen.get("attributes", {})
    if not chosen_attrs:
        return reasons

    # Compare each attribute against other options
    for attr_name, attr_value in chosen_attrs.items():
        if attr_value is None:
            continue

        # Check if this attribute is notably different
        other_values = []
        for i, opt in enumerate(options):
            if i != chosen_index:
                other_val = opt.get("attributes", {}).get(attr_name)
                if other_val is not None:
                    other_values.append(other_val)

        if not other_values:
            continue

        # For numeric attributes
        if isinstance(attr_value, (int, float)) and all(isinstance(v, (int, float)) for v in other_values):
            avg_others = sum(other_values) / len(other_values)
            if attr_value > avg_others * 1.3:
                reasons.append(f"Higher {attr_name.replace('_', ' ')}")
            elif attr_value < avg_others * 0.7:
                reasons.append(f"Lower {attr_name.replace('_', ' ')}")

        # For boolean attributes
        elif isinstance(attr_value, bool):
            if attr_value and not any(other_values):
                reasons.append(f"Has {attr_name.replace('_', ' ')}")
            elif not attr_value and all(other_values):
                reasons.append(f"No {attr_name.replace('_', ' ')}")

    # Position bias check
    if chosen_index == 0:
        reasons.append("First option presented")

    return reasons[:5]  # Limit to 5 reasons


async def _apply_choice_to_preferences(
    person_id: str,
    context: str,
    options: List[Dict[str, Any]],
    chosen: Dict[str, Any],
    reasons: List[str],
) -> None:
    """Apply choice signal to preference updater."""
    try:
        from sakhi.apps.api.services.learning.preference_updater import apply_choice_to_preferences
        await apply_choice_to_preferences(
            person_id=person_id,
            domain=_context_to_domain(context),
            chosen_attributes=chosen.get("attributes", {}),
            rejected_attributes=[
                opt.get("attributes", {})
                for opt in options
                if opt != chosen
            ],
        )
    except Exception as e:
        logger.debug(f"Could not apply choice to preferences: {e}")


def _context_to_domain(context: str) -> str:
    """Map choice context to preference domain."""
    mapping = {
        "restaurant": "food",
        "food": "food",
        "meal": "food",
        "product": "custom",
        "fragrance": "fragrance",
        "perfume": "fragrance",
        "activity": "wellness",
        "hotel": "travel",
        "destination": "travel",
    }
    return mapping.get(context.lower(), "custom")


async def get_choice_patterns(
    person_id: str,
    context: Optional[str] = None,
    lookback_days: int = 30,
    min_choices: int = 3,
) -> Dict[str, Any]:
    """
    Analyze choice patterns for a user.

    Returns:
        Pattern analysis with frequently chosen attributes
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    try:
        # Get all choices
        query = """
            SELECT choice_context, chosen_option, inferred_reasons, created_at
            FROM user_choices
            WHERE person_id = $1 AND created_at > $2
        """
        params: List[Any] = [person_id, cutoff]

        if context:
            query += " AND choice_context = $3"
            params.append(context)

        query += " ORDER BY created_at DESC"

        choices = await dbfetch(query, *params)

        if not choices or len(choices) < min_choices:
            return {"patterns": [], "total_choices": len(choices or [])}

        # Aggregate reasons
        reason_counts: Dict[str, int] = {}
        attribute_values: Dict[str, List[float]] = {}

        for choice in choices:
            # Count reasons
            reasons = choice.get("inferred_reasons") or []
            if isinstance(reasons, str):
                reasons = json.loads(reasons)
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            # Aggregate attributes
            chosen = choice.get("chosen_option")
            if isinstance(chosen, str):
                chosen = json.loads(chosen)
            if chosen:
                for attr, val in chosen.get("attributes", {}).items():
                    if isinstance(val, (int, float)):
                        if attr not in attribute_values:
                            attribute_values[attr] = []
                        attribute_values[attr].append(val)

        # Calculate patterns
        patterns = []

        # Top reasons
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1])[:5]:
            if count >= 2:
                patterns.append({
                    "type": "reason",
                    "description": reason,
                    "frequency": count,
                    "percentage": round(count / len(choices) * 100, 1),
                })

        # Attribute tendencies
        for attr, values in attribute_values.items():
            if len(values) >= min_choices:
                avg = sum(values) / len(values)
                patterns.append({
                    "type": "attribute",
                    "attribute": attr,
                    "average_chosen": round(avg, 2),
                    "sample_size": len(values),
                })

        return {
            "patterns": patterns,
            "total_choices": len(choices),
            "contexts": list(set(c["choice_context"] for c in choices)),
        }

    except Exception as e:
        logger.warning(f"Failed to analyze choice patterns: {e}")
        return {"patterns": [], "error": str(e)}
