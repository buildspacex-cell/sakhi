"""
Task Orchestrator
-----------------
The central coordinator that connects preferences, memory, and vision loop
for intelligent, preference-aware autonomous execution.

This is what makes Sakhi "smart" - it doesn't just execute tasks blindly,
it understands WHO you are (via memory) and WHAT you like (via preferences)
to make decisions that truly match you.

Example: "Find me the best running shoes on Amazon"
1. Recalls: You had knee pain, prefer cushioned shoes, run 3x/week
2. Gets preferences: Temperature hot areas (breathable), firm support preferred
3. Plans: Search Amazon → Filter cushioned → Check breathability → Compare reviews
4. Executes: Vision loop browses with these constraints in mind
5. Returns: Shoes that match YOUR needs, not just "best sellers"

This is the "planner + executor" that gives Sakhi multi-hop reasoning.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Task Planning Models
# =============================================================================

class TaskType(str, Enum):
    """Types of tasks Sakhi can orchestrate."""
    SHOPPING = "shopping"  # Find/purchase products
    RESEARCH = "research"  # Gather information
    BOOKING = "booking"  # Reserve/book something
    BROWSING = "browsing"  # General web navigation
    FOOD = "food"  # Restaurant/food ordering
    CUSTOM = "custom"  # General task


class TaskStep(BaseModel):
    """A single step in a task plan."""
    step_number: int
    action: str  # What to do
    description: str  # Human-readable description
    success_criteria: str  # How to know it's done
    fallback: Optional[str] = None  # What to do if it fails
    depends_on: Optional[int] = None  # Previous step dependency
    estimated_actions: int = 3  # Estimated vision loop actions


class TaskPlan(BaseModel):
    """Complete plan for executing a task."""
    task_id: str
    task_type: TaskType
    original_request: str
    steps: List[TaskStep]
    total_estimated_actions: int
    context_summary: str  # Summary of preferences/memory used
    constraints: List[str]  # Things to avoid/ensure
    success_criteria: str  # How we know the whole task is done
    created_at: datetime = datetime.utcnow()


class TaskStatus(str, Enum):
    """Status of an orchestrated task."""
    PLANNING = "planning"
    GATHERING_CONTEXT = "gathering_context"
    READY = "ready"
    EXECUTING = "executing"
    STEP_COMPLETE = "step_complete"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResult(BaseModel):
    """Result of an orchestrated task."""
    task_id: str
    status: TaskStatus
    plan: Optional[TaskPlan] = None
    steps_completed: int = 0
    current_step: int = 0
    results: Dict[str, Any] = {}
    errors: List[str] = []
    context_used: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# =============================================================================
# Task Orchestrator
# =============================================================================

class TaskOrchestrator:
    """
    Orchestrates preference-aware autonomous task execution.

    This is the "brain" that connects:
    - Memory (what Sakhi knows about you)
    - Preferences (how you experience things)
    - Vision Loop (autonomous browsing)
    - Planning (multi-step reasoning)

    Example:
        orchestrator = TaskOrchestrator(person_id="123", agent_id="456")
        result = await orchestrator.execute(
            "Find me a good birthday gift for Mom under $50"
        )
    """

    def __init__(
        self,
        person_id: str,
        agent_id: str,
        *,
        max_steps: int = 10,
        max_actions_per_step: int = 20,
        on_step_complete: Optional[Callable[[int, Dict], None]] = None,
        on_status_change: Optional[Callable[[TaskStatus], None]] = None,
    ):
        self.person_id = person_id
        self.agent_id = agent_id
        self.max_steps = max_steps
        self.max_actions_per_step = max_actions_per_step

        # Callbacks
        self.on_step_complete = on_step_complete
        self.on_status_change = on_status_change

        # State
        self.current_task: Optional[TaskResult] = None
        self._running = False

    async def execute(
        self,
        task_description: str,
        *,
        starting_url: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute a task with full preference and memory awareness.

        This is the main entry point. It:
        1. Gathers context (preferences, relevant memories)
        2. Plans the task (multi-step decomposition)
        3. Executes each step via vision loop
        4. Returns comprehensive results

        Args:
            task_description: What the user wants (natural language)
            starting_url: Optional URL to start at
            additional_context: Extra context to consider

        Returns:
            TaskResult with status, results, and execution details
        """
        import uuid

        task_id = str(uuid.uuid4())[:8]

        LOGGER.info(
            "[orchestrator] Starting task %s: %s",
            task_id,
            task_description[:100],
        )

        self.current_task = TaskResult(
            task_id=task_id,
            status=TaskStatus.GATHERING_CONTEXT,
            started_at=datetime.utcnow(),
        )
        self._running = True
        self._update_status(TaskStatus.GATHERING_CONTEXT)

        try:
            # Step 1: Gather context (preferences + memories)
            context = await self._gather_context(task_description)
            self.current_task.context_used = context

            # Step 2: Plan the task
            self._update_status(TaskStatus.PLANNING)
            plan = await self._plan_task(task_description, context)
            self.current_task.plan = plan

            # Step 3: Execute each step
            self._update_status(TaskStatus.EXECUTING)

            for step in plan.steps:
                if not self._running:
                    self._update_status(TaskStatus.CANCELLED)
                    break

                self.current_task.current_step = step.step_number

                step_result = await self._execute_step(
                    step=step,
                    context=context,
                    starting_url=starting_url if step.step_number == 1 else None,
                )

                self.current_task.steps_completed += 1
                self.current_task.results[f"step_{step.step_number}"] = step_result

                if self.on_step_complete:
                    self.on_step_complete(step.step_number, step_result)

                # Check if step failed
                if step_result.get("status") == "failed":
                    if step.fallback:
                        LOGGER.info("[orchestrator] Step %d failed, trying fallback", step.step_number)
                        # Could implement fallback execution here
                    else:
                        self.current_task.errors.append(
                            f"Step {step.step_number} failed: {step_result.get('error')}"
                        )
                        self._update_status(TaskStatus.FAILED)
                        break

            # Mark complete only if all steps finished AND status is still EXECUTING
            # (Don't override FAILED or CANCELLED status)
            if (
                self.current_task.steps_completed == len(plan.steps)
                and self.current_task.status == TaskStatus.EXECUTING
            ):
                self._update_status(TaskStatus.COMPLETED)

            self.current_task.completed_at = datetime.utcnow()

        except Exception as e:
            LOGGER.exception("[orchestrator] Task %s failed: %s", task_id, e)
            self.current_task.errors.append(str(e))
            self._update_status(TaskStatus.FAILED)

        finally:
            self._running = False

        return self.current_task

    async def cancel(self) -> None:
        """Cancel the current task."""
        self._running = False
        if self.current_task:
            self._update_status(TaskStatus.CANCELLED)

    def _update_status(self, status: TaskStatus) -> None:
        """Update task status and trigger callback."""
        if self.current_task:
            self.current_task.status = status
        if self.on_status_change:
            self.on_status_change(status)

    # -------------------------------------------------------------------------
    # Context Gathering
    # -------------------------------------------------------------------------

    async def _gather_context(self, task_description: str) -> Dict[str, Any]:
        """
        Gather all relevant context for the task.

        This pulls:
        - Sensory preferences (temperature, texture, etc.)
        - Food memory (if relevant)
        - General memories via hybrid search
        - Relationship context (if relevant)
        """
        context = {
            "task": task_description,
            "preferences": {},
            "memories": [],
            "food_context": {},
            "constraints": [],
        }

        # Get sensory profile
        try:
            from sakhi.apps.api.services.memory.sensory_preferences import (
                get_sensory_profile,
                get_dining_sensory_context,
            )

            profile = await get_sensory_profile(self.person_id)
            if profile:
                context["preferences"]["sensory"] = profile.to_dict() if hasattr(profile, 'to_dict') else profile
        except Exception as e:
            LOGGER.warning("[orchestrator] Failed to get sensory profile: %s", e)

        # Get food context if food-related
        if any(word in task_description.lower() for word in ["food", "restaurant", "eat", "dinner", "lunch", "breakfast", "order"]):
            try:
                from sakhi.apps.api.services.memory.food_memory import (
                    get_food_context_for_recommendations,
                    get_recent_meals,
                )

                food_ctx = await get_food_context_for_recommendations(self.person_id)
                if food_ctx:
                    context["food_context"] = food_ctx

                # Add constraint: avoid recent meals
                recent = await get_recent_meals(self.person_id, days=3)
                if recent:
                    recent_dishes = [m.get("dish_name") for m in recent if m.get("dish_name")]
                    if recent_dishes:
                        context["constraints"].append(f"Recently ate: {', '.join(recent_dishes)}")
            except Exception as e:
                LOGGER.warning("[orchestrator] Failed to get food context: %s", e)

        # Recall relevant memories via hybrid search
        try:
            from sakhi.apps.api.services.memory.recall import recall_advanced

            memories = await recall_advanced(
                person_id=self.person_id,
                query=task_description,
                k=10,
            )

            # Filter to most relevant
            context["memories"] = [
                {
                    "content": m.get("content", ""),
                    "source": m.get("source", ""),
                    "relevance": m.get("score", 0),
                }
                for m in memories[:5]  # Top 5
                if m.get("score", 0) > 0.3  # Above threshold
            ]
        except Exception as e:
            LOGGER.warning("[orchestrator] Failed to recall memories: %s", e)

        # Extract preference constraints from memories
        context["constraints"].extend(
            self._extract_constraints_from_context(context)
        )

        LOGGER.info(
            "[orchestrator] Gathered context: %d memories, %d constraints",
            len(context["memories"]),
            len(context["constraints"]),
        )

        return context

    def _extract_constraints_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Extract actionable constraints from gathered context."""
        constraints = []

        # From sensory preferences
        sensory = context.get("preferences", {}).get("sensory")
        if sensory:
            # sensory might be a SensoryProfile Pydantic model or a dict
            # Handle both cases
            if hasattr(sensory, "spice"):
                # It's a SensoryProfile model
                spice_data = sensory.spice or {}
                temp_data = sensory.temperature or {}
                if spice_data.get("tolerance") == "low":
                    constraints.append("User has low spice tolerance")
                if temp_data.get("preference") == "cold":
                    constraints.append("User prefers cold items/environments")
            elif isinstance(sensory, dict):
                # It's a dictionary
                if sensory.get("spice_tolerance") == "low":
                    constraints.append("User has low spice tolerance")
                if sensory.get("temperature_preference") == "cold":
                    constraints.append("User prefers cold items/environments")

        # From food context
        food_ctx = context.get("food_context", {})
        if food_ctx.get("dietary_restrictions"):
            constraints.append(f"Dietary restrictions: {', '.join(food_ctx['dietary_restrictions'])}")
        if food_ctx.get("allergies"):
            constraints.append(f"Allergies: {', '.join(food_ctx['allergies'])}")

        # From memories
        for memory in context.get("memories", []):
            content = memory.get("content", "").lower()

            # Look for preference patterns
            if "don't like" in content or "hate" in content:
                # Extract what they don't like
                constraints.append(f"May not like: {memory['content'][:50]}")

            if "allergic to" in content:
                constraints.append(f"Allergy warning: {memory['content'][:50]}")

        return constraints

    # -------------------------------------------------------------------------
    # Task Planning
    # -------------------------------------------------------------------------

    async def _plan_task(
        self,
        task_description: str,
        context: Dict[str, Any],
    ) -> TaskPlan:
        """
        Create a multi-step plan for the task.

        Uses Claude to decompose the task into actionable steps,
        considering the gathered context.
        """
        import uuid
        import json
        from sakhi.apps.api.core.llm import get_router

        # Determine task type
        task_type = self._classify_task(task_description)

        prompt = self._build_planning_prompt(task_description, context, task_type)

        try:
            import os
            router = get_router()

            # Use configured chat model
            target_model = os.getenv("MODEL_CHAT") or "openrouter/chat"
            response = await router.chat(
                messages=[{"role": "user", "content": prompt}],
                model=target_model,
                max_tokens=2000,
            )

            # Handle both OpenAI and Anthropic response formats
            if hasattr(response, 'content') and response.content:
                # Anthropic format
                content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            elif hasattr(response, 'choices') and response.choices:
                # OpenAI format
                content = response.choices[0].message.content or "{}"
            else:
                content = "{}"
            plan_data = self._parse_json_response(content)

            # Build TaskPlan from response
            steps = []
            for i, step_data in enumerate(plan_data.get("steps", []), 1):
                steps.append(TaskStep(
                    step_number=i,
                    action=step_data.get("action", ""),
                    description=step_data.get("description", ""),
                    success_criteria=step_data.get("success_criteria", ""),
                    fallback=step_data.get("fallback"),
                    depends_on=step_data.get("depends_on"),
                    estimated_actions=step_data.get("estimated_actions", 3),
                ))

            # If no steps from Claude, create a basic plan
            if not steps:
                steps = [TaskStep(
                    step_number=1,
                    action="execute",
                    description=task_description,
                    success_criteria="Task completed",
                    estimated_actions=10,
                )]

            plan = TaskPlan(
                task_id=str(uuid.uuid4())[:8],
                task_type=task_type,
                original_request=task_description,
                steps=steps,
                total_estimated_actions=sum(s.estimated_actions for s in steps),
                context_summary=plan_data.get("context_summary", ""),
                constraints=context.get("constraints", []) + plan_data.get("constraints", []),
                success_criteria=plan_data.get("success_criteria", "Task completed"),
            )

            LOGGER.info(
                "[orchestrator] Created plan with %d steps for task type %s",
                len(steps),
                task_type.value,
            )

            return plan

        except Exception as e:
            LOGGER.exception("[orchestrator] Planning failed: %s", e)
            # Return a simple fallback plan
            return TaskPlan(
                task_id=str(uuid.uuid4())[:8],
                task_type=task_type,
                original_request=task_description,
                steps=[TaskStep(
                    step_number=1,
                    action="execute",
                    description=task_description,
                    success_criteria="Task completed",
                    estimated_actions=20,
                )],
                total_estimated_actions=20,
                context_summary="",
                constraints=context.get("constraints", []),
                success_criteria="Task completed",
            )

    def _classify_task(self, task_description: str) -> TaskType:
        """Classify the task type."""
        desc_lower = task_description.lower()

        if any(word in desc_lower for word in ["buy", "purchase", "order", "shop", "amazon", "find product"]):
            return TaskType.SHOPPING

        if any(word in desc_lower for word in ["restaurant", "food", "eat", "dinner", "lunch", "breakfast", "dine"]):
            return TaskType.FOOD

        if any(word in desc_lower for word in ["book", "reserve", "reservation", "appointment"]):
            return TaskType.BOOKING

        if any(word in desc_lower for word in ["research", "find out", "learn about", "what is"]):
            return TaskType.RESEARCH

        return TaskType.BROWSING

    def _build_planning_prompt(
        self,
        task_description: str,
        context: Dict[str, Any],
        task_type: TaskType,
    ) -> str:
        """Build the planning prompt."""
        import json

        prompt = f"""You are Sakhi, an AI assistant planning an autonomous task for the user.

