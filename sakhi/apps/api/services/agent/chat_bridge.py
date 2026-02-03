"""
Chat-Agent Bridge
-----------------
Connects the chat interface to the agent task orchestrator.

This module:
1. Detects when a user message is an "agent task" request
2. Creates task plans using the orchestrator
3. Manages pending task confirmations
4. Handles task execution triggers from chat

Example flow:
  User: "Book me a table at a nice Italian restaurant"
  → detect_agent_task_intent() → "restaurant" task detected
  → create_task_plan() → returns plan with steps
  → Chat shows plan and asks for confirmation
  → User: "Yes, go ahead"
  → confirm_and_start_task() → starts mock/real execution
"""

from __future__ import annotations

import logging
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import uuid

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Agent Task Intent Detection
# =============================================================================

class AgentTaskType(str, Enum):
    """Types of agent tasks that can be detected from chat."""
    RESTAURANT = "restaurant"
    SHOPPING = "shopping"
    BOOKING = "booking"
    SEARCH = "search"
    NAVIGATION = "navigation"
    GENERAL = "general"


# Intent patterns for each task type
TASK_INTENT_PATTERNS: Dict[AgentTaskType, List[str]] = {
    AgentTaskType.RESTAURANT: [
        r"book\s*(me\s+)?a?\s*table",
        r"find\s*(me\s+)?a?\s*restaurant",
        r"make\s*(a\s+)?reservation",
        r"reserve\s*(a\s+)?table",
        r"looking\s+for\s+(a\s+)?place\s+to\s+eat",
        r"recommend\s*(me\s+)?a?\s*restaurant",
        r"where\s+should\s+(i|we)\s+eat",
        r"find\s+somewhere\s+to\s+eat",
        r"(italian|indian|mexican|chinese|thai|japanese|french|american)\s+restaurant",
        r"dinner\s+(reservation|booking)",
        r"lunch\s+(reservation|booking)",
    ],
    AgentTaskType.SHOPPING: [
        r"buy\s*(me\s+)?",
        r"order\s*(me\s+)?",
        r"shop\s+for",
        r"find\s*(me\s+)?(a|some|the)\s+\w+\s+(on|from|at)\s+(amazon|flipkart|walmart)",
        r"add\s+to\s+(my\s+)?cart",
        r"purchase\s+",
        r"get\s+me\s+",
        r"i\s+need\s+to\s+buy",
        r"looking\s+for\s+\w+\s+to\s+buy",
    ],
    AgentTaskType.BOOKING: [
        r"book\s*(me\s+)?(a\s+)?(flight|hotel|ticket|appointment|cab|uber|ola)",
        r"schedule\s*(an?\s+)?appointment",
        r"reserve\s*(a\s+)?(room|seat|spot)",
        r"make\s*(a\s+)?booking",
        # Accommodation patterns
        r"find\s*(me\s+)?(a\s+)?(accommodation|hotel|place\s+to\s+stay|room|hostel|airbnb|oyo)",
        r"need\s+(a\s+)?(accommodation|hotel|place\s+to\s+stay|room)",
        r"looking\s+for\s+(a\s+)?(accommodation|hotel|place\s+to\s+stay|room)",
        r"get\s+me\s+(a\s+)?(accommodation|hotel|room)",
        r"stay\s+(in|at|near)\s+",
        r"one\s+day\s+accomodation",
        r"one\s+night\s+(stay|accommodation|hotel)",
    ],
    AgentTaskType.SEARCH: [
        r"search\s+for",
        r"look\s+up",
        r"find\s+information\s+(on|about)",
        r"google\s+",
        r"research\s+",
    ],
    AgentTaskType.NAVIGATION: [
        r"open\s+(the\s+)?",
        r"go\s+to\s+",
        r"navigate\s+to",
        r"take\s+me\s+to",
    ],
}

