"""
Task Planner Service
--------------------
Plan and execute multi-step tasks for Sakhi.
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PLANNING = "planning"
    PENDING_APPROVAL = "pending_approval"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStep(BaseModel):
    """A single step in a task plan."""
    step: int
    action: str  # Tool name or special action
    parameters: Dict[str, Any] = {}
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    depends_on: List[int] = []  # Step numbers this depends on


class TaskPlan(BaseModel):
    """A multi-step task execution plan."""
    id: str
    person_id: str
    task_description: str
    goal: str
    steps: List[TaskStep] = []
    current_step: int = 0
    status: TaskStatus = TaskStatus.PLANNING
    results: Dict[str, Any] = {}
    final_output: Optional[str] = None
    session_id: Optional[str] = None


async def create_task_plan(
    person_id: str,
    task_description: str,
    session_id: Optional[str] = None,
    auto_approve: bool = False,
) -> TaskPlan:
    """
    Create a plan for a task.

    Uses LLM to break down task into steps.
    """
    from sakhi.apps.api.core.llm import get_router
    from sakhi.apps.api.services.agentic.tools import get_available_tools

    # Get available tools
    tools = await get_available_tools(person_id)
    tool_descriptions = "\n".join([
        f"- {t.tool_name}: {t.description}"
        for t in tools
    ])

    # Plan the task
    prompt = f"""You are a task planner. Break down this task into executable steps.

Task: {task_description}

Available Tools:
{tool_descriptions}

Special Actions:
- respond: Provide a response to the user
- synthesize: Combine results from previous steps

Create a JSON plan with steps. Each step should have:
- step: Step number (1, 2, 3...)
- action: Tool name or special action
- parameters: Parameters for the action
- description: What this step does
- depends_on: List of step numbers this depends on (empty for first steps)

Example:
{{
    "goal": "Brief description of what we're trying to achieve",
    "steps": [
        {{"step": 1, "action": "web_search", "parameters": {{"query": "..."}}, "description": "Search for...", "depends_on": []}},
        {{"step": 2, "action": "summarize", "parameters": {{"text": "step_1_result"}}, "description": "Summarize findings", "depends_on": [1]}},
        {{"step": 3, "action": "respond", "parameters": {{"content": "synthesis"}}, "description": "Provide answer", "depends_on": [2]}}
    ]
}}

Return ONLY valid JSON."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
        )

        content = response.content[0].text if response.content else "{}"

        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        plan_data = json.loads(content.strip())

        # Build steps
        steps = []
        for s in plan_data.get("steps", []):
            steps.append(TaskStep(
                step=s.get("step", len(steps) + 1),
                action=s.get("action", "respond"),
                parameters=s.get("parameters", {}),
                description=s.get("description", ""),
                depends_on=s.get("depends_on", []),
            ))

        if not steps:
            # Fallback: simple single-step plan
            steps = [TaskStep(
                step=1,
                action="respond",
                parameters={"content": task_description},
                description="Respond to user request",
            )]

        goal = plan_data.get("goal", task_description[:100])

    except Exception as e:
        LOGGER.error("[planner] Planning failed: %s", e)
        # Fallback plan
        goal = task_description[:100]
        steps = [TaskStep(
            step=1,
            action="respond",
            parameters={"content": f"I'll help with: {task_description}"},
            description="Acknowledge request",
        )]

    # Save to database
    row = await dbfetch(
        """
        INSERT INTO task_plans (
            person_id, session_id, task_description, goal, steps, status
        )
        VALUES ($1, $2, $3, $4, $5::jsonb, $6)
        RETURNING id, created_at
        """,
        person_id,
        session_id,
        task_description,
        goal,
        json.dumps([s.model_dump() for s in steps]),
        TaskStatus.PENDING_APPROVAL.value if not auto_approve else TaskStatus.EXECUTING.value,
        one=True,
    )

    plan = TaskPlan(
        id=str(row["id"]),
        person_id=person_id,
        task_description=task_description,
        goal=goal,
        steps=steps,
        status=TaskStatus.PENDING_APPROVAL if not auto_approve else TaskStatus.EXECUTING,
        session_id=session_id,
    )

    LOGGER.info("[planner] Created plan %s with %d steps", plan.id, len(steps))

    # Auto-execute if approved
    if auto_approve:
        plan = await execute_task_plan(plan.id, person_id)

    return plan