TASK: {task_description}
TASK TYPE: {task_type.value}

USER CONTEXT:
"""

        if context.get("preferences", {}).get("sensory"):
            sensory = context['preferences']['sensory']
            # Convert Pydantic model to dict if needed
            if hasattr(sensory, 'model_dump'):
                sensory = sensory.model_dump()
            elif hasattr(sensory, 'dict'):
                sensory = sensory.dict()
            prompt += f"Sensory Preferences: {json.dumps(sensory, indent=2, default=str)}\n"

        if context.get("food_context"):
            food_ctx = context['food_context']
            # Convert Pydantic model to dict if needed
            if hasattr(food_ctx, 'model_dump'):
                food_ctx = food_ctx.model_dump()
            elif hasattr(food_ctx, 'dict'):
                food_ctx = food_ctx.dict()
            prompt += f"Food Context: {json.dumps(food_ctx, indent=2, default=str)}\n"

        if context.get("memories"):
            prompt += f"Relevant Memories:\n"
            for m in context["memories"]:
                prompt += f"  - {m['content'][:100]}\n"

        if context.get("constraints"):
            prompt += f"Constraints to Consider:\n"
            for c in context["constraints"]:
                prompt += f"  - {c}\n"

        prompt += f"""
Create a step-by-step plan to accomplish this task. Each step should be:
- Specific and actionable
- Have clear success criteria
- Consider the user's preferences and constraints