# Confirmation patterns
CONFIRMATION_PATTERNS = [
    r"^yes\s*(,|\.|!)?$",
    r"^yeah\s*(,|\.|!)?$",
    r"^yep\s*(,|\.|!)?$",
    r"^sure\s*(,|\.|!)?$",
    r"^ok\s*(ay)?\s*(,|\.|!)?$",
    r"^go\s+ahead",
    r"^proceed",
    r"^do\s+it",
    r"^start\s*(it)?",
    r"^yes,?\s*(please|go ahead|proceed|start|do it)",
    r"^sounds\s+good",
    r"^let'?s\s+(do|go)",
]

REJECTION_PATTERNS = [
    r"^no\s*(,|\.|!)?$",
    r"^nope\s*(,|\.|!)?$",
    r"^cancel",
    r"^stop",
    r"^don'?t",
    r"^never\s*mind",
    r"^forget\s+it",
]


def detect_agent_task_intent(text: str) -> Optional[Tuple[AgentTaskType, str, float]]:
    """
    Detect if user message is an agent task request.

    Returns:
        Tuple of (task_type, matched_pattern, confidence) or None
    """
    text_lower = text.lower().strip()

    for task_type, patterns in TASK_INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Calculate confidence based on pattern specificity
                confidence = 0.7 + (len(match.group()) / len(text_lower)) * 0.3
                confidence = min(confidence, 0.95)

                LOGGER.info(
                    "[chat_bridge] Detected agent task: type=%s pattern=%s confidence=%.2f",
                    task_type.value,
                    pattern,
                    confidence,
                )

                return (task_type, pattern, confidence)

    return None


def detect_task_confirmation(text: str) -> Optional[bool]:
    """
    Detect if user message is confirming or rejecting a pending task.

    Returns:
        True for confirmation, False for rejection, None if neither
    """
    text_lower = text.lower().strip()

    for pattern in CONFIRMATION_PATTERNS:
        if re.match(pattern, text_lower):
            return True

    for pattern in REJECTION_PATTERNS:
        if re.match(pattern, text_lower):
            return False

    return None


# =============================================================================
# Pending Task Management
# =============================================================================

class PendingTask(BaseModel):
    """A task awaiting user confirmation."""
    task_id: str
    person_id: str
    task_type: AgentTaskType
    task_description: str
    original_request: str

    # Plan details
    plan_steps: List[Dict[str, Any]]
    context_used: Dict[str, Any]

    # Status
    status: str = "pending_confirmation"  # pending_confirmation, confirmed, rejected, executing, completed
    created_at: datetime = datetime.utcnow()
    expires_at: Optional[datetime] = None

    # Execution
    current_step: int = 0
    execution_started_at: Optional[datetime] = None


# In-memory store for demo (should be Redis in production)
_pending_tasks: Dict[str, PendingTask] = {}


async def create_pending_task(
    person_id: str,
    task_type: AgentTaskType,
    original_request: str,
    plan_steps: List[Dict[str, Any]],
    context_used: Dict[str, Any],
) -> PendingTask:
    """
    Create a pending task awaiting user confirmation.
    """
    # Use full UUID for DB, short form for display
    full_task_id = str(uuid.uuid4())
    task_id = full_task_id[:12]  # Short ID for in-memory tracking

    # Generate task description
    description = _generate_task_description(task_type, original_request, plan_steps)

    task = PendingTask(
        task_id=task_id,
        person_id=person_id,
        task_type=task_type,
        task_description=description,
        original_request=original_request,
        plan_steps=plan_steps,
        context_used=context_used,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )

    _pending_tasks[task_id] = task

    # Also store in database for persistence
    try:
        await dbexec(
            """
            INSERT INTO agent_task_plans (
                id, person_id, task_type, task_description, steps, context_used, status
            ) VALUES (
                $1::uuid, $2, $3, $4, $5::jsonb, $6::jsonb, 'pending_confirmation'
            )
            """,
            full_task_id,  # Use full UUID for database
            person_id,
            task_type.value,
            description,
            json.dumps(plan_steps),
            json.dumps(context_used),
        )
    except Exception as e:
        LOGGER.warning("[chat_bridge] Failed to persist task: %s", e)

    LOGGER.info(
        "[chat_bridge] Created pending task: id=%s type=%s steps=%d",
        task_id,
        task_type.value,
        len(plan_steps),
    )

    return task


