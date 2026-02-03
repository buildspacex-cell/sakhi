"""
Mission Decomposer - LLM-based decomposition of goals into actionable plans

Takes a high-level goal like "Build my Twitter brand" and breaks it down into:
- Phases (multi-week chunks with approval gates)
- Weekly plans (concrete objectives and actions)
- Scheduled actions (specific tasks to execute)

The decomposer considers:
- User context and preferences
- Realistic time estimates
- Dependencies between tasks
- Metrics and success criteria
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sakhi.apps.api.core.llm import call_llm
from .models import (
    MissionDecomposition, PhasePlan, WeekPlan, ActionPlan,
    MissionCategory
)

LOGGER = logging.getLogger(__name__)

# Day name to offset mapping
DAY_OFFSETS = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
}


async def decompose_mission(
    goal: str,
    person_id: UUID,
    category: Optional[MissionCategory] = None,
    context: Optional[Dict[str, Any]] = None,
    target_weeks: int = 8,
) -> MissionDecomposition:
    """
    Decompose a high-level goal into a structured mission plan.

    Args:
        goal: The user's goal in natural language
        person_id: User ID for personalization
        category: Optional category hint
        context: Additional context (preferences, constraints)
        target_weeks: How many weeks to plan for (default 8)

    Returns:
        MissionDecomposition with phases, weeks, and actions
    """
    prompt = _build_decomposition_prompt(
        goal=goal,
        category=category,
        context=context,
        target_weeks=target_weeks,
    )

    try:
        result = await call_llm(
            prompt=prompt,
            schema=MissionDecomposition,
            person_id=str(person_id),
            max_repair_attempts=2,
            max_tokens=4000,  # Ensure enough tokens for full response
        )

        LOGGER.info(
            "[decomposer] Decomposed mission '%s' into %d phases, %d total weeks",
            result.title,
            len(result.phases),
            sum(p.duration_weeks for p in result.phases),
        )

        return result

    except Exception as e:
        LOGGER.exception("[decomposer] Mission decomposition failed: %s", e)
        raise


async def decompose_first_week(
    mission_title: str,
    mission_description: str,
    phase_objective: str,
    person_id: UUID,
    context: Optional[Dict[str, Any]] = None,
) -> WeekPlan:
    """
    Generate detailed plan for just the first week.

    Use this for immediate actionability - plan the first week in detail,
    leave later weeks at higher level.

    Args:
        mission_title: Title of the mission
        mission_description: Full description
        phase_objective: Objective of the current phase
        person_id: User ID
        context: Additional context

    Returns:
        Detailed WeekPlan with specific actions
    """
    prompt = f"""You are Sakhi, a life companion AI helping plan the first week of a mission.

MISSION: {mission_title}
DESCRIPTION: {mission_description}
CURRENT PHASE OBJECTIVE: {phase_objective}

Create a detailed plan for WEEK 1 only. This week should:
1. Build momentum with achievable wins
2. Establish habits and routines that will compound
3. Include specific, time-bound actions
4. Not overwhelm - 2-4 meaningful actions per day max

For each action, specify:
- action_type: "research", "create", "review", "outreach", "learn", "practice", "analyze"
- description: Specific task description
- scheduled_day: "monday", "tuesday", etc.
- scheduled_time: Optional "HH:MM" format (24h)
- instructions: Optional dict with any specific details needed to execute

Context:
{json.dumps(context or {}, indent=2)}

Return a JSON object matching this schema:
{{
    "week_number": 1,
    "objectives": ["list of 2-4 objectives for this week"],
    "actions": [
        {{
            "action_type": "string",
            "description": "specific task",
            "scheduled_day": "monday",
            "scheduled_time": "09:00",
            "instructions": {{"key": "value"}}
        }}
    ]
}}