For a {task_type.value} task, typical steps might include:
"""

        if task_type == TaskType.SHOPPING:
            prompt += """
1. Navigate to the shopping site
2. Search for the product
3. Apply filters based on user preferences
4. Compare options
5. Select the best match
6. Add to cart / initiate purchase
"""
        elif task_type == TaskType.FOOD:
            prompt += """
1. Open a restaurant finder (Google, Yelp, etc.)
2. Search with location and cuisine criteria
3. Filter by user preferences (price, dietary, etc.)
4. Review options considering user's food history
5. Select and verify restaurant details
6. Initiate booking if needed
"""
        elif task_type == TaskType.BOOKING:
            prompt += """
1. Navigate to the booking site
2. Enter search criteria
3. Filter results by preferences
4. Compare options
5. Select and verify details
6. Complete booking
"""

        prompt += """
Respond with JSON:
{
    "steps": [
        {
            "action": "navigate|search|filter|select|verify|complete",
            "description": "what this step does",
            "success_criteria": "how to know it's done",
            "fallback": "what to do if it fails (optional)",
            "depends_on": step_number or null,
            "estimated_actions": 3
        }
    ],
    "context_summary": "summary of how user context affects the plan",
    "constraints": ["any additional constraints to add"],
    "success_criteria": "how to know the whole task is done"
}