async def get_pending_task(person_id: str) -> Optional[PendingTask]:
    """Get the current pending task for a user."""
    for task in _pending_tasks.values():
        if task.person_id == person_id and task.status == "pending_confirmation":
            # Check if expired
            if task.expires_at and datetime.utcnow() > task.expires_at:
                task.status = "expired"
                continue
            return task
    return None


async def confirm_task(task_id: str) -> Optional[PendingTask]:
    """Confirm a pending task and mark it for execution."""
    task = _pending_tasks.get(task_id)
    if not task:
        return None

    task.status = "confirmed"
    task.execution_started_at = datetime.utcnow()

    LOGGER.info("[chat_bridge] Task confirmed: id=%s", task_id)

    return task


async def reject_task(task_id: str) -> Optional[PendingTask]:
    """Reject a pending task."""
    task = _pending_tasks.get(task_id)
    if not task:
        return None

    task.status = "rejected"

    LOGGER.info("[chat_bridge] Task rejected: id=%s", task_id)

    return task


def _generate_task_description(
    task_type: AgentTaskType,
    original_request: str,
    plan_steps: List[Dict[str, Any]],
) -> str:
    """Generate a human-readable task description."""
    descriptions = {
        AgentTaskType.RESTAURANT: "Find and book a restaurant",
        AgentTaskType.SHOPPING: "Find and purchase items",
        AgentTaskType.BOOKING: "Make a booking or reservation",
        AgentTaskType.SEARCH: "Search and gather information",
        AgentTaskType.NAVIGATION: "Navigate to a website or app",
        AgentTaskType.GENERAL: "Complete a task",
    }

    base = descriptions.get(task_type, "Complete a task")

    # Extract key details from request
    # This is simplified - in production, use LLM extraction
    if "italian" in original_request.lower():
        base = "Find and book an Italian restaurant"
    elif "indian" in original_request.lower():
        base = "Find and book an Indian restaurant"

    return base


# =============================================================================
# Task Plan Generation (bridges to TaskOrchestrator)
# =============================================================================

