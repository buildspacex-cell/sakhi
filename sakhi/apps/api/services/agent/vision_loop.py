"""
Vision Loop Orchestrator
------------------------
Core autonomous browsing loop for Sakhi Desktop Agent.

The vision loop enables Sakhi to:
1. Capture the current screen state
2. Analyze what's visible (via Claude Vision)
3. Decide what action to take next
4. Execute the action
5. Repeat until task is complete

This is the "brain" that lets Sakhi browse the web and interact
with desktop applications autonomously on your behalf.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.services.agent.errors import (
    AgentError,
    VisionLoopError,
    ErrorReason,
    classify_error,
    is_retryable_error,
    get_retry_delay_ms,
    track_error,
    clear_errors,
)
from sakhi.apps.api.services.agent.timeouts import (
    Timeouts,
    clamp_timeout,
    ms_to_seconds,
    with_timeout,
    poll_until,
)
from sakhi.apps.api.services.agent.session_lock import (
    session_write_lock,
    release_all_locks,
)

from sakhi.apps.api.services.agent.sessions import (
    AgentSession,
    get_session,
    get_active_session,
    update_session_step,
    update_session_screen,
    end_session,
)
from sakhi.apps.api.services.agent.actions import (
    queue_action,
    queue_action_batch,
    get_latest_screenshot,
    store_screenshot,
    update_screenshot_analysis,
)
from sakhi.apps.api.services.agent.protocol import (
    AgentAction,
    ActionType,
    SessionStatus,
    ScreenCapture,
    ScreenUnderstanding,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Vision Loop Models
# =============================================================================

class LoopStatus(str, Enum):
    """Status of the vision loop."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_INPUT = "waiting_input"
    WAITING_APPROVAL = "waiting_approval"  # Paused for user approval
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VisionLoopState(BaseModel):
    """Current state of a vision loop execution."""
    session_id: str
    status: LoopStatus = LoopStatus.IDLE
    current_step: int = 0
    max_steps: int = 50  # Safety limit
    task_description: str
    task_context: Dict[str, Any] = {}

    # Execution tracking
    actions_executed: int = 0
    errors: List[str] = []
    classified_errors: List[Dict[str, Any]] = []  # Detailed error info
    last_screen_analysis: Optional[Dict[str, Any]] = None
    last_action: Optional[Dict[str, Any]] = None
    action_history: List[Dict[str, Any]] = []  # Full history for context

    # Retry tracking (OpenClaw pattern)
    consecutive_errors: int = 0
    total_retries: int = 0
    max_retries_per_step: int = 3
    context_compaction_attempted: bool = False

    # Approval tracking
    pending_approval_id: Optional[str] = None
    approvals_requested: int = 0
    approvals_granted: int = 0
    approvals_rejected: int = 0

    # Timing
    started_at: Optional[datetime] = None
    last_step_at: Optional[datetime] = None
    timeout_at: Optional[datetime] = None


class StepResult(BaseModel):
    """Result of a single vision loop step."""
    success: bool
    action_taken: Optional[AgentAction] = None
    screen_analysis: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    is_complete: bool = False
    error: Optional[str] = None
    # Approval tracking
    needs_approval: bool = False
    approval_request_id: Optional[str] = None
    approval_status: Optional[str] = None  # pending, approved, rejected


# =============================================================================
# Vision Loop Orchestrator
# =============================================================================

