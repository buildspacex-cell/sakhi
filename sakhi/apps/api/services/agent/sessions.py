"""
Agent Session Service
---------------------
Manages agent registration, heartbeats, and sessions.
"""

from __future__ import annotations

import json
import logging
import hashlib
import secrets
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.services.agent.protocol import (
    AgentRegistration,
    AgentRegistrationResponse,
    AgentHeartbeat,
    HeartbeatResponse,
    SessionRequest,
    SessionResponse,
    SessionStatus,
    AgentStatus,
    AgentCapability,
    UpdateInfo,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Agent Models
# =============================================================================

class RegisteredAgent(BaseModel):
    """A registered agent."""
    id: str
    person_id: str
    agent_name: str
    agent_type: str
    device_id: str
    agent_version: str
    protocol_version: str
    capabilities: List[str] = []
    approved_capabilities: List[str] = []
    platform: str
    platform_version: Optional[str] = None
    status: str = "registered"
    last_heartbeat_at: Optional[datetime] = None


class AgentSession(BaseModel):
    """An active agent session."""
    id: str
    person_id: str
    agent_id: str
    status: str
    task_description: Optional[str] = None
    current_step: int = 0
    total_steps: Optional[int] = None
    actions_executed: int = 0
    started_at: datetime


# =============================================================================
# Agent Registration
# =============================================================================

async def register_agent(
    person_id: str,
    registration: AgentRegistration,
) -> AgentRegistrationResponse:
    """
    Register a new agent or update existing one.

    Returns auth token for future requests.
    """
    # Hash device_id for storage
    device_hash = hashlib.sha256(registration.device_id.encode()).hexdigest()[:32]

    # Generate auth token
    auth_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(auth_token.encode()).hexdigest()

    capabilities_list = [c.value if isinstance(c, AgentCapability) else c for c in registration.capabilities]

    # Auto-approve low-risk capabilities
    low_risk = ["screen_capture", "mouse_move", "scroll", "browser_navigate", "clipboard_write"]
    auto_approved = [c for c in capabilities_list if c in low_risk]

    # Check for existing agent
    existing = await dbfetch(
        """
        SELECT id, capabilities, approved_capabilities
        FROM registered_agents
        WHERE person_id = $1 AND device_id = $2
        """,
        person_id,
        device_hash,
        one=True,
    )

    if existing:
        # Update existing agent
        await dbexec(
            """
            UPDATE registered_agents
            SET agent_name = $3,
                agent_version = $4,
                protocol_version = $5,
                capabilities = $6::jsonb,
                platform_version = $7,
                architecture = $8,
                auth_token_hash = $9,
                status = 'registered',
                updated_at = NOW()
            WHERE id = $2
            """,
            person_id,
            existing["id"],
            registration.agent_name,
            registration.agent_version,
            registration.protocol_version,
            json.dumps(capabilities_list),
            registration.platform_version,
            registration.architecture,
            token_hash,
        )

        agent_id = str(existing["id"])
        approved = existing.get("approved_capabilities") or []

        LOGGER.info("[agent] Updated registration: %s for person %s", agent_id, person_id)

    else:
        # Create new agent (with ON CONFLICT for re-registration)
        row = await dbfetch(
            """
            INSERT INTO registered_agents (
                person_id, agent_name, agent_type, device_id,
                agent_version, protocol_version, capabilities,
                platform, platform_version, architecture,
                auth_token_hash, approved_capabilities
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11, $12::jsonb)
            ON CONFLICT (person_id, device_id) DO UPDATE SET
                agent_name = EXCLUDED.agent_name,
                agent_version = EXCLUDED.agent_version,
                protocol_version = EXCLUDED.protocol_version,
                capabilities = EXCLUDED.capabilities,
                auth_token_hash = EXCLUDED.auth_token_hash,
                status = 'registered',
                updated_at = NOW()
            RETURNING id, approved_capabilities
            """,
            person_id,
            registration.agent_name,
            registration.agent_type,
            device_hash,
            registration.agent_version,
            registration.protocol_version,
            json.dumps(capabilities_list),
            registration.platform,
            registration.platform_version,
            registration.architecture,
            token_hash,
            json.dumps(auto_approved),
            one=True,
        )

        agent_id = str(row["id"])
        # Use existing approved_capabilities if this was an update
        approved = row.get("approved_capabilities") or auto_approved

        LOGGER.info("[agent] Registered: %s (%s) for person %s", agent_id, registration.agent_name, person_id)

    # Check for pending approvals
    pending = [c for c in capabilities_list if c not in approved]

    # Check for updates
    update_info = await check_agent_update(
        agent_type=registration.agent_type,
        platform=registration.platform,
        current_version=registration.agent_version,
        architecture=registration.architecture,
    )

    return AgentRegistrationResponse(
        agent_id=agent_id,
        auth_token=auth_token,
        status="registered",
        approved_capabilities=approved,
        pending_approval=pending,
        update_available=update_info.has_update if update_info else False,
        latest_version=update_info.latest_version if update_info else None,
    )


def _parse_json_field(value: Any) -> list:
    """Parse a JSON field that may be a string or list."""
    if value is None:
        return []
    if isinstance(value, str):
        return json.loads(value)
    return value


async def get_agent(agent_id: str) -> Optional[RegisteredAgent]:
    """Get agent by ID."""
    row = await dbfetch(
        "SELECT * FROM registered_agents WHERE id = $1",
        agent_id,
        one=True,
    )

    if not row:
        return None

    return RegisteredAgent(
        id=str(row["id"]),
        person_id=row["person_id"],
        agent_name=row["agent_name"],
        agent_type=row["agent_type"],
        device_id=row["device_id"],
        agent_version=row["agent_version"],
        protocol_version=row["protocol_version"],
        capabilities=_parse_json_field(row.get("capabilities")),
        approved_capabilities=_parse_json_field(row.get("approved_capabilities")),
        platform=row["platform"],
        platform_version=row.get("platform_version"),
        status=row["status"],
        last_heartbeat_at=row.get("last_heartbeat_at"),
    )


async def get_agents_for_person(person_id: str) -> List[RegisteredAgent]:
    """Get all agents for a person."""
    rows = await dbfetch(
        """
        SELECT * FROM registered_agents
        WHERE person_id = $1
        ORDER BY updated_at DESC
        """,
        person_id,
    )

    return [
        RegisteredAgent(
            id=str(row["id"]),
            person_id=row["person_id"],
            agent_name=row["agent_name"],
            agent_type=row["agent_type"],
            device_id=row["device_id"],
            agent_version=row["agent_version"],
            protocol_version=row["protocol_version"],
            capabilities=_parse_json_field(row.get("capabilities")),
            approved_capabilities=_parse_json_field(row.get("approved_capabilities")),
            platform=row["platform"],
            platform_version=row.get("platform_version"),
            status=row["status"],
            last_heartbeat_at=row.get("last_heartbeat_at"),
        )
        for row in (rows or [])
    ]


async def verify_agent_token(agent_id: str, token: str) -> bool:
    """Verify agent auth token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    row = await dbfetch(
        "SELECT 1 FROM registered_agents WHERE id = $1 AND auth_token_hash = $2",
        agent_id,
        token_hash,
        one=True,
    )

    return bool(row)


# =============================================================================
# Heartbeat
# =============================================================================

async def update_agent_heartbeat(
    heartbeat: AgentHeartbeat,
) -> HeartbeatResponse:
    """
    Process agent heartbeat.

    Updates status and returns any pending work.
    """
    from sakhi.apps.api.services.agent.actions import get_pending_commands

    # Update heartbeat timestamp
    await dbexec(
        """
        UPDATE registered_agents
        SET status = $2,
            last_heartbeat_at = NOW(),
            updated_at = NOW()
        WHERE id = $1
        """,
        heartbeat.agent_id,
        heartbeat.status,
    )

    # Check for pending actions
    pending_count = await dbfetch(
        """
        SELECT COUNT(*) as count
        FROM agent_actions a
        JOIN agent_sessions s ON s.id = a.session_id
        WHERE a.agent_id = $1
          AND a.status = 'pending'
          AND s.status = 'active'
        """,
        heartbeat.agent_id,
        one=True,
    )

    pending_actions = (pending_count or {}).get("count", 0)

    # Get any pending commands for this agent
    commands = await get_pending_commands(heartbeat.agent_id)

    # Check for updates
    agent = await get_agent(heartbeat.agent_id)
    update_info = None
    if agent:
        update_info = await check_agent_update(
            agent_type=agent.agent_type,
            platform=agent.platform,
            current_version=agent.agent_version,
        )

    return HeartbeatResponse(
        acknowledged=True,
        has_pending_actions=pending_actions > 0,
        pending_action_count=pending_actions,
        update_available=update_info.has_update if update_info else False,
        update_mandatory=update_info.is_mandatory if update_info else False,
        latest_version=update_info.latest_version if update_info else None,
        commands=commands,  # Include pending commands
    )


# =============================================================================
# Sessions
# =============================================================================

async def create_session(
    person_id: str,
    agent_id: str,
    request: SessionRequest,
) -> AgentSession:
    """
    Create a new agent session.

    A session represents a task the user wants to accomplish.
    """
    # End any existing active sessions
    await dbexec(
        """
        UPDATE agent_sessions
        SET status = 'cancelled', completed_at = NOW()
        WHERE agent_id = $1 AND status = 'active'
        """,
        agent_id,
    )

    # Set timeout (30 minutes default)
    timeout = datetime.utcnow() + timedelta(minutes=30)

    row = await dbfetch(
        """
        INSERT INTO agent_sessions (
            person_id, agent_id, task_description, timeout_at
        )
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        person_id,
        agent_id,
        request.task_description,
        timeout,
        one=True,
    )

    LOGGER.info(
        "[agent] Created session %s for task: %s",
        row["id"],
        request.task_description[:50],
    )

    return AgentSession(
        id=str(row["id"]),
        person_id=row["person_id"],
        agent_id=str(row["agent_id"]),
        status=row["status"],
        task_description=row["task_description"],
        current_step=row.get("current_step", 0),
        total_steps=row.get("total_steps"),
        actions_executed=row.get("actions_executed", 0),
        started_at=row["started_at"],
    )


