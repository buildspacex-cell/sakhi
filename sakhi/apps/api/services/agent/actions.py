"""
Agent Actions Service
---------------------
Manages action queuing, execution, and results.
"""

from __future__ import annotations

import logging
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.services.agent.protocol import (
    AgentAction,
    ActionType,
    ActionStatus,
    ActionResult,
    ScreenCapture,
    ScreenUnderstanding,
)

LOGGER = logging.getLogger(__name__)


def _parse_json_field(value: Any, default: Any = None) -> Any:
    """Parse a JSON field that may be a string or already parsed."""
    if value is None:
        return default if default is not None else {}
    if isinstance(value, str):
        return json.loads(value)
    return value


# =============================================================================
# Action Models
# =============================================================================

class QueuedAction(BaseModel):
    """An action queued for execution."""
    id: str
    session_id: str
    agent_id: str
    action_type: str
    parameters: Dict[str, Any] = {}
    status: str
    sequence: int
    requires_approval: bool = False
    approved: bool = False
    description: Optional[str] = None


# =============================================================================
# Queue Actions
# =============================================================================

async def queue_action(
    session_id: str,
    agent_id: str,
    person_id: str,
    action: AgentAction,
) -> str:
    """
    Queue an action for agent execution.

    Returns the action ID.
    """
    # Determine if action requires approval
    high_risk_actions = [
        ActionType.SHORTCUT.value,  # Could delete files, etc.
    ]
    requires_approval = action.action_type.value in high_risk_actions

    row = await dbfetch(
        """
        INSERT INTO agent_actions (
            session_id, agent_id, person_id,
            action_type, parameters, requires_approval,
            sequence, status
        )
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, 'pending')
        RETURNING id
        """,
        session_id,
        agent_id,
        person_id,
        action.action_type.value,
        json.dumps(action.parameters),
        requires_approval,
        action.sequence,
        one=True,
    )

    action_id = str(row["id"])

    LOGGER.info(
        "[agent] Queued action %s: %s (session=%s)",
        action_id,
        action.action_type.value,
        session_id,
    )

    return action_id


async def queue_action_batch(
    session_id: str,
    agent_id: str,
    person_id: str,
    actions: List[AgentAction],
) -> List[str]:
    """Queue multiple actions at once."""
    action_ids = []

    for i, action in enumerate(actions):
        # Set sequence if not already set
        if action.sequence == 0:
            action.sequence = i + 1

        action_id = await queue_action(
            session_id=session_id,
            agent_id=agent_id,
            person_id=person_id,
            action=action,
        )
        action_ids.append(action_id)

    return action_ids


async def get_pending_actions(
    agent_id: str,
    limit: int = 10,
) -> List[QueuedAction]:
    """
    Get pending actions for an agent.

    Only returns actions that:
    - Are in pending status
    - Have active sessions
    - Are approved (if approval required)
    """
    rows = await dbfetch(
        """
        SELECT
            a.id,
            a.session_id,
            a.agent_id,
            a.action_type,
            a.parameters,
            a.status,
            a.sequence,
            a.requires_approval,
            a.approved_at IS NOT NULL as approved
        FROM agent_actions a
        JOIN agent_sessions s ON s.id = a.session_id
        WHERE a.agent_id = $1
          AND a.status = 'pending'
          AND s.status = 'active'
          AND (a.requires_approval = false OR a.approved_at IS NOT NULL)
        ORDER BY a.sequence ASC, a.created_at ASC
        LIMIT $2
        """,
        agent_id,
        limit,
    )

    return [
        QueuedAction(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            agent_id=str(row["agent_id"]),
            action_type=row["action_type"],
            parameters=_parse_json_field(row.get("parameters"), {}),
            status=row["status"],
            sequence=row.get("sequence", 0),
            requires_approval=row.get("requires_approval", False),
            approved=row.get("approved", False),
        )
        for row in (rows or [])
    ]