class VisionLoop:
    """
    Orchestrates the autonomous vision-action loop.

    This is the core component that enables Sakhi to:
    - See what's on screen (via screenshots + Claude Vision)
    - Understand the current state
    - Decide what to do next
    - Take action
    - Verify the result

    Example usage:
        loop = VisionLoop(session_id="abc123", agent_id="agent456")
        await loop.start("Find a good Italian restaurant in SF for dinner tonight")
    """

    def __init__(
        self,
        session_id: str,
        agent_id: str,
        person_id: str,
        *,
        max_steps: int = 50,
        step_delay_ms: int = 500,
        timeout_minutes: int = 30,
        on_step: Optional[Callable[[StepResult], None]] = None,
        on_screenshot: Optional[Callable[[str], None]] = None,
        on_approval_needed: Optional[Callable[[Dict[str, Any]], None]] = None,
        require_approval: bool = True,  # Enable approval flow
    ):
        self.session_id = session_id
        self.agent_id = agent_id
        self.person_id = person_id
        self.max_steps = max_steps
        self.step_delay_ms = step_delay_ms
        self.timeout_minutes = timeout_minutes
        self.require_approval = require_approval

        # Callbacks
        self.on_step = on_step
        self.on_screenshot = on_screenshot
        self.on_approval_needed = on_approval_needed

        # State
        self.state: Optional[VisionLoopState] = None
        self._running = False
        self._paused = False
        self._waiting_approval = False

    async def start(
        self,
        task_description: str,
        *,
        initial_context: Optional[Dict[str, Any]] = None,
        starting_url: Optional[str] = None,
    ) -> VisionLoopState:
        """
        Start the vision loop for a task.

        Args:
            task_description: What the user wants to accomplish
            initial_context: Optional context (preferences, constraints, etc.)
            starting_url: Optional URL to navigate to first

        Returns:
            Final state after loop completes or fails
        """
        LOGGER.info(
            "[vision_loop] Starting for session %s: %s",
            self.session_id,
            task_description[:100],
        )

        # Initialize state
        self.state = VisionLoopState(
            session_id=self.session_id,
            status=LoopStatus.RUNNING,
            task_description=task_description,
            task_context=initial_context or {},
            started_at=datetime.utcnow(),
            timeout_at=datetime.utcnow() + timedelta(minutes=self.timeout_minutes),
        )

        self._running = True

        try:
            # Queue a command to notify the desktop agent to start this session
            await self._notify_agent_session_start(task_description)

            # Navigate to starting URL if provided
            if starting_url:
                await self._execute_action(AgentAction(
                    action_id="init_navigate",
                    action_type=ActionType.NAVIGATE,
                    parameters={"url": starting_url},
                    sequence=0,
                ))

            # Wait for the desktop agent to capture an initial screenshot
            # This gives the agent time to receive the command and respond
            initial_screenshot = await self._wait_for_screenshot(timeout_seconds=60)
            if not initial_screenshot:
                LOGGER.error("[vision_loop] No desktop agent response - timed out waiting for screenshot")
                self.state.status = LoopStatus.FAILED
                self.state.errors.append(
                    "Desktop agent not responding. Please ensure Sakhi Desktop Agent is running and connected."
                )
                await end_session(self.session_id, SessionStatus.FAILED)
                return self.state

            LOGGER.info("[vision_loop] Received initial screenshot, starting vision loop")

            # Main loop with multi-layer retry (OpenClaw pattern)
            while self._should_continue():
                step_retry_count = 0

                while step_retry_count <= self.state.max_retries_per_step:
                    try:
                        result = await self._execute_step_with_timeout()

                        # Success - clear error tracking
                        self.state.consecutive_errors = 0
                        clear_errors(self.agent_id)

                        if self.on_step:
                            self.on_step(result)

                        if result.is_complete:
                            self.state.status = LoopStatus.COMPLETED
                            LOGGER.info("[vision_loop] Task completed successfully")
                            break

                        if result.error:
                            # Classify the error
                            classified = classify_error(
                                Exception(result.error),
                                context={
                                    "session_id": self.session_id,
                                    "agent_id": self.agent_id,
                                },
                            )
                            self.state.classified_errors.append(classified.to_dict())

                            if is_retryable_error(classified):
                                step_retry_count += 1
                                self.state.total_retries += 1
                                self.state.consecutive_errors += 1

                                if step_retry_count <= self.state.max_retries_per_step:
                                    delay_ms = get_retry_delay_ms(classified, step_retry_count)
                                    LOGGER.info(
                                        "[vision_loop] Retrying step (attempt %d/%d) after %dms: %s",
                                        step_retry_count,
                                        self.state.max_retries_per_step,
                                        delay_ms,
                                        classified.reason.value,
                                    )
                                    await asyncio.sleep(ms_to_seconds(delay_ms))
                                    continue
                            else:
                                # Non-retryable error
                                self.state.errors.append(result.error)
                                self.state.consecutive_errors += 1

                        break  # Exit retry loop on success or non-retryable error

                    except AgentError as e:
                        # Classified error from our system
                        self.state.classified_errors.append(e.to_dict())
                        self.state.consecutive_errors += 1
                        track_error(self.agent_id)

                        if e.is_retryable() and step_retry_count < self.state.max_retries_per_step:
                            step_retry_count += 1
                            self.state.total_retries += 1
                            delay_ms = get_retry_delay_ms(e, step_retry_count)
                            LOGGER.warning(
                                "[vision_loop] Retryable error (attempt %d): %s",
                                step_retry_count,
                                e.reason.value,
                            )
                            await asyncio.sleep(ms_to_seconds(delay_ms))
                            continue
                        else:
                            self.state.errors.append(str(e))
                            break

                    except Exception as e:
                        # Unclassified error - classify and handle
                        classified = classify_error(
                            e,
                            context={
                                "session_id": self.session_id,
                                "agent_id": self.agent_id,
                            },
                        )
                        self.state.classified_errors.append(classified.to_dict())
                        self.state.consecutive_errors += 1
                        track_error(self.agent_id)

                        if classified.is_retryable() and step_retry_count < self.state.max_retries_per_step:
                            step_retry_count += 1
                            self.state.total_retries += 1
                            delay_ms = get_retry_delay_ms(classified, step_retry_count)
                            LOGGER.warning(
                                "[vision_loop] Retrying after error (attempt %d): %s",
                                step_retry_count,
                                classified.reason.value,
                            )
                            await asyncio.sleep(ms_to_seconds(delay_ms))
                            continue
                        else:
                            self.state.errors.append(str(e))
                            LOGGER.exception("[vision_loop] Non-retryable error: %s", e)
                            break

                # Check if we hit max consecutive errors
                if self.state.consecutive_errors >= 5:
                    LOGGER.error(
                        "[vision_loop] Too many consecutive errors (%d), stopping",
                        self.state.consecutive_errors,
                    )
                    self.state.status = LoopStatus.FAILED
                    self.state.errors.append("Max consecutive errors exceeded")
                    break

                if result and result.is_complete:
                    break

                # Small delay between steps
                delay = clamp_timeout(self.step_delay_ms, default_ms=500, min_ms=100, max_ms=5000)
                await asyncio.sleep(ms_to_seconds(delay))

            # Update session status
            if self.state.status == LoopStatus.COMPLETED:
                await end_session(self.session_id, SessionStatus.COMPLETED)
            elif self.state.status == LoopStatus.FAILED:
                await end_session(self.session_id, SessionStatus.FAILED)
            elif self.state.status == LoopStatus.CANCELLED:
                await end_session(self.session_id, SessionStatus.CANCELLED)

        except Exception as e:
            LOGGER.exception("[vision_loop] Fatal error: %s", e)
            self.state.status = LoopStatus.FAILED
            self.state.errors.append(str(e))
            await end_session(self.session_id, SessionStatus.FAILED)

        finally:
            self._running = False

        return self.state

    async def pause(self) -> None:
        """Pause the vision loop."""
        self._paused = True
        if self.state:
            self.state.status = LoopStatus.PAUSED
        LOGGER.info("[vision_loop] Paused session %s", self.session_id)

    async def resume(self) -> None:
        """Resume a paused vision loop."""
        self._paused = False
        if self.state:
            self.state.status = LoopStatus.RUNNING
        LOGGER.info("[vision_loop] Resumed session %s", self.session_id)

    async def stop(self) -> None:
        """Stop the vision loop."""
        self._running = False
        if self.state:
            self.state.status = LoopStatus.CANCELLED
        LOGGER.info("[vision_loop] Stopped session %s", self.session_id)

    def _should_continue(self) -> bool:
        """Check if the loop should continue running."""
        if not self._running:
            return False

        if self._paused:
            return False

        if self._waiting_approval:
            return False  # Paused waiting for user approval

        if not self.state:
            return False

        # Check step limit
        if self.state.current_step >= self.max_steps:
            LOGGER.warning("[vision_loop] Hit max steps limit: %d", self.max_steps)
            self.state.status = LoopStatus.FAILED
            self.state.errors.append("Max steps exceeded")
            return False

        # Check timeout
        if self.state.timeout_at and datetime.utcnow() > self.state.timeout_at:
            LOGGER.warning("[vision_loop] Session timed out")
            self.state.status = LoopStatus.FAILED
            self.state.errors.append("Session timed out")
            return False

        return True

    async def _execute_step_with_timeout(self) -> StepResult:
        """Execute a step with defensive timeout and session locking."""
        try:
            # Acquire session lock to prevent concurrent writes
            async with session_write_lock(self.session_id, timeout_ms=Timeouts.LOCK_ACQUISITION):
                return await with_timeout(
                    self._execute_step(),
                    timeout_ms=Timeouts.ACTION_EXECUTION + Timeouts.SCREEN_ANALYSIS + Timeouts.ACTION_DECISION,
                    operation_name="vision_loop_step",
                    min_ms=30000,  # At least 30 seconds for a full step
                    max_ms=180000,  # Max 3 minutes per step
                )
        except AgentError:
            raise
        except asyncio.TimeoutError:
            raise VisionLoopError(
                "Step execution timed out",
                reason=ErrorReason.TIMEOUT,
                session_id=self.session_id,
                agent_id=self.agent_id,
            )

    async def _execute_step(self) -> StepResult:
        """Execute a single step of the vision loop."""
        from sakhi.apps.api.services.agent.screen_analyzer import analyze_screen
        from sakhi.apps.api.services.agent.action_decider import decide_next_action

        self.state.current_step += 1
        self.state.last_step_at = datetime.utcnow()

        await update_session_step(
            self.session_id,
            self.state.current_step,
            self.max_steps,
        )

        LOGGER.debug(
            "[vision_loop] Step %d/%d",
            self.state.current_step,
            self.max_steps,
        )

        try:
            # 1. Get latest screenshot from agent
            screenshot = await get_latest_screenshot(self.session_id)

            if not screenshot:
                return StepResult(
                    success=False,
                    error="No screenshot available",
                )

            if self.on_screenshot:
                self.on_screenshot(screenshot["id"])

            # 2. Analyze what's on screen
            analysis = await analyze_screen(
                screenshot_path=screenshot["storage_path"],
                width=screenshot["width"],
                height=screenshot["height"],
                task_context=self.state.task_description,
                previous_actions=self._get_action_history(),
            )

            self.state.last_screen_analysis = analysis

            # Update session with screen understanding
            await update_session_screen(self.session_id, analysis)

            # Update screenshot with analysis
            await update_screenshot_analysis(
                screenshot["id"],
                ScreenUnderstanding(
                    description=analysis.get("description", ""),
                    detected_elements=analysis.get("elements", []),
                    ocr_text=analysis.get("text", ""),
                    current_app=analysis.get("app"),
                    current_url=analysis.get("url"),
                    confidence=analysis.get("confidence", 0.5),
                ),
            )

            # 3. Decide what action to take
            decision = await decide_next_action(
                task_description=self.state.task_description,
                task_context=self.state.task_context,
                screen_analysis=analysis,
                action_history=self._get_action_history(),
                step_number=self.state.current_step,
            )

            # 4. Check if task is complete
            if decision.get("is_complete"):
                return StepResult(
                    success=True,
                    screen_analysis=analysis,
                    reasoning=decision.get("reasoning"),
                    is_complete=True,
                )

            # 5. Check if action requires approval
            action = decision.get("action")
            if action:
                # Import approval system
                from sakhi.apps.api.services.agent.action_approval import (
                    requires_approval,
                    request_action_approval,
                    get_approval_manager,
                )

                action_type = action["type"]
                action_params = action.get("parameters", {})
                action_desc = action.get("description", "")

                # Check if this action needs user approval
                if self.require_approval and requires_approval(
                    action_type=action_type,
                    action_parameters=action_params,
                    button_text=action_desc,
                ):
                    # Request approval
                    LOGGER.info(
                        "[vision_loop] Action '%s' requires approval",
                        action_type,
                    )

                    self.state.status = LoopStatus.WAITING_APPROVAL
                    self._waiting_approval = True
                    self.state.approvals_requested += 1

                    # Create approval request
                    approval_request = await request_action_approval(
                        session_id=self.session_id,
                        task_id=self.state.task_context.get("task_id", ""),
                        person_id=self.person_id,
                        action_type=action_type,
                        action_parameters=action_params,
                        action_description=action_desc,
                        context_summary=decision.get("reasoning", ""),
                        screenshot_id=screenshot.get("id") if screenshot else None,
                    )

                    self.state.pending_approval_id = approval_request.request_id

                    # Notify via callback (for chat integration)
                    if self.on_approval_needed:
                        self.on_approval_needed({
                            "request_id": approval_request.request_id,
                            "action_type": action_type,
                            "action_description": action_desc,
                            "context": decision.get("reasoning"),
                            "options": approval_request.options,
                            "risk_level": approval_request.risk_level.value,
                        })

                    # Wait for approval
                    manager = get_approval_manager()
                    resolved_request = await manager.wait_for_approval(
                        approval_request.request_id,
                        timeout=300,  # 5 minutes
                    )

                    self._waiting_approval = False

                    if resolved_request.status.value == "approved":
                        self.state.approvals_granted += 1
                        self.state.status = LoopStatus.RUNNING
                        LOGGER.info("[vision_loop] Action approved, executing")
                        # Continue to execute below
                    elif resolved_request.status.value == "rejected":
                        self.state.approvals_rejected += 1
                        self.state.status = LoopStatus.RUNNING
                        self.state.pending_approval_id = None
                        LOGGER.info("[vision_loop] Action rejected by user")
                        return StepResult(
                            success=False,
                            screen_analysis=analysis,
                            reasoning="User rejected the action",
                            needs_approval=True,
                            approval_request_id=approval_request.request_id,
                            approval_status="rejected",
                        )
                    else:  # expired
                        self.state.status = LoopStatus.RUNNING
                        self.state.pending_approval_id = None
                        LOGGER.info("[vision_loop] Approval request expired")
                        return StepResult(
                            success=False,
                            screen_analysis=analysis,
                            reasoning="Approval request timed out",
                            needs_approval=True,
                            approval_request_id=approval_request.request_id,
                            approval_status="expired",
                        )

                    self.state.pending_approval_id = None

                # Execute the action (either no approval needed, or was approved)
                action_obj = AgentAction(
                    action_id=f"step_{self.state.current_step}",
                    action_type=ActionType(action["type"]),
                    parameters=action.get("parameters", {}),
                    sequence=self.state.current_step,
                    description=action.get("description"),
                )

                await self._execute_action(action_obj)

                self.state.actions_executed += 1
                self._record_action({
                    "type": action["type"],
                    "parameters": action.get("parameters", {}),
                    "reasoning": decision.get("reasoning"),
                })

                return StepResult(
                    success=True,
                    action_taken=action_obj,
                    screen_analysis=analysis,
                    reasoning=decision.get("reasoning"),
                )
            else:
                return StepResult(
                    success=False,
                    screen_analysis=analysis,
                    error="No action decided",
                )

        except Exception as e:
            LOGGER.exception("[vision_loop] Step %d failed: %s", self.state.current_step, e)
            return StepResult(
                success=False,
                error=str(e),
            )

    async def _execute_action(self, action: AgentAction) -> None:
        """Queue an action for the agent to execute."""
        await queue_action(
            session_id=self.session_id,
            agent_id=self.agent_id,
            person_id=self.person_id,
            action=action,
        )

        LOGGER.debug(
            "[vision_loop] Queued action: %s %s",
            action.action_type.value,
            action.parameters,
        )

    def _get_action_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent action history for context.

        Maintains full history but returns only recent actions for LLM context.

        Args:
            limit: Maximum number of recent actions to return

        Returns:
            List of recent action records
        """
        if not self.state or not self.state.action_history:
            return []

        # Return most recent actions up to limit
        return self.state.action_history[-limit:]

    def _record_action(self, action: Dict[str, Any]) -> None:
        """
        Record an action to history.

        Maintains history with optional compaction if too large.
        """
        if not self.state:
            return

        self.state.action_history.append({
            **action,
            "step": self.state.current_step,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.state.last_action = action

        # Compact history if too large (keep last 50 actions)
        MAX_HISTORY = 50
        if len(self.state.action_history) > MAX_HISTORY:
            # Keep first 5 (context) and last 45 (recent)
            self.state.action_history = (
                self.state.action_history[:5] +
                self.state.action_history[-(MAX_HISTORY - 5):]
            )

    async def _notify_agent_session_start(self, task_description: str) -> None:
        """
        Notify the desktop agent to start this session.

        This queues a command that will be delivered to the agent
        on their next heartbeat or poll.
        """
        from sakhi.apps.api.services.agent.actions import queue_agent_command

        try:
            await queue_agent_command(
                agent_id=self.agent_id,
                command="start_session",
                parameters={
                    "session_id": self.session_id,
                    "task_description": task_description,
                },
            )
            LOGGER.info(
                "[vision_loop] Queued start_session command for agent %s",
                self.agent_id,
            )
        except Exception as e:
            LOGGER.warning(
                "[vision_loop] Failed to queue start command: %s",
                e,
            )

    async def _wait_for_screenshot(
        self,
        timeout_seconds: int = 60,
        poll_interval: float = 2.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for the desktop agent to send a screenshot.

        Polls the database until a screenshot appears or timeout.

        Args:
            timeout_seconds: Max time to wait for a screenshot
            poll_interval: Seconds between polls

        Returns:
            Screenshot info or None if timed out
        """
        deadline = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        attempts = 0

        LOGGER.info(
            "[vision_loop] Waiting for screenshot (timeout=%ds)...",
            timeout_seconds,
        )

        while datetime.utcnow() < deadline:
            attempts += 1
            screenshot = await get_latest_screenshot(self.session_id)

            if screenshot:
                LOGGER.info(
                    "[vision_loop] Got screenshot after %d attempts (%.1fs)",
                    attempts,
                    attempts * poll_interval,
                )
                return screenshot

            # Log progress periodically
            if attempts % 5 == 0:
                LOGGER.debug(
                    "[vision_loop] Still waiting for screenshot... (attempt %d)",
                    attempts,
                )

            await asyncio.sleep(poll_interval)

        LOGGER.warning(
            "[vision_loop] Timed out waiting for screenshot after %d attempts",
            attempts,
        )
        return None