async def generate_task_plan(
    person_id: str,
    task_type: AgentTaskType,
    task_request: str,
) -> Dict[str, Any]:
    """
    Generate a task plan using the real TaskOrchestrator.

    This uses Claude to create an intelligent plan based on:
    - User's sensory preferences
    - Food/restaurant memories
    - Relevant past experiences
    - Extracted constraints
    """
    try:
        from sakhi.apps.api.services.agent.task_orchestrator import get_task_plan

        # Get real plan from orchestrator (uses Claude + user context)
        plan = await get_task_plan(
            person_id=person_id,
            task_description=task_request,
        )

        # Extract details for additional context display
        details = _extract_task_details(task_request)

        # Build context from plan
        context = {
            "context_summary": plan.context_summary,
            "constraints": plan.constraints,
            "task_type": plan.task_type.value if hasattr(plan.task_type, 'value') else str(plan.task_type),
        }

        # Add extracted details
        if details.get("city"):
            context["city"] = details["city"]
        if details.get("budget_str"):
            context["budget"] = details["budget_str"]
        if details.get("date"):
            context["date"] = details["date"]
        if details.get("suggested_location"):
            context["suggested_location"] = details["suggested_location"]
        if details:
            context["extracted_from_request"] = True

        # Calculate estimated duration
        total_actions = plan.total_estimated_actions
        # Rough estimate: 10 seconds per action
        estimated_minutes = max(1, total_actions // 6)

        LOGGER.info(
            "[chat_bridge] Generated real plan: %d steps, %d estimated actions",
            len(plan.steps),
            total_actions,
        )

        return {
            "success": True,
            "steps": [
                {
                    "step_number": step.step_number,
                    "action": step.action,
                    "description": step.description,
                    "success_criteria": step.success_criteria,
                    "requires_approval": step.action in ["book", "purchase", "checkout", "reserve", "submit"],
                    "estimated_actions": step.estimated_actions,
                }
                for step in plan.steps
            ],
            "context": context,
            "estimated_duration": estimated_minutes,
            "success_criteria": plan.success_criteria,
        }

    except Exception as e:
        LOGGER.warning("[chat_bridge] TaskOrchestrator failed: %s", e)

        # If orchestrator fails, create a simple plan with extracted details
        # This is NOT a mock - it's a fallback using real extracted info
        details = _extract_task_details(task_request)

        return {
            "success": True,
            "steps": [
                {
                    "step_number": 1,
                    "action": "search",
                    "description": f"Search for options matching your request",
                    "success_criteria": "Found relevant options",
                    "requires_approval": False,
                },
                {
                    "step_number": 2,
                    "action": "evaluate",
                    "description": "Compare and evaluate options",
                    "success_criteria": "Identified best options",
                    "requires_approval": False,
                },
                {
                    "step_number": 3,
                    "action": "select",
                    "description": "Select the best match",
                    "success_criteria": "Option selected",
                    "requires_approval": True,
                },
            ],
            "context": {
                "city": details.get("city"),
                "budget": details.get("budget_str"),
                "date": details.get("date"),
                "suggested_location": details.get("suggested_location"),
                "extracted_from_request": True,
                "fallback_plan": True,
            },
            "estimated_duration": 3,
        }


def _extract_task_details(task_request: str) -> Dict[str, Any]:
    """Extract details from the task request for smarter planning."""
    details = {}
    text_lower = task_request.lower()

    # Extract budget
    import re
    budget_match = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*(rupees|rs|inr|₹)?', text_lower)
    if budget_match:
        details['budget_min'] = int(budget_match.group(1))
        details['budget_max'] = int(budget_match.group(2))
        details['budget_str'] = f"₹{budget_match.group(1)}-{budget_match.group(2)}"

    # Extract location
    cities = ['chennai', 'mumbai', 'delhi', 'bangalore', 'hyderabad', 'kolkata', 'pune']
    for city in cities:
        if city in text_lower:
            details['city'] = city.title()
            break

    # Extract date
    date_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(st|nd|rd|th)?', text_lower)
    if date_match:
        details['date'] = f"{date_match.group(1).title()} {date_match.group(2)}"

    # Extract purpose/context
    if 'visa' in text_lower or 'consulate' in text_lower or 'embassy' in text_lower:
        details['purpose'] = 'visa_interview'
        details['suggested_location'] = 'near US Consulate'
    if 'interview' in text_lower:
        details['has_interview'] = True

    return details


def _generate_mock_plan(
    task_type: AgentTaskType,
    task_request: str,
) -> Dict[str, Any]:
    """Generate a mock plan for demo purposes."""

    # Extract details from request
    details = _extract_task_details(task_request)

    if task_type == AgentTaskType.BOOKING:
        # Smart accommodation plan
        location_hint = details.get('suggested_location', 'central location')
        city = details.get('city', 'the city')
        budget = details.get('budget_str', 'your budget')
        date = details.get('date', 'your dates')

        return {
            "success": True,
            "steps": [
                {
                    "step_number": 1,
                    "action": "search",
                    "description": f"Search for accommodations in {city} {location_hint}",
                    "target": "MakeMyTrip, OYO, Booking.com",
                    "estimated_seconds": 30,
                },
                {
                    "step_number": 2,
                    "action": "filter",
                    "description": f"Filter by budget ({budget}) and check-in date ({date})",
                    "estimated_seconds": 15,
                },
                {
                    "step_number": 3,
                    "action": "evaluate",
                    "description": "Compare options based on ratings, distance, and amenities",
                    "estimated_seconds": 20,
                },
                {
                    "step_number": 4,
                    "action": "select",
                    "description": "Pick the best match and show you details",
                    "requires_approval": True,
                    "estimated_seconds": 10,
                },
                {
                    "step_number": 5,
                    "action": "book",
                    "description": "Complete the booking",
                    "requires_approval": True,
                    "estimated_seconds": 45,
                },
            ],
            "context": {
                "city": city,
                "budget": budget,
                "date": date,
                "purpose": details.get('purpose'),
                "suggested_location": location_hint,
                "extracted_from_request": True,
            },
            "estimated_duration": 3,
        }

    if task_type == AgentTaskType.RESTAURANT:
        return {
            "success": True,
            "steps": [
                {
                    "step_number": 1,
                    "action": "search",
                    "description": "Search for restaurants matching your preferences",
                    "target": "Google Maps or OpenTable",
                    "estimated_seconds": 30,
                },
                {
                    "step_number": 2,
                    "action": "evaluate",
                    "description": "Compare options based on your taste preferences and past experiences",
                    "details": "Checking ratings, cuisine type, price range",
                    "estimated_seconds": 20,
                },
                {
                    "step_number": 3,
                    "action": "select",
                    "description": "Pick the best match and check availability",
                    "requires_approval": True,
                    "estimated_seconds": 15,
                },
                {
                    "step_number": 4,
                    "action": "book",
                    "description": "Make the reservation",
                    "requires_approval": True,
                    "estimated_seconds": 30,
                },
            ],
            "context": {
                "preferences_loaded": True,
                "past_restaurants": 3,
                "dietary_restrictions": ["vegetarian options preferred"],
            },
            "estimated_duration": 2,
        }

    elif task_type == AgentTaskType.SHOPPING:
        return {
            "success": True,
            "steps": [
                {
                    "step_number": 1,
                    "action": "navigate",
                    "description": "Open shopping website",
                    "target": "Amazon",
                    "estimated_seconds": 10,
                },
                {
                    "step_number": 2,
                    "action": "search",
                    "description": "Search for products matching your request",
                    "estimated_seconds": 15,
                },
                {
                    "step_number": 3,
                    "action": "evaluate",
                    "description": "Compare options based on your preferences",
                    "details": "Checking reviews, price, features",
                    "estimated_seconds": 30,
                },
                {
                    "step_number": 4,
                    "action": "add_to_cart",
                    "description": "Add selected item to cart",
                    "requires_approval": True,
                    "estimated_seconds": 10,
                },
            ],
            "context": {
                "preferences_loaded": True,
                "sensory_preferences": {"texture": "soft", "temperature": "room temp"},
            },
            "estimated_duration": 2,
        }

    else:
        return {
            "success": True,
            "steps": [
                {
                    "step_number": 1,
                    "action": "analyze",
                    "description": "Understand the task requirements",
                    "estimated_seconds": 10,
                },
                {
                    "step_number": 2,
                    "action": "execute",
                    "description": "Perform the requested action",
                    "estimated_seconds": 30,
                },
                {
                    "step_number": 3,
                    "action": "verify",
                    "description": "Confirm the task was completed successfully",
                    "estimated_seconds": 10,
                },
            ],
            "context": {},
            "estimated_duration": 1,
        }


# =============================================================================
# Real Task Execution (via Desktop Agent + Vision Loop)
# =============================================================================

class TaskExecutionState(BaseModel):
    """State of a real task execution."""
    task_id: str
    person_id: str
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    current_step: int = 0
    total_steps: int
    status: str = "running"  # running, waiting_approval, completed, failed, no_agent
    steps_completed: List[Dict[str, Any]] = []
    pending_approval: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


_task_executions: Dict[str, TaskExecutionState] = {}


async def get_active_agent_for_person(person_id: str) -> Optional[str]:
    """
    Get the active/online agent ID for a person.

    Returns the most recently active agent that is online (has recent heartbeat).
    """
    from sakhi.apps.api.services.agent.sessions import get_agents_for_person

    try:
        agents = await get_agents_for_person(person_id)

        if not agents:
            LOGGER.info("[chat_bridge] No registered agents for person %s", person_id)
            return None

        # Find an active agent (recent heartbeat within 2 minutes)
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)

        for agent in agents:
            # Handle both timezone-aware and naive datetimes
            heartbeat = agent.last_heartbeat_at
            if heartbeat:
                # Make heartbeat timezone-aware if it isn't
                if heartbeat.tzinfo is None:
                    heartbeat = heartbeat.replace(tzinfo=timezone.utc)
                # Check if heartbeat is recent (within cutoff)
                is_active = heartbeat > cutoff
                if is_active:
                    LOGGER.info(
                        "[chat_bridge] Found active agent: %s (%s) for person %s",
                        agent.id,
                        agent.agent_name,
                        person_id,
                    )
                    return agent.id

        # If no recently active agent, return the most recent one anyway
        # (it might come online)
        LOGGER.info(
            "[chat_bridge] No active agent, using most recent: %s for person %s",
            agents[0].id,
            person_id,
        )
        return agents[0].id

    except Exception as e:
        LOGGER.warning("[chat_bridge] Failed to get agents: %s", e)
        return None