async def get_action(action_id: str) -> Optional[QueuedAction]:
    """Get an action by ID."""
    row = await dbfetch(
        """
        SELECT
            id, session_id, agent_id, action_type, parameters,
            status, sequence, requires_approval, approved_at IS NOT NULL as approved
        FROM agent_actions
        WHERE id = $1
        """,
        action_id,
        one=True,
    )

    if not row:
        return None

    return QueuedAction(
        id=str(row["id"]),
        session_id=str(row["session_id"]),
        agent_id=str(row["agent_id"]),
        action_type=row["action_type"],
        parameters=_parse_json_field(row.get("parameters"), {}),
        status=row["status"],
        sequence=row.get("sequence", 0),
        requires_approval=row.get("requires_approval", False),
        approved=row.get("approved", False),
    )


# =============================================================================
# Action Status Updates
# =============================================================================

async def mark_action_sent(action_id: str) -> None:
    """Mark action as sent to agent."""
    await dbexec(
        """
        UPDATE agent_actions
        SET status = 'sent', sent_at = NOW()
        WHERE id = $1
        """,
        action_id,
    )


async def mark_action_executing(action_id: str) -> None:
    """Mark action as currently executing."""
    await dbexec(
        """
        UPDATE agent_actions
        SET status = 'executing', started_at = NOW()
        WHERE id = $1
        """,
        action_id,
    )


async def mark_action_completed(
    action_id: str,
    result: ActionResult,
) -> None:
    """Mark action as completed with result."""
    await dbexec(
        """
        UPDATE agent_actions
        SET status = 'completed',
            completed_at = NOW(),
            result = $2::jsonb
        WHERE id = $1
        """,
        action_id,
        json.dumps({
            "success": result.success,
            "duration_ms": result.duration_ms,
            "screenshot_id": result.screenshot_id,
            "data": result.data,
        }),
    )

    # Update session action count
    await dbexec(
        """
        UPDATE agent_sessions s
        SET actions_executed = actions_executed + 1,
            updated_at = NOW()
        FROM agent_actions a
        WHERE a.id = $1 AND s.id = a.session_id
        """,
        action_id,
    )

    LOGGER.info("[agent] Action %s completed successfully", action_id)


async def mark_action_failed(
    action_id: str,
    error: str,
    retry: bool = False,
) -> None:
    """Mark action as failed."""
    if retry:
        # Increment retry count and keep pending
        await dbexec(
            """
            UPDATE agent_actions
            SET retry_count = retry_count + 1,
                error_message = $2,
                status = 'pending'
            WHERE id = $1
            """,
            action_id,
            error,
        )
    else:
        await dbexec(
            """
            UPDATE agent_actions
            SET status = 'failed',
                completed_at = NOW(),
                error_message = $2
            WHERE id = $1
            """,
            action_id,
            error,
        )

        # Update session failure count
        await dbexec(
            """
            UPDATE agent_sessions s
            SET actions_failed = actions_failed + 1,
                updated_at = NOW()
            FROM agent_actions a
            WHERE a.id = $1 AND s.id = a.session_id
            """,
            action_id,
        )

    LOGGER.warning("[agent] Action %s failed: %s", action_id, error)


async def cancel_action(action_id: str) -> None:
    """Cancel a pending action."""
    await dbexec(
        """
        UPDATE agent_actions
        SET status = 'cancelled'
        WHERE id = $1 AND status IN ('pending', 'sent')
        """,
        action_id,
    )


async def cancel_session_actions(session_id: str) -> int:
    """Cancel all pending actions for a session."""
    result = await dbfetch(
        """
        UPDATE agent_actions
        SET status = 'cancelled'
        WHERE session_id = $1 AND status IN ('pending', 'sent')
        RETURNING id
        """,
        session_id,
    )

    count = len(result) if result else 0
    LOGGER.info("[agent] Cancelled %d pending actions for session %s", count, session_id)

    return count


# =============================================================================
# Action Approval
# =============================================================================