async def get_active_session(agent_id: str) -> Optional[AgentSession]:
    """Get active session for an agent."""
    row = await dbfetch(
        """
        SELECT * FROM agent_sessions
        WHERE agent_id = $1 AND status = 'active'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        agent_id,
        one=True,
    )

    if not row:
        return None

    return AgentSession(
        id=str(row["id"]),
        person_id=row["person_id"],
        agent_id=str(row["agent_id"]),
        status=row["status"],
        task_description=row.get("task_description"),
        current_step=row.get("current_step", 0),
        total_steps=row.get("total_steps"),
        actions_executed=row.get("actions_executed", 0),
        started_at=row["started_at"],
    )


async def get_session(session_id: str) -> Optional[AgentSession]:
    """Get session by ID."""
    row = await dbfetch(
        "SELECT * FROM agent_sessions WHERE id = $1",
        session_id,
        one=True,
    )

    if not row:
        return None

    return AgentSession(
        id=str(row["id"]),
        person_id=row["person_id"],
        agent_id=str(row["agent_id"]),
        status=row["status"],
        task_description=row.get("task_description"),
        current_step=row.get("current_step", 0),
        total_steps=row.get("total_steps"),
        actions_executed=row.get("actions_executed", 0),
        started_at=row["started_at"],
    )


async def update_session_step(
    session_id: str,
    current_step: int,
    total_steps: Optional[int] = None,
) -> None:
    """Update session progress."""
    if total_steps is not None:
        await dbexec(
            """
            UPDATE agent_sessions
            SET current_step = $2, total_steps = $3, updated_at = NOW()
            WHERE id = $1
            """,
            session_id,
            current_step,
            total_steps,
        )
    else:
        await dbexec(
            """
            UPDATE agent_sessions
            SET current_step = $2, updated_at = NOW()
            WHERE id = $1
            """,
            session_id,
            current_step,
        )


async def update_session_screen(
    session_id: str,
    screen_understanding: Dict[str, Any],
) -> None:
    """Update session with screen understanding."""
    import json

    await dbexec(
        """
        UPDATE agent_sessions
        SET screen_understanding = $2::jsonb,
            last_screenshot_at = NOW(),
            updated_at = NOW()
        WHERE id = $1
        """,
        session_id,
        json.dumps(screen_understanding),
    )


async def end_session(
    session_id: str,
    status: SessionStatus = SessionStatus.COMPLETED,
) -> None:
    """End an agent session."""
    await dbexec(
        """
        UPDATE agent_sessions
        SET status = $2, completed_at = NOW(), updated_at = NOW()
        WHERE id = $1
        """,
        session_id,
        status.value,
    )

    LOGGER.info("[agent] Ended session %s with status: %s", session_id, status.value)


# =============================================================================
# Updates
# =============================================================================

async def check_agent_update(
    agent_type: str,
    platform: str,
    current_version: str,
    architecture: Optional[str] = None,
) -> Optional[UpdateInfo]:
    """Check if an agent update is available."""
    try:
        # Use empty string as sentinel for NULL architecture to avoid type inference issues
        arch_param = architecture or ''
        row = await dbfetch(
            """
            SELECT
                version != $3 as has_update,
                version as latest_version,
                download_url,
                checksum,
                file_size_bytes,
                is_mandatory,
                release_notes,
                min_required_version
            FROM agent_versions
            WHERE agent_type = $1
              AND platform = $2
              AND status = 'active'
              AND ($4 = '' OR architecture = $4 OR architecture = 'universal')
            ORDER BY released_at DESC
            LIMIT 1
            """,
            agent_type,
            platform,
            current_version,
            arch_param,
            one=True,
        )

        if not row:
            return UpdateInfo(has_update=False)

        return UpdateInfo(
            has_update=row.get("has_update", False),
            latest_version=row.get("latest_version"),
            download_url=row.get("download_url"),
            checksum=row.get("checksum"),
            file_size_bytes=row.get("file_size_bytes"),
            is_mandatory=row.get("is_mandatory", False),
            release_notes=row.get("release_notes"),
            min_required_version=row.get("min_required_version"),
        )
    except Exception as e:
        # Table may not exist yet - return no update available
        LOGGER.warning("[agent] Update check failed (table may not exist): %s", e)
        return UpdateInfo(has_update=False)


async def approve_capability(
    agent_id: str,
    capability: str,
) -> bool:
    """Approve a capability for an agent."""
    await dbexec(
        """
        UPDATE registered_agents
        SET approved_capabilities = approved_capabilities || $2::jsonb,
            updated_at = NOW()
        WHERE id = $1
          AND NOT (approved_capabilities ? $3)
        """,
        agent_id,
        [capability],
        capability,
    )
    return True


async def revoke_capability(
    agent_id: str,
    capability: str,
) -> bool:
    """Revoke a capability from an agent."""
    await dbexec(
        """
        UPDATE registered_agents
        SET approved_capabilities = approved_capabilities - $2,
            updated_at = NOW()
        WHERE id = $1
        """,
        agent_id,
        capability,
    )
    return True


__all__ = [
    "RegisteredAgent",
    "AgentSession",
    "register_agent",
    "get_agent",
    "get_agents_for_person",
    "verify_agent_token",
    "update_agent_heartbeat",
    "create_session",
    "get_active_session",
    "get_session",
    "update_session_step",
    "update_session_screen",
    "end_session",
    "check_agent_update",
    "approve_capability",
    "revoke_capability",
]