async def start_task_execution(task: PendingTask) -> TaskExecutionState:
    """
    Start real execution of a confirmed task via the desktop agent.

    This uses the actual TaskOrchestrator → VisionLoop → Desktop Agent flow.
    """
    # Get the user's active agent
    agent_id = await get_active_agent_for_person(task.person_id)

    state = TaskExecutionState(
        task_id=task.task_id,
        person_id=task.person_id,
        agent_id=agent_id,
        total_steps=len(task.plan_steps),
    )

    _task_executions[task.task_id] = state

    if not agent_id:
        state.status = "no_agent"
        state.error = "No desktop agent is currently connected. Please ensure Sakhi Desktop Agent is running."
        LOGGER.warning("[chat_bridge] No agent available for task %s", task.task_id)
        return state

    # Start the real execution in background
    import asyncio
    asyncio.create_task(_execute_task_real(state, task))

    return state


async def _execute_task_real(
    state: TaskExecutionState,
    task: PendingTask,
) -> None:
    """
    Execute the task using the real TaskOrchestrator.

    This runs the full preference-aware vision loop.
    """
    from sakhi.apps.api.services.agent.task_orchestrator import execute_task

    try:
        LOGGER.info(
            "[chat_bridge] Starting real execution: task=%s agent=%s",
            task.task_id,
            state.agent_id,
        )

        # Execute via the real orchestrator
        result = await execute_task(
            person_id=task.person_id,
            agent_id=state.agent_id,
            task_description=task.original_request,
        )

        # Update state from result
        state.current_step = result.steps_completed
        state.total_steps = len(result.plan.steps) if result.plan else state.total_steps

        if result.status.value == "completed":
            state.status = "completed"
            state.result = {
                "success": True,
                "message": "Task completed successfully",
                "steps_completed": result.steps_completed,
                "context_used": result.context_used,
            }
        elif result.status.value == "failed":
            state.status = "failed"
            state.error = "; ".join(result.errors) if result.errors else "Task failed"
            state.result = {
                "success": False,
                "errors": result.errors,
                "steps_completed": result.steps_completed,
            }
        else:
            # Still running or blocked
            state.status = result.status.value

        LOGGER.info(
            "[chat_bridge] Task execution finished: task=%s status=%s steps=%d",
            task.task_id,
            state.status,
            state.current_step,
        )

    except Exception as e:
        LOGGER.exception("[chat_bridge] Task execution failed: %s", e)
        state.status = "failed"
        state.error = str(e)
        state.result = {
            "success": False,
            "error": str(e),
        }