async def get_task_plan(plan_id: str) -> Optional[TaskPlan]:
    """Get a task plan by ID."""
    row = await dbfetch(
        "SELECT * FROM task_plans WHERE id = $1",
        plan_id,
        one=True,
    )

    if not row:
        return None

    steps = [TaskStep(**s) for s in (row.get("steps") or [])]

    return TaskPlan(
        id=str(row["id"]),
        person_id=row["person_id"],
        task_description=row["task_description"],
        goal=row["goal"],
        steps=steps,
        current_step=row.get("current_step", 0),
        status=TaskStatus(row["status"]),
        results=row.get("results") or {},
        final_output=row.get("final_output"),
        session_id=row.get("session_id"),
    )


async def approve_task_plan(plan_id: str, person_id: str) -> Optional[TaskPlan]:
    """Approve a task plan for execution."""
    await dbexec(
        """
        UPDATE task_plans
        SET status = 'executing',
            approved_at = NOW(),
            started_at = NOW()
        WHERE id = $1 AND person_id = $2 AND status = 'pending_approval'
        """,
        plan_id,
        person_id,
    )

    return await execute_task_plan(plan_id, person_id)


async def cancel_task_plan(plan_id: str, person_id: str) -> bool:
    """Cancel a task plan."""
    await dbexec(
        """
        UPDATE task_plans
        SET status = 'cancelled', updated_at = NOW()
        WHERE id = $1 AND person_id = $2
        """,
        plan_id,
        person_id,
    )
    return True


async def execute_task_plan(
    plan_id: str,
    person_id: str,
) -> TaskPlan:
    """
    Execute a task plan step by step.

    Returns updated plan with results.
    """
    from sakhi.apps.api.services.agentic.tools import execute_tool

    plan = await get_task_plan(plan_id)
    if not plan:
        raise ValueError(f"Plan not found: {plan_id}")

    if plan.status not in (TaskStatus.EXECUTING, TaskStatus.PENDING_APPROVAL):
        return plan

    # Update status to executing
    await dbexec(
        "UPDATE task_plans SET status = 'executing', started_at = COALESCE(started_at, NOW()) WHERE id = $1",
        plan_id,
    )

    results: Dict[str, Any] = plan.results.copy()

    for step in plan.steps:
        if step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED):
            continue

        # Check dependencies
        deps_satisfied = all(
            results.get(f"step_{dep}") is not None
            for dep in step.depends_on
        )

        if not deps_satisfied:
            LOGGER.warning("[planner] Step %d dependencies not satisfied", step.step)
            continue

        # Update step status
        step.status = StepStatus.EXECUTING
        await _update_plan_steps(plan_id, plan.steps, step.step)

        try:
            # Resolve parameters (replace step references with actual results)
            resolved_params = _resolve_parameters(step.parameters, results)

            if step.action == "respond":
                # Special action: generate response
                result = await _generate_response(
                    resolved_params.get("content", ""),
                    results,
                    plan.task_description,
                )
                step.result = result
                step.status = StepStatus.COMPLETED

            elif step.action == "synthesize":
                # Special action: combine results
                result = await _synthesize_results(results, plan.goal)
                step.result = result
                step.status = StepStatus.COMPLETED

            else:
                # Execute tool
                tool_result = await execute_tool(
                    person_id=person_id,
                    tool_name=step.action,
                    parameters=resolved_params,
                    task_plan_id=plan_id,
                    skip_approval_check=True,  # Plan was approved
                )

                if tool_result.success:
                    step.result = tool_result.result
                    step.status = StepStatus.COMPLETED
                else:
                    step.error = tool_result.error
                    step.status = StepStatus.FAILED

            results[f"step_{step.step}"] = step.result

        except Exception as e:
            LOGGER.error("[planner] Step %d failed: %s", step.step, e)
            step.error = str(e)
            step.status = StepStatus.FAILED

        # Update plan after each step
        await _update_plan_steps(plan_id, plan.steps, step.step)

    # Determine final status
    all_completed = all(
        s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        for s in plan.steps
    )
    any_failed = any(s.status == StepStatus.FAILED for s in plan.steps)

    if all_completed:
        final_status = TaskStatus.COMPLETED
        # Get final output from last step
        last_step = plan.steps[-1]
        final_output = last_step.result if isinstance(last_step.result, str) else json.dumps(last_step.result)
    elif any_failed:
        final_status = TaskStatus.FAILED
        final_output = None
    else:
        final_status = TaskStatus.PAUSED
        final_output = None

    # Update plan
    await dbexec(
        """
        UPDATE task_plans
        SET status = $2,
            results = $3::jsonb,
            final_output = $4,
            completed_at = CASE WHEN $2 IN ('completed', 'failed') THEN NOW() ELSE NULL END,
            updated_at = NOW()
        WHERE id = $1
        """,
        plan_id,
        final_status.value,
        json.dumps(results),
        final_output,
    )

    plan.status = final_status
    plan.results = results
    plan.final_output = final_output

    LOGGER.info("[planner] Plan %s completed with status: %s", plan_id, final_status.value)

    return plan