# =============================================================================
# Convenience Functions
# =============================================================================

async def start_vision_loop(
    session_id: str,
    agent_id: str,
    person_id: str,
    task_description: str,
    *,
    starting_url: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    max_steps: int = 50,
) -> VisionLoopState:
    """
    Start a vision loop for a task.

    This is the main entry point for autonomous browsing.

    Args:
        session_id: Agent session ID
        agent_id: Registered agent ID
        person_id: User's person ID
        task_description: What to accomplish
        starting_url: Optional URL to start at
        context: Optional context (preferences, etc.)
        max_steps: Maximum steps before stopping

    Returns:
        Final loop state
    """
    loop = VisionLoop(
        session_id=session_id,
        agent_id=agent_id,
        person_id=person_id,
        max_steps=max_steps,
    )

    return await loop.start(
        task_description,
        initial_context=context,
        starting_url=starting_url,
    )


async def run_vision_task(
    person_id: str,
    agent_id: str,
    task: str,
    *,
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    High-level function to run a complete vision task.

    Creates a session, runs the vision loop, and returns results.

    Args:
        person_id: User's person ID
        agent_id: Registered agent ID
        task: Task description in natural language
        preferences: User preferences to consider

    Returns:
        Task result with status and any gathered information
    """
    from sakhi.apps.api.services.agent.sessions import create_session
    from sakhi.apps.api.services.agent.protocol import SessionRequest

    # Create session
    session = await create_session(
        person_id=person_id,
        agent_id=agent_id,
        request=SessionRequest(task_description=task),
    )

    # Build context from preferences
    context = {}
    if preferences:
        context["preferences"] = preferences

    # Run the loop
    state = await start_vision_loop(
        session_id=session.id,
        agent_id=agent_id,
        person_id=person_id,
        task_description=task,
        context=context,
    )

    return {
        "session_id": session.id,
        "status": state.status.value,
        "steps_taken": state.current_step,
        "actions_executed": state.actions_executed,
        "errors": state.errors,
        "completed": state.status == LoopStatus.COMPLETED,
    }


__all__ = [
    "LoopStatus",
    "VisionLoopState",
    "StepResult",
    "VisionLoop",
    "start_vision_loop",
    "run_vision_task",
]