Make the actions specific and actionable. Include realistic times.
Return ONLY the JSON."""

    try:
        result = await call_llm(
            prompt=prompt,
            schema=WeekPlan,
            person_id=str(person_id),
            max_repair_attempts=2,
        )
        return result

    except Exception as e:
        LOGGER.exception("[decomposer] First week decomposition failed: %s", e)
        raise


async def suggest_next_actions(
    mission_id: UUID,
    recent_outcomes: List[Dict[str, Any]],
    current_metrics: Dict[str, Any],
    person_id: UUID,
) -> List[ActionPlan]:
    """
    Suggest next actions based on recent outcomes.

    Uses mission progress and learnings to suggest adaptive next steps.
    Called during weekly reviews or when user asks "what should I do next?"

    Args:
        mission_id: Current mission
        recent_outcomes: Results of recent actions
        current_metrics: Current mission metrics
        person_id: User ID

    Returns:
        List of suggested ActionPlans
    """
    prompt = f"""Based on recent progress, suggest 3-5 next actions.

RECENT OUTCOMES:
{json.dumps(recent_outcomes[-5:], indent=2)}

CURRENT METRICS:
{json.dumps(current_metrics, indent=2)}

Consider:
1. What's working well - do more of it
2. What's not working - adjust or drop
3. What's the next logical step
4. Any quick wins available

Return a JSON array of actions:
[
    {{
        "action_type": "string",
        "description": "specific task",
        "scheduled_day": "string (monday-sunday)",
        "scheduled_time": "HH:MM" (optional),
        "instructions": {{}} (optional)
    }}
]

Return ONLY the JSON array."""

    try:
        from pydantic import BaseModel, RootModel

        class ActionList(RootModel):
            root: List[ActionPlan]

        result = await call_llm(
            prompt=prompt,
            schema=ActionList,
            person_id=str(person_id),
            max_repair_attempts=2,
        )
        return result.root

    except Exception as e:
        LOGGER.exception("[decomposer] Next actions suggestion failed: %s", e)
        return []


def calculate_action_dates(
    actions: List[ActionPlan],
    week_start: date,
) -> List[Dict[str, Any]]:
    """
    Convert day names to actual dates for scheduling.

    Args:
        actions: List of ActionPlan with scheduled_day
        week_start: Monday of the target week

    Returns:
        List of dicts with action data and calculated dates
    """
    result = []

    for action in actions:
        day_name = action.scheduled_day.lower()
        offset = DAY_OFFSETS.get(day_name, 0)
        scheduled_date = week_start + timedelta(days=offset)

        result.append({
            "action_type": action.action_type,
            "description": action.description,
            "scheduled_date": scheduled_date,
            "scheduled_time": action.scheduled_time,
            "instructions": action.instructions,
        })

    return result


def _build_decomposition_prompt(
    goal: str,
    category: Optional[MissionCategory],
    context: Optional[Dict[str, Any]],
    target_weeks: int,
) -> str:
    """Build the prompt for mission decomposition."""

    category_hint = ""
    if category:
        category_examples = {
            MissionCategory.CAREER: "job search, skill building, networking, side projects",
            MissionCategory.HEALTH: "fitness, nutrition, sleep, mental health",
            MissionCategory.LEARNING: "courses, certifications, skills acquisition",
            MissionCategory.CREATIVE: "writing, art, music, content creation",
            MissionCategory.RELATIONSHIPS: "networking, dating, family, friendships",
            MissionCategory.FINANCE: "budgeting, saving, investing, debt reduction",
        }
        category_hint = f"\nCategory hint: {category.value} ({category_examples.get(category, '')})"

    context_section = ""
    if context:
        context_section = f"\nUser context:\n{json.dumps(context, indent=2)}"

    return f"""You are Sakhi, a life companion AI. Decompose this goal into an actionable mission plan.

GOAL: {goal}
{category_hint}
{context_section}

TARGET DURATION: {target_weeks} weeks

Create a structured plan with:

1. PHASES (2-4 phases, each 2-4 weeks)
   - Each phase has a clear objective and approval gate
   - Phase 1 focuses on foundation/learning
   - Later phases build complexity

2. WEEKLY PLANS (within each phase)
   - 2-4 concrete objectives per week
   - Specific actions tied to days