def _resolve_parameters(
    parameters: Dict[str, Any],
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """Replace step references in parameters with actual results."""
    resolved = {}

    for key, value in parameters.items():
        if isinstance(value, str):
            # Check for step references like "step_1_result"
            if value.startswith("step_") and value.endswith("_result"):
                step_num = value.replace("step_", "").replace("_result", "")
                resolved[key] = results.get(f"step_{step_num}")
            elif value == "synthesis":
                # Use all results
                resolved[key] = results
            else:
                resolved[key] = value
        else:
            resolved[key] = value

    return resolved


async def _update_plan_steps(
    plan_id: str,
    steps: List[TaskStep],
    current_step: int,
) -> None:
    """Update plan steps in database."""
    await dbexec(
        """
        UPDATE task_plans
        SET steps = $2::jsonb,
            current_step = $3,
            updated_at = NOW()
        WHERE id = $1
        """,
        plan_id,
        json.dumps([s.model_dump() for s in steps]),
        current_step,
    )


async def _generate_response(
    content_hint: str,
    results: Dict[str, Any],
    task: str,
) -> str:
    """Generate a response based on task results."""
    from sakhi.apps.api.core.llm import get_router

    # Summarize results
    results_text = json.dumps(results, indent=2, default=str)[:3000]

    prompt = f"""Based on the task and results, generate a helpful response.

Task: {task}
Results from steps:
{results_text}

Provide a clear, helpful response that answers the user's request.
Be concise but complete. Include relevant details from the results."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-20250514",
            max_tokens=500,
        )
        return response.content[0].text if response.content else "Task completed."
    except Exception as e:
        LOGGER.error("[planner] Response generation failed: %s", e)
        return f"Task completed. Results: {content_hint}"


async def _synthesize_results(
    results: Dict[str, Any],
    goal: str,
) -> str:
    """Synthesize results from multiple steps."""
    from sakhi.apps.api.core.llm import get_router

    results_text = json.dumps(results, indent=2, default=str)[:3000]

    prompt = f"""Synthesize these results into a coherent answer.

Goal: {goal}
Results:
{results_text}

Provide a well-organized summary that addresses the goal."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-20250514",
            max_tokens=500,
        )
        return response.content[0].text if response.content else "See results above."
    except Exception as e:
        LOGGER.error("[planner] Synthesis failed: %s", e)
        return "Results gathered successfully."


async def get_active_plans(person_id: str) -> List[TaskPlan]:
    """Get active task plans for a user."""
    rows = await dbfetch(
        """
        SELECT * FROM task_plans
        WHERE person_id = $1
          AND status IN ('planning', 'pending_approval', 'executing', 'paused')
        ORDER BY created_at DESC
        LIMIT 10
        """,
        person_id,
    )

    return [
        TaskPlan(
            id=str(row["id"]),
            person_id=row["person_id"],
            task_description=row["task_description"],
            goal=row["goal"],
            steps=[TaskStep(**s) for s in (row.get("steps") or [])],
            current_step=row.get("current_step", 0),
            status=TaskStatus(row["status"]),
            results=row.get("results") or {},
            final_output=row.get("final_output"),
            session_id=row.get("session_id"),
        )
        for row in (rows or [])
    ]


__all__ = [
    "TaskStatus",
    "StepStatus",
    "TaskStep",
    "TaskPlan",
    "create_task_plan",
    "get_task_plan",
    "approve_task_plan",
    "cancel_task_plan",
    "execute_task_plan",
    "get_active_plans",
]
