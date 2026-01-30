"""Goal suggester: clusters intents into goal suggestions respecting crystallization thresholds."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.crystallization.thresholds import CRYSTALLIZATION_THRESHOLDS
from sakhi.apps.worker.utils.llm_parsing import extract_json_from_llm_response

LOGGER = logging.getLogger(__name__)

# Goal threshold from crystallization rules
GOAL_THRESHOLD = CRYSTALLIZATION_THRESHOLDS.get("goal")
MIN_MENTIONS = GOAL_THRESHOLD.min_mentions if GOAL_THRESHOLD else 3
WINDOW_DAYS = GOAL_THRESHOLD.window_days if GOAL_THRESHOLD else 21
MIN_CONFIDENCE = GOAL_THRESHOLD.min_confidence if GOAL_THRESHOLD else 0.5


async def suggest_goals_from_intents(person_id: str) -> Dict[str, Any]:
    """
    Cluster related intents into goal suggestions.
    Only suggests goals that meet crystallization thresholds (3+ mentions).

    Returns suggestions for user confirmation - does NOT auto-create goals.
    """
    # Fetch recent intents within the window
    window_start = datetime.utcnow() - timedelta(days=WINDOW_DAYS)

    intents = await dbfetch(
        """
        SELECT id, title, intent_type, timeline, priority, clarity_score,
               context_snapshot, created_at
        FROM intents
        WHERE user_id = $1
          AND created_at >= $2
          AND status IN ('draft', 'pending')
          AND intent_type IN ('goal', 'task', 'plan')
        ORDER BY created_at DESC
        """,
        person_id,
        window_start,
    )

    if not intents or len(intents) < MIN_MENTIONS:
        LOGGER.debug(
            "[GoalSuggester] Not enough intents for person=%s (have=%s, need=%s)",
            person_id,
            len(intents) if intents else 0,
            MIN_MENTIONS,
        )
        return {"suggestions": [], "reason": "insufficient_intents"}

    # Fetch existing active goals to avoid duplicates
    existing_goals = await dbfetch(
        """
        SELECT title, description FROM goals
        WHERE person_id = $1 AND status = 'active'
        """,
        person_id,
    )

    # Use LLM to cluster intents into goal suggestions
    intents_text = json.dumps([dict(i) for i in intents], default=str, indent=2)
    existing_text = json.dumps([dict(g) for g in (existing_goals or [])], default=str, indent=2)

    prompt = f"""You are Sakhi's Goal Suggester.
Review user intents and cluster related ones into potential goals.

INTENTS (last {WINDOW_DAYS} days):
{intents_text}

EXISTING ACTIVE GOALS (avoid duplicates):
{existing_text}

RULES:
1. Only suggest goals that appear at least {MIN_MENTIONS} times in intents
2. Cluster similar/related intents into single goal suggestions
3. Don't duplicate existing goals
4. Include evidence (which intent IDs support this goal)

Output JSON:
```json
{{
  "suggestions": [
    {{
      "title": "<goal title>",
      "description": "<1-2 sentence description>",
      "type": "goal",
      "priority": 1-5,
      "evidence_intent_ids": [1, 2, 3],
      "mention_count": 3,
      "confidence": 0.7,
      "timeline": "this_week" | "this_month" | "this_quarter",
      "reasoning": "<why this goal was suggested>"
    }}
  ],
  "summary": "<brief summary of goal landscape>"
}}
```

If no goals meet the threshold, return empty suggestions array."""

    response = await call_llm(
        messages=[{"role": "user", "content": prompt}],
        person_id=person_id,
    )

    payload = response if isinstance(response, str) else json.dumps(response)
    parsed = extract_json_from_llm_response(payload)

    if not parsed:
        LOGGER.warning("[GoalSuggester] Failed to parse LLM response for person=%s", person_id)
        return {"suggestions": [], "reason": "parse_error"}

    suggestions = parsed.get("suggestions") or []

    # Filter to only include suggestions meeting threshold
    valid_suggestions = []
    for s in suggestions:
        mention_count = s.get("mention_count", 0)
        confidence = s.get("confidence", 0.5)

        if mention_count >= MIN_MENTIONS and confidence >= MIN_CONFIDENCE:
            valid_suggestions.append(s)

    LOGGER.info(
        "[GoalSuggester] person=%s intents=%s suggestions=%s valid=%s",
        person_id,
        len(intents),
        len(suggestions),
        len(valid_suggestions),
    )

    return {
        "suggestions": valid_suggestions,
        "total_intents": len(intents),
        "summary": parsed.get("summary"),
    }


async def confirm_goal_suggestion(
    person_id: str,
    suggestion: Dict[str, Any],
) -> Optional[str]:
    """
    Convert a confirmed suggestion into an actual goal.
    Returns the new goal ID if created.
    """
    title = suggestion.get("title")
    if not title:
        return None

    try:
        result = await dbfetch(
            """
            INSERT INTO goals (person_id, type, title, description, priority, status)
            VALUES ($1, $2, $3, $4, $5, 'active')
            RETURNING id
            """,
            person_id,
            suggestion.get("type", "goal"),
            title,
            suggestion.get("description"),
            suggestion.get("priority", 3),
            one=True,
        )

        goal_id = str(result.get("id")) if result else None

        # Update linked intents to 'converted' status
        evidence_ids = suggestion.get("evidence_intent_ids") or []
        if evidence_ids and goal_id:
            await dbexec(
                """
                UPDATE intents
                SET status = 'converted'
                WHERE id = ANY($1::bigint[])
                  AND user_id = $2
                """,
                evidence_ids,
                person_id,
            )

        LOGGER.info(
            "[GoalSuggester] Confirmed goal=%s for person=%s from %s intents",
            goal_id,
            person_id,
            len(evidence_ids),
        )

        return goal_id

    except Exception as exc:
        LOGGER.warning("[GoalSuggester] Failed to create goal: %s", exc)
        return None


async def get_goal_suggestion_status(person_id: str) -> Dict[str, Any]:
    """
    Get current status of goal suggestions for the user.
    Useful for displaying in UI.
    """
    window_start = datetime.utcnow() - timedelta(days=WINDOW_DAYS)

    # Count intents by type
    intent_counts = await dbfetch(
        """
        SELECT intent_type, COUNT(*) as count
        FROM intents
        WHERE user_id = $1
          AND created_at >= $2
          AND status IN ('draft', 'pending')
        GROUP BY intent_type
        """,
        person_id,
        window_start,
    )

    # Count active goals
    goal_count = await dbfetch(
        """
        SELECT COUNT(*) as count FROM goals
        WHERE person_id = $1 AND status = 'active'
        """,
        person_id,
        one=True,
    )

    total_intents = sum(r.get("count", 0) for r in (intent_counts or []))
    ready_for_suggestions = total_intents >= MIN_MENTIONS

    return {
        "total_intents": total_intents,
        "intent_breakdown": {r.get("intent_type"): r.get("count") for r in (intent_counts or [])},
        "active_goals": (goal_count or {}).get("count", 0),
        "ready_for_suggestions": ready_for_suggestions,
        "threshold": MIN_MENTIONS,
        "window_days": WINDOW_DAYS,
    }


__all__ = [
    "suggest_goals_from_intents",
    "confirm_goal_suggestion",
    "get_goal_suggestion_status",
]