async def approve_action(
    action_id: str,
    approver: str = "user",
) -> bool:
    """Approve a pending action that requires approval."""
    await dbexec(
        """
        UPDATE agent_actions
        SET approved_at = NOW(), approved_by = $2
        WHERE id = $1 AND requires_approval = true
        """,
        action_id,
        approver,
    )
    return True


async def get_actions_needing_approval(
    person_id: str,
) -> List[QueuedAction]:
    """Get actions that need user approval."""
    rows = await dbfetch(
        """
        SELECT
            a.id, a.session_id, a.agent_id, a.action_type, a.parameters,
            a.status, a.sequence, a.requires_approval
        FROM agent_actions a
        JOIN agent_sessions s ON s.id = a.session_id
        WHERE a.person_id = $1
          AND a.requires_approval = true
          AND a.approved_at IS NULL
          AND a.status = 'pending'
          AND s.status = 'active'
        ORDER BY a.created_at ASC
        """,
        person_id,
    )

    return [
        QueuedAction(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            agent_id=str(row["agent_id"]),
            action_type=row["action_type"],
            parameters=row.get("parameters") or {},
            status=row["status"],
            sequence=row.get("sequence", 0),
            requires_approval=True,
            approved=False,
        )
        for row in (rows or [])
    ]


# =============================================================================
# Screenshots
# =============================================================================

async def store_screenshot(
    capture: ScreenCapture,
    person_id: str,
    storage_path: str,
) -> str:
    """Store a screenshot from an agent."""
    row = await dbfetch(
        """
        INSERT INTO agent_screenshots (
            session_id, agent_id, person_id,
            storage_path, width, height, format,
            trigger, preceding_action_id, captured_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
        """,
        capture.session_id,
        capture.agent_id,
        person_id,
        storage_path,
        capture.width,
        capture.height,
        capture.format,
        capture.trigger,
        capture.preceding_action_id,
        capture.captured_at,
        one=True,
    )

    return str(row["id"])


async def update_screenshot_analysis(
    screenshot_id: str,
    analysis: ScreenUnderstanding,
) -> None:
    """Update screenshot with vision analysis."""
    await dbexec(
        """
        UPDATE agent_screenshots
        SET analysis = $2::jsonb, analyzed_at = NOW()
        WHERE id = $1
        """,
        screenshot_id,
        json.dumps({
            "description": analysis.description,
            "detected_elements": analysis.detected_elements,
            "ocr_text": analysis.ocr_text,
            "current_app": analysis.current_app,
            "current_url": analysis.current_url,
            "confidence": analysis.confidence,
        }),
    )


async def get_latest_screenshot(
    session_id: str,
) -> Optional[Dict[str, Any]]:
    """Get the latest screenshot for a session."""
    row = await dbfetch(
        """
        SELECT id, storage_path, width, height, analysis, captured_at
        FROM agent_screenshots
        WHERE session_id = $1
        ORDER BY captured_at DESC
        LIMIT 1
        """,
        session_id,
        one=True,
    )

    if not row:
        return None

    return {
        "id": str(row["id"]),
        "storage_path": row["storage_path"],
        "width": row["width"],
        "height": row["height"],
        "analysis": row.get("analysis") or {},
        "captured_at": str(row["captured_at"]),
    }


# =============================================================================
# Action Generation from Task
# =============================================================================

