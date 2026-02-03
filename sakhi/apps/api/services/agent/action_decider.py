"""
Action Decider Service
----------------------
Decides what action to take based on screen analysis and task context.

This service is the "brain" of Sakhi's vision loop:
- Takes screen analysis + task context
- Reasons about what to do next
- Returns a specific action to execute

The decider considers:
- What the user is trying to accomplish
- What's currently visible on screen
- What actions have already been taken
- User preferences (from Sakhi's memory)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)

# Default model for action decisions - Claude is better at reasoning
# Using Claude 3 Haiku for faster decisions, can upgrade to Sonnet for complex tasks
DEFAULT_DECISION_MODEL = "anthropic/claude-3-haiku-20240307"


# =============================================================================
# Action Decision
# =============================================================================

async def decide_next_action(
    task_description: str,
    task_context: Dict[str, Any],
    screen_analysis: Dict[str, Any],
    action_history: List[Dict[str, Any]],
    step_number: int,
) -> Dict[str, Any]:
    """
    Decide the next action to take.

    Args:
        task_description: What the user wants to accomplish
        task_context: Additional context (preferences, constraints)
        screen_analysis: Analysis of current screen state
        action_history: Previous actions taken
        step_number: Current step number

    Returns:
        Decision containing:
        - action: The action to take (or None if complete)
        - reasoning: Why this action was chosen
        - is_complete: Whether the task is done
    """
    from sakhi.apps.api.core.llm import get_router

    prompt = _build_decision_prompt(
        task_description=task_description,
        task_context=task_context,
        screen_analysis=screen_analysis,
        action_history=action_history,
        step_number=step_number,
    )

    try:
        router = get_router()

        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model=os.getenv("MODEL_DECISION") or DEFAULT_DECISION_MODEL,
            max_tokens=1000,
        )

        content = response.content[0].text if response.content else "{}"
        decision = _parse_decision_response(content)

        LOGGER.info(
            "[action_decider] Step %d decision: %s (%s)",
            step_number,
            decision.get("action", {}).get("type", "complete" if decision.get("is_complete") else "none"),
            decision.get("reasoning", "")[:50],
        )

        return decision

    except Exception as e:
        LOGGER.exception("[action_decider] Decision failed: %s", e)
        return {
            "action": None,
            "reasoning": f"Error making decision: {e}",
            "is_complete": False,
            "error": str(e),
        }


async def decide_with_preferences(
    task_description: str,
    screen_analysis: Dict[str, Any],
    person_id: str,
    action_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Decide action considering user's stored preferences.

    This version pulls preferences from Sakhi's memory to inform
    decisions (e.g., "user prefers window seats", "user is vegetarian").

    Args:
        task_description: What to accomplish
        screen_analysis: Current screen state
        person_id: User's person ID for preference lookup
        action_history: Previous actions

    Returns:
        Action decision with preference-informed reasoning
    """
    # Recall relevant preferences
    preferences = await _get_relevant_preferences(person_id, task_description)

    context = {
        "preferences": preferences,
        "person_id": person_id,
    }

    return await decide_next_action(
        task_description=task_description,
        task_context=context,
        screen_analysis=screen_analysis,
        action_history=action_history,
        step_number=len(action_history) + 1,
    )


async def should_stop(
    task_description: str,
    screen_analysis: Dict[str, Any],
    action_history: List[Dict[str, Any]],
    errors: List[str],
) -> Dict[str, Any]:
    """
    Determine if the vision loop should stop.

    Returns:
        Decision about stopping:
        - should_stop: True if should stop
        - reason: Why (completed, stuck, failed)
        - confidence: How sure we are
    """
    from sakhi.apps.api.core.llm import get_router

    prompt = f"""Evaluate whether this automated task should stop.

TASK: {task_description}

CURRENT SCREEN:
{json.dumps(screen_analysis, indent=2)[:1500]}

ACTIONS TAKEN ({len(action_history)} total):
{json.dumps(action_history[-5:], indent=2) if action_history else "None"}

ERRORS ENCOUNTERED:
{json.dumps(errors, indent=2) if errors else "None"}

Should the task stop? Consider:
1. Has the task been completed successfully?
2. Is the task stuck in a loop (repeating same actions)?
3. Have there been too many errors?
4. Is there no clear path forward?

Respond with JSON:
{{
    "should_stop": true/false,
    "reason": "completed|stuck|failed|blocked|can_continue",
    "explanation": "detailed explanation",
    "confidence": 0.0-1.0,
    "suggestion": "what to do if should_stop is false"
}}

Return ONLY the JSON."""

    try:
        router = get_router()

        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model=os.getenv("MODEL_DECISION") or DEFAULT_DECISION_MODEL,
            max_tokens=500,
        )

        content = response.content[0].text if response.content else "{}"
        return _parse_json_response(content)

    except Exception as e:
        LOGGER.exception("[action_decider] Stop check failed: %s", e)
        return {
            "should_stop": True,
            "reason": "error",
            "explanation": f"Error evaluating: {e}",
            "confidence": 0.5,
        }