3. ACTIONS (per week)
   - Specific, time-bound tasks
   - Realistic scheduling (2-4 meaningful actions per day max)
   - Include action_type: "research", "create", "review", "outreach", "learn", "practice", "analyze"

4. SUCCESS CRITERIA
   - Measurable outcomes
   - Both leading indicators (activities) and lagging indicators (results)

5. PLAN DOCUMENT
   - A markdown document summarizing the full plan
   - Easy to read and reference

Return a JSON object:
{{
    "title": "mission title (clear, motivating)",
    "description": "1-2 sentence description",
    "category": "career|health|learning|creative|relationships|finance",
    "success_criteria": {{
        "primary": "main outcome",
        "metrics": ["measurable indicator 1", "measurable indicator 2"],
        "milestones": ["milestone 1", "milestone 2"]
    }},
    "target_weeks": {target_weeks},
    "phases": [
        {{
            "phase_number": 1,
            "name": "phase name",
            "objective": "what this phase accomplishes",
            "duration_weeks": 2,
            "expected_outcomes": ["outcome 1", "outcome 2"],
            "weeks": [
                {{
                    "week_number": 1,
                    "objectives": ["week objective 1", "week objective 2"],
                    "actions": [
                        {{
                            "action_type": "research",
                            "description": "specific task",
                            "scheduled_day": "monday",
                            "scheduled_time": "09:00",
                            "instructions": {{}}
                        }}
                    ]
                }}
            ]
        }}
    ],
    "plan_document": "# Mission: Title\\n\\n## Overview\\n...markdown content..."
}}

Important:
- Be specific and actionable
- Include realistic time estimates
- Don't overwhelm - sustainable progress > burnout
- Week 1 should have immediate, achievable wins

Return ONLY the JSON."""


async def generate_plan_document(
    decomposition: MissionDecomposition,
) -> str:
    """
    Generate a human-readable markdown plan document.

    This creates a nicely formatted document that users can reference
    and that gets stored in the mission's plan_document field.
    """
    lines = [
        f"# Mission: {decomposition.title}",
        "",
        f"**Category:** {decomposition.category.value}",
        f"**Duration:** {decomposition.target_weeks} weeks",
        "",
        "## Description",
        decomposition.description,
        "",
        "## Success Criteria",
    ]

    criteria = decomposition.success_criteria
    if isinstance(criteria, dict):
        if "primary" in criteria:
            lines.append(f"**Primary Goal:** {criteria['primary']}")
        if "metrics" in criteria:
            lines.append("\n**Metrics:**")
            for m in criteria["metrics"]:
                lines.append(f"- {m}")
        if "milestones" in criteria:
            lines.append("\n**Milestones:**")
            for m in criteria["milestones"]:
                lines.append(f"- [ ] {m}")

    lines.append("")
    lines.append("---")
    lines.append("")

    for phase in decomposition.phases:
        lines.append(f"## Phase {phase.phase_number}: {phase.name}")
        lines.append(f"*Duration: {phase.duration_weeks} weeks*")
        lines.append("")
        lines.append(f"**Objective:** {phase.objective}")
        lines.append("")
        lines.append("**Expected Outcomes:**")
        for outcome in phase.expected_outcomes:
            lines.append(f"- {outcome}")
        lines.append("")

        for week in phase.weeks:
            lines.append(f"### Week {week.week_number}")
            lines.append("**Objectives:**")
            for obj in week.objectives:
                lines.append(f"- {obj}")
            lines.append("")
            lines.append("**Actions:**")

            # Group by day
            by_day: Dict[str, List[ActionPlan]] = {}
            for action in week.actions:
                day = action.scheduled_day.capitalize()
                if day not in by_day:
                    by_day[day] = []
                by_day[day].append(action)

            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for day in day_order:
                if day in by_day:
                    lines.append(f"\n*{day}:*")
                    for action in by_day[day]:
                        time_str = f" ({action.scheduled_time})" if action.scheduled_time else ""
                        lines.append(f"- [ ] {action.description}{time_str}")

            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "decompose_mission",
    "decompose_first_week",
    "suggest_next_actions",
    "calculate_action_dates",
    "generate_plan_document",
]