async def generate_actions_for_task(
    task_description: str,
    screen_context: Optional[ScreenUnderstanding] = None,
) -> List[AgentAction]:
    """
    Use LLM to generate actions for a task.

    This is the "brain" part - understanding what needs to be done
    and generating the specific actions.
    """
    from sakhi.apps.api.core.llm import get_router

    # Build context
    context = f"Task: {task_description}\n\n"

    if screen_context:
        context += f"Current screen: {screen_context.description}\n"
        if screen_context.detected_elements:
            context += "Detected UI elements:\n"
            for elem in screen_context.detected_elements[:10]:
                context += f"  - {elem.get('type')}: {elem.get('text', '')} at {elem.get('bounds', {})}\n"

    prompt = f"""You are controlling a computer to help the user. Generate a list of actions to accomplish the task.

{context}

Available actions:
- click: Click at coordinates {"x", "y"} with optional "button" (left/right)
- type: Type text with "text" parameter
- key: Press a single key like "enter", "tab", "escape"
- shortcut: Press keyboard shortcut with "keys" array like ["cmd", "c"]
- scroll: Scroll with "direction" (up/down) and "amount" (pixels)
- navigate: Go to URL with "url" parameter
- wait: Wait with "ms" parameter

Return a JSON array of actions. Each action should have:
- "action_type": one of the above
- "parameters": the parameters for that action
- "description": human-readable description

Example:
[
    {{"action_type": "navigate", "parameters": {{"url": "https://google.com"}}, "description": "Open Google"}},
    {{"action_type": "click", "parameters": {{"x": 500, "y": 300}}, "description": "Click search box"}},
    {{"action_type": "type", "parameters": {{"text": "weather today"}}, "description": "Type search query"}},
    {{"action_type": "key", "parameters": {{"key": "enter"}}, "description": "Submit search"}}
]

Return ONLY the JSON array, no other text."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model=os.getenv("MODEL_CHAT") or "gpt-4o-mini",
            max_tokens=1000,
        )

        content = response.content[0].text if response.content else "[]"

        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        actions_data = json.loads(content.strip())

        # Convert to AgentAction objects
        actions = []
        for i, a in enumerate(actions_data):
            action_type = a.get("action_type", "wait")
            try:
                action = AgentAction(
                    action_id=str(uuid.uuid4()),
                    action_type=ActionType(action_type),
                    parameters=a.get("parameters", {}),
                    sequence=i + 1,
                    description=a.get("description"),
                )
                actions.append(action)
            except ValueError:
                LOGGER.warning("[agent] Unknown action type: %s", action_type)
                continue

        return actions

    except Exception as e:
        LOGGER.error("[agent] Failed to generate actions: %s", e)
        return []


# =============================================================================
# Agent Commands (Thread-Safe with Optional Persistence)
# =============================================================================

import asyncio
from typing import Tuple

# Thread-safe command queue with lock
_agent_commands: Dict[str, List[Dict[str, Any]]] = {}
_command_lock = asyncio.Lock()

# Configuration
PERSIST_COMMANDS_TO_DB = os.getenv("PERSIST_AGENT_COMMANDS", "false").lower() == "true"


async def queue_agent_command(
    agent_id: str,
    command: str,
    parameters: Dict[str, Any] = None,
    *,
    persist: bool = None,
) -> str:
    """
    Queue a command for the agent to execute.

    Commands are delivered to the agent on their next heartbeat.
    Thread-safe with optional database persistence.

    Args:
        agent_id: Target agent ID
        command: Command name (e.g., "start_session", "take_screenshot")
        parameters: Command parameters
        persist: Override persistence setting (default from env)

    Returns:
        Command ID for tracking
    """
    cmd_id = str(uuid.uuid4())
    cmd = {
        "id": cmd_id,
        "command": command,
        "parameters": parameters or {},
        "queued_at": datetime.utcnow().isoformat(),
    }

    should_persist = persist if persist is not None else PERSIST_COMMANDS_TO_DB

    # Thread-safe in-memory queue
    async with _command_lock:
        if agent_id not in _agent_commands:
            _agent_commands[agent_id] = []
        _agent_commands[agent_id].append(cmd)

    # Optional database persistence
    if should_persist:
        try:
            await dbexec(
                """
                INSERT INTO agent_commands (id, agent_id, command, parameters, status)
                VALUES ($1, $2, $3, $4::jsonb, 'pending')
                """,
                cmd_id,
                agent_id,
                command,
                json.dumps(parameters or {}),
            )
        except Exception as e:
            LOGGER.warning(
                "[agent] Failed to persist command to DB: %s (continuing with in-memory)",
                e,
            )

    LOGGER.info(
        "[agent] Queued command '%s' for agent %s (id=%s)",
        command,
        agent_id,
        cmd_id,
    )

    return cmd_id


async def get_pending_commands(agent_id: str) -> List[Dict[str, Any]]:
    """
    Get and clear pending commands for an agent.

    Commands are removed once retrieved (delivered).
    Thread-safe operation.

    Returns:
        List of pending commands
    """
    # Thread-safe pop from in-memory queue
    async with _command_lock:
        commands = _agent_commands.pop(agent_id, [])

    # Also check database if persistence is enabled
    if PERSIST_COMMANDS_TO_DB:
        try:
            db_commands = await dbfetch(
                """
                UPDATE agent_commands
                SET status = 'delivered', delivered_at = NOW()
                WHERE agent_id = $1 AND status = 'pending'
                RETURNING id, command, parameters, queued_at
                """,
                agent_id,
            )
            if db_commands:
                for row in db_commands:
                    # Avoid duplicates (check by command ID)
                    cmd_id = str(row["id"])
                    if not any(c.get("id") == cmd_id for c in commands):
                        commands.append({
                            "id": cmd_id,
                            "command": row["command"],
                            "parameters": _parse_json_field(row.get("parameters"), {}),
                            "queued_at": str(row["queued_at"]),
                        })
        except Exception as e:
            LOGGER.warning(
                "[agent] Failed to fetch DB commands: %s (using in-memory only)",
                e,
            )

    if commands:
        LOGGER.debug(
            "[agent] Delivering %d commands to agent %s",
            len(commands),
            agent_id,
        )

    return commands


async def get_command_queue_status(agent_id: str) -> Dict[str, Any]:
    """
    Get status of command queue for an agent (for diagnostics).

    Returns:
        Queue status including count and oldest command age
    """
    async with _command_lock:
        commands = _agent_commands.get(agent_id, [])
        count = len(commands)
        oldest_age_ms = 0

        if commands and commands[0].get("queued_at"):
            try:
                queued_at = datetime.fromisoformat(commands[0]["queued_at"])
                oldest_age_ms = int((datetime.utcnow() - queued_at).total_seconds() * 1000)
            except (ValueError, TypeError):
                pass

    return {
        "agent_id": agent_id,
        "pending_count": count,
        "oldest_age_ms": oldest_age_ms,
    }


async def clear_stale_commands(max_age_seconds: int = 300) -> int:
    """
    Clear commands older than max_age_seconds.

    Used to clean up commands for agents that never connected.

    Args:
        max_age_seconds: Maximum age of commands to keep (default 5 minutes)

    Returns:
        Number of commands cleared
    """
    cleared = 0
    cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)

    async with _command_lock:
        for agent_id in list(_agent_commands.keys()):
            original_count = len(_agent_commands[agent_id])
            _agent_commands[agent_id] = [
                cmd for cmd in _agent_commands[agent_id]
                if datetime.fromisoformat(cmd.get("queued_at", "")) > cutoff
            ]
            cleared += original_count - len(_agent_commands[agent_id])

            # Remove empty entries
            if not _agent_commands[agent_id]:
                del _agent_commands[agent_id]

    if cleared > 0:
        LOGGER.info("[agent] Cleared %d stale commands", cleared)

    return cleared


__all__ = [
    "QueuedAction",
    "queue_action",
    "queue_action_batch",
    "get_pending_actions",
    "get_action",
    "mark_action_sent",
    "mark_action_executing",
    "mark_action_completed",
    "mark_action_failed",
    "cancel_action",
    "cancel_session_actions",
    "approve_action",
    "get_actions_needing_approval",
    "store_screenshot",
    "update_screenshot_analysis",
    "get_latest_screenshot",
    "generate_actions_for_task",
    "queue_agent_command",
    "get_pending_commands",
    "get_command_queue_status",
    "clear_stale_commands",
]