# =============================================================================
# Restaurant-Specific Decisions
# =============================================================================

async def decide_restaurant_action(
    search_criteria: Dict[str, Any],
    screen_analysis: Dict[str, Any],
    action_history: List[Dict[str, Any]],
    person_preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Specialized decision making for restaurant search tasks.

    This is optimized for the demo use case of finding and booking
    restaurants on behalf of the user.

    Args:
        search_criteria: What the user wants (cuisine, location, time, etc.)
        screen_analysis: Current screen state
        action_history: Previous actions
        person_preferences: User's food/dining preferences

    Returns:
        Action decision tailored for restaurant search
    """
    from sakhi.apps.api.core.llm import get_router

    prompt = _build_restaurant_decision_prompt(
        search_criteria=search_criteria,
        screen_analysis=screen_analysis,
        action_history=action_history,
        preferences=person_preferences,
    )

    try:
        router = get_router()

        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model=os.getenv("MODEL_DECISION") or DEFAULT_DECISION_MODEL,
            max_tokens=1000,
        )

        content = response.content[0].text if response.content else "{}"
        return _parse_decision_response(content)

    except Exception as e:
        LOGGER.exception("[action_decider] Restaurant decision failed: %s", e)
        return {
            "action": None,
            "reasoning": f"Error: {e}",
            "is_complete": False,
            "error": str(e),
        }


async def evaluate_restaurant_option(
    restaurant_info: Dict[str, Any],
    user_preferences: Dict[str, Any],
    search_criteria: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate if a restaurant matches user preferences.

    Used when Sakhi finds a potential restaurant to determine
    if it's a good match before suggesting it.

    Args:
        restaurant_info: Information about the restaurant
        user_preferences: User's stored preferences
        search_criteria: What the user asked for

    Returns:
        Evaluation with match score and reasoning
    """
    from sakhi.apps.api.core.llm import get_router

    prompt = f"""Evaluate if this restaurant matches the user's preferences.

RESTAURANT:
{json.dumps(restaurant_info, indent=2)}

USER PREFERENCES:
{json.dumps(user_preferences, indent=2)}

SEARCH CRITERIA:
{json.dumps(search_criteria, indent=2)}

Evaluate and respond with JSON:
{{
    "match_score": 0.0-1.0,
    "matches": ["list of matching criteria"],
    "mismatches": ["list of mismatching criteria"],
    "unknown": ["criteria we can't determine"],
    "recommendation": "strongly_recommend|recommend|neutral|not_recommended",
    "reasoning": "explanation of the evaluation"
}}

Return ONLY the JSON."""

    try:
        router = get_router()

        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model=os.getenv("MODEL_DECISION") or DEFAULT_DECISION_MODEL,
            max_tokens=500,
        )

        content = response.content[0].text if response.content else "{}"
        return _parse_json_response(content)

    except Exception as e:
        LOGGER.exception("[action_decider] Restaurant evaluation failed: %s", e)
        return {
            "match_score": 0.5,
            "recommendation": "neutral",
            "reasoning": f"Error evaluating: {e}",
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _build_decision_prompt(
    task_description: str,
    task_context: Dict[str, Any],
    screen_analysis: Dict[str, Any],
    action_history: List[Dict[str, Any]],
    step_number: int,
) -> str:
    """Build the decision prompt."""
    prompt = f"""You are an AI agent controlling a computer to help the user. Decide what action to take next.

TASK: {task_description}

CURRENT SCREEN (step {step_number}):
- Description: {screen_analysis.get('description', 'Unknown')}
- Page type: {screen_analysis.get('page_type', 'unknown')}
- URL: {screen_analysis.get('url', 'not visible')}
- Key text: {screen_analysis.get('text', '')[:500]}

AVAILABLE ELEMENTS:
"""

    elements = screen_analysis.get("elements", [])
    for elem in elements[:15]:  # Limit to top elements
        prompt += f"  - {elem.get('type', '?')}: \"{elem.get('text', '')}\" at ({elem.get('x', 0)}, {elem.get('y', 0)})"
        if elem.get('actionable'):
            prompt += " [CLICKABLE]"
        prompt += "\n"

    if action_history:
        prompt += f"\nPREVIOUS ACTIONS ({len(action_history)} total):\n"
        for action in action_history[-5:]:
            prompt += f"  - {action.get('type', '?')}: {action.get('reasoning', '')[:50]}\n"

    if task_context.get("preferences"):
        prompt += f"\nUSER PREFERENCES:\n{json.dumps(task_context['preferences'], indent=2)}\n"

    prompt += """
AVAILABLE ACTIONS:
- click: Click at coordinates {x, y}
- type: Type text {text}
- key: Press key {key} (enter, tab, escape, etc.)
- scroll: Scroll {direction} (up/down) by {amount} pixels
- navigate: Go to {url}
- wait: Wait {ms} milliseconds

Decide what to do next. If the task is complete, set is_complete to true.

Respond with JSON:
{
    "action": {
        "type": "click|type|key|scroll|navigate|wait",
        "parameters": {...},
        "description": "what this action does"
    },
    "reasoning": "why this action was chosen",
    "is_complete": false,
    "progress": "estimate of task completion",
    "next_expected": "what should happen after this action"
}

If the task is complete:
{
    "action": null,
    "reasoning": "explanation of completion",
    "is_complete": true,
    "result": "summary of what was accomplished"
}

Return ONLY the JSON."""

    return prompt


def _build_restaurant_decision_prompt(
    search_criteria: Dict[str, Any],
    screen_analysis: Dict[str, Any],
    action_history: List[Dict[str, Any]],
    preferences: Optional[Dict[str, Any]],
) -> str:
    """Build prompt for restaurant-specific decisions."""
    prompt = f"""You are Sakhi, an AI assistant helping find and book a restaurant.

SEARCH CRITERIA:
{json.dumps(search_criteria, indent=2)}

USER'S DINING PREFERENCES:
{json.dumps(preferences or {}, indent=2)}

CURRENT SCREEN:
- Type: {screen_analysis.get('page_type', 'unknown')}
- URL: {screen_analysis.get('url', 'not visible')}
- Description: {screen_analysis.get('description', '')}

VISIBLE ELEMENTS:
"""

    elements = screen_analysis.get("elements", [])
    for elem in elements[:15]:
        if elem.get('actionable') or elem.get('relevance') == 'high':
            prompt += f"  - {elem.get('type', '?')}: \"{elem.get('text', '')}\" at ({elem.get('x', 0)}, {elem.get('y', 0)})\n"

    if action_history:
        prompt += f"\nACTIONS TAKEN:\n"
        for action in action_history[-5:]:
            prompt += f"  - {action.get('type', '?')}: {action.get('reasoning', '')}\n"

    prompt += """
Your goal is to find a restaurant matching the criteria and the user's preferences.

Strategy:
1. If on search results, look for restaurants matching preferences
2. Consider ratings, reviews, and relevance to user preferences
3. Click on promising options to see details
4. Look for reservation/booking options

Respond with JSON:
{
    "action": {
        "type": "click|type|key|scroll|navigate|wait",
        "parameters": {...},
        "description": "what this action does"
    },
    "reasoning": "why this action, considering user preferences",
    "is_complete": false,
    "found_options": ["list any good restaurant options found so far"]
}

If you found a suitable restaurant:
{
    "action": null,
    "reasoning": "why this restaurant is a good match",
    "is_complete": true,
    "recommended_restaurant": {
        "name": "restaurant name",
        "why_recommended": "matches user preferences because...",
        "next_steps": "how to book/reserve"
    }
}

Return ONLY the JSON."""

    return prompt


async def _get_relevant_preferences(
    person_id: str,
    task_description: str,
) -> Dict[str, Any]:
    """Get user preferences relevant to the task."""
    try:
        from sakhi.apps.api.services.memory.recall import recall_advanced

        # Recall preferences related to this task
        results = await recall_advanced(
            person_id=person_id,
            query=f"preferences for: {task_description}",
            k=5,
        )

        # Extract preference-like items
        preferences = {}
        for result in results:
            content = result.get("content", "")
            source = result.get("source", "")

            # Look for preference patterns
            if "prefer" in content.lower() or "like" in content.lower():
                if "food" in task_description.lower() or "restaurant" in task_description.lower():
                    if "food_preferences" not in preferences:
                        preferences["food_preferences"] = []
                    preferences["food_preferences"].append(content)

        return preferences

    except Exception as e:
        LOGGER.warning("[action_decider] Failed to get preferences: %s", e)
        return {}


def _parse_decision_response(content: str) -> Dict[str, Any]:
    """Parse Claude's decision response."""
    return _parse_json_response(content)


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse a JSON response, handling markdown code blocks."""
    try:
        # Strip markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        LOGGER.warning("[action_decider] JSON parse error: %s", e)
        return {
            "action": None,
            "reasoning": "Failed to parse response",
            "is_complete": False,
            "error": str(e),
        }


__all__ = [
    "decide_next_action",
    "decide_with_preferences",
    "should_stop",
    "decide_restaurant_action",
    "evaluate_restaurant_option",
]