Return ONLY the JSON."""

        return prompt

    # -------------------------------------------------------------------------
    # Step Execution
    # -------------------------------------------------------------------------

    async def _execute_step(
        self,
        step: TaskStep,
        context: Dict[str, Any],
        starting_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single step of the plan via vision loop.
        """
        from sakhi.apps.api.services.agent.vision_loop import start_vision_loop
        from sakhi.apps.api.services.agent.sessions import create_session
        from sakhi.apps.api.services.agent.protocol import SessionRequest

        LOGGER.info(
            "[orchestrator] Executing step %d: %s",
            step.step_number,
            step.description,
        )

        try:
            # Create session for this step
            session = await create_session(
                person_id=self.person_id,
                agent_id=self.agent_id,
                request=SessionRequest(
                    agent_id=self.agent_id,
                    task_description=step.description,
                ),
            )

            # Build step-specific context
            step_context = {
                **context,
                "step_number": step.step_number,
                "success_criteria": step.success_criteria,
                "action_type": step.action,
            }

            # Execute via vision loop
            state = await start_vision_loop(
                session_id=session.id,
                agent_id=self.agent_id,
                person_id=self.person_id,
                task_description=step.description,
                starting_url=starting_url,
                context=step_context,
                max_steps=self.max_actions_per_step,
            )

            return {
                "status": "completed" if state.status.value == "completed" else "failed",
                "session_id": session.id,
                "actions_taken": state.actions_executed,
                "errors": state.errors,
                "last_analysis": state.last_screen_analysis,
            }

        except Exception as e:
            LOGGER.exception("[orchestrator] Step %d failed: %s", step.step_number, e)
            return {
                "status": "failed",
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse a JSON response, handling markdown code blocks."""
        import json

        try:
            # Strip markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            LOGGER.warning("[orchestrator] JSON parse error: %s", e)
            return {}


# =============================================================================
# Convenience Functions
# =============================================================================

async def execute_task(
    person_id: str,
    agent_id: str,
    task_description: str,
    *,
    starting_url: Optional[str] = None,
) -> TaskResult:
    """
    Execute a preference-aware autonomous task.

    This is the main entry point for the task orchestrator.

    Args:
        person_id: User's person ID
        agent_id: Registered agent ID
        task_description: What to accomplish
        starting_url: Optional URL to start at

    Returns:
        TaskResult with execution details
    """
    orchestrator = TaskOrchestrator(
        person_id=person_id,
        agent_id=agent_id,
    )

    return await orchestrator.execute(
        task_description,
        starting_url=starting_url,
    )


async def execute_shopping_task(
    person_id: str,
    agent_id: str,
    product_query: str,
    *,
    site: str = "amazon",
    max_price: Optional[float] = None,
) -> TaskResult:
    """
    Execute a shopping task with preference awareness.

    Example:
        result = await execute_shopping_task(
            person_id="123",
            agent_id="456",
            product_query="running shoes for long distance",
            site="amazon",
            max_price=150.00,
        )
    """
    # Build task description
    task = f"Find and select the best {product_query}"
    if max_price:
        task += f" under ${max_price}"

    # Determine starting URL
    urls = {
        "amazon": "https://www.amazon.com",
        "ebay": "https://www.ebay.com",
        "walmart": "https://www.walmart.com",
        "target": "https://www.target.com",
    }
    starting_url = urls.get(site.lower(), "https://www.google.com/shopping")

    return await execute_task(
        person_id=person_id,
        agent_id=agent_id,
        task_description=task,
        starting_url=starting_url,
    )


async def execute_restaurant_task(
    person_id: str,
    agent_id: str,
    criteria: Dict[str, Any],
) -> TaskResult:
    """
    Execute a restaurant finding/booking task.

    Args:
        person_id: User's person ID
        agent_id: Registered agent ID
        criteria: Search criteria like:
            - cuisine: "Italian"
            - location: "San Francisco"
            - party_size: 2
            - date: "tonight"
            - price_range: "moderate"
    """
    # Build task description from criteria
    parts = []

    if criteria.get("cuisine"):
        parts.append(criteria["cuisine"])

    parts.append("restaurant")

    if criteria.get("location"):
        parts.append(f"in {criteria['location']}")

    if criteria.get("price_range"):
        parts.append(f"({criteria['price_range']} price)")

    if criteria.get("date"):
        parts.append(f"for {criteria['date']}")

    if criteria.get("party_size"):
        parts.append(f"for {criteria['party_size']} people")

    task = f"Find a good {' '.join(parts)}"

    return await execute_task(
        person_id=person_id,
        agent_id=agent_id,
        task_description=task,
        starting_url="https://www.google.com/maps",
    )


async def get_task_plan(
    person_id: str,
    task_description: str,
) -> TaskPlan:
    """
    Get a task plan without executing it.

    Useful for previewing what Sakhi would do.
    """
    orchestrator = TaskOrchestrator(
        person_id=person_id,
        agent_id="preview",
    )

    # Gather context
    context = await orchestrator._gather_context(task_description)

    # Create plan
    plan = await orchestrator._plan_task(task_description, context)

    return plan


__all__ = [
    # Models
    "TaskType",
    "TaskStep",
    "TaskPlan",
    "TaskStatus",
    "TaskResult",
    # Main class
    "TaskOrchestrator",
    # Convenience functions
    "execute_task",
    "execute_shopping_task",
    "execute_restaurant_task",
    "get_task_plan",
]