async def get_task_execution_state(task_id: str) -> Optional[TaskExecutionState]:
    """Get the current state of a task execution."""
    return _task_executions.get(task_id)


async def get_active_task_executions_for_person(person_id: str) -> List[TaskExecutionState]:
    """Get all active task executions for a person."""
    # Normalize person_id for comparison
    person_id_str = str(person_id).lower()
    LOGGER.debug(
        "[chat_bridge] Looking for active tasks for person %s, have %d tasks total",
        person_id_str,
        len(_task_executions),
    )
    results = [
        state for state in _task_executions.values()
        if str(state.person_id).lower() == person_id_str
    ]
    LOGGER.debug("[chat_bridge] Found %d active tasks for person %s", len(results), person_id_str)
    return results


async def approve_execution_step(task_id: str) -> Optional[TaskExecutionState]:
    """
    Approve a pending step in the execution.

    This responds to action approval requests in the real system.
    """
    state = _task_executions.get(task_id)
    if not state or state.status != "waiting_approval":
        return None

    # Respond to the approval request
    from sakhi.apps.api.services.agent.action_approval import submit_approval_response

    if state.pending_approval and state.pending_approval.get("request_id"):
        try:
            await submit_approval_response(
                request_id=state.pending_approval["request_id"],
                approved=True,
            )
        except Exception as e:
            LOGGER.warning("[chat_bridge] Failed to respond to approval: %s", e)

    # Update state
    state.pending_approval = None
    state.status = "running"

    return state


# Backward compatibility aliases
MockExecutionState = TaskExecutionState
_mock_executions = _task_executions
start_mock_execution = start_task_execution
get_mock_execution_state = get_task_execution_state
approve_mock_step = approve_execution_step


# =============================================================================
# Chat Response Formatting
# =============================================================================

def format_task_plan_for_chat(
    task_type: AgentTaskType,
    plan: Dict[str, Any],
    context: Dict[str, Any],
) -> str:
    """
    Format a task plan as a chat message.

    Returns a string that Sakhi can use in the reply.
    """
    steps = plan.get("steps", [])
    duration = plan.get("estimated_duration", 2)

    # Build step list
    step_list = []
    for step in steps:
        step_num = step.get("step_number", len(step_list) + 1)
        description = step.get("description", "Execute action")
        approval = " *(requires your approval)*" if step.get("requires_approval") else ""
        step_list.append(f"{step_num}. {description}{approval}")

    steps_text = "\n".join(step_list)

    # Context info - show what we understood
    context_info = ""

    # For booking/accommodation tasks
    if context.get("extracted_from_request"):
        understood_parts = []
        if context.get("city"):
            understood_parts.append(f"**Location:** {context['city']}")
        if context.get("budget"):
            understood_parts.append(f"**Budget:** {context['budget']}")
        if context.get("date"):
            understood_parts.append(f"**Date:** {context['date']}")
        if context.get("suggested_location"):
            understood_parts.append(f"**Ideal area:** {context['suggested_location']}")

        if understood_parts:
            context_info = "\n\n**I understood:**\n" + "\n".join(understood_parts)

    # For restaurant/general tasks
    if context.get("preferences_loaded"):
        context_info += "\n\nI'll use your preferences and past experiences to find the best match."
    if context.get("past_restaurants"):
        context_info += f" I see you've rated {context['past_restaurants']} restaurants before."

    return f"""Here's my plan:

{steps_text}

Estimated time: ~{duration} minutes{context_info}

Would you like me to proceed?"""


def format_execution_update_for_chat(state: TaskExecutionState) -> str:
    """Format an execution state update for chat."""
    if state.status == "completed":
        return f"Done! Completed all {state.total_steps} steps successfully."

    if state.status == "no_agent":
        return f"I need my desktop agent to be running to help with this task. {state.error or 'Please start Sakhi Desktop Agent.'}"

    if state.status == "failed":
        return f"I ran into an issue: {state.error or 'Task could not be completed'}. Would you like me to try again?"

    if state.status == "waiting_approval":
        approval = state.pending_approval
        if approval:
            return f"Step {approval.get('step', state.current_step + 1)}: {approval.get('description', 'Ready to proceed')}\n\nShould I proceed with this?"
        return "Waiting for your approval to continue."

    if state.status == "running":
        return f"Working on step {state.current_step + 1} of {state.total_steps}..."

    return "Task is in progress."


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "AgentTaskType",
    "PendingTask",
    "TaskExecutionState",
    # Detection
    "detect_agent_task_intent",
    "detect_task_confirmation",
    # Task management
    "create_pending_task",
    "get_pending_task",
    "confirm_task",
    "reject_task",
    # Planning
    "generate_task_plan",
    # Real execution
    "get_active_agent_for_person",
    "start_task_execution",
    "get_task_execution_state",
    "approve_execution_step",
    # Formatting
    "format_task_plan_for_chat",
    "format_execution_update_for_chat",
    # Backward compatibility
    "MockExecutionState",
    "start_mock_execution",
    "get_mock_execution_state",
    "approve_mock_step",
]
