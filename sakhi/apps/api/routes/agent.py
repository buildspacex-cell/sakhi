"""
Agent API Routes
----------------
Endpoints for desktop/mobile agent communication.

These endpoints enable:
1. Agent registration and authentication
2. Session management (start/end tasks)
3. Action queuing and execution
4. Screenshot submission and analysis
5. Auto-update checks
"""

from __future__ import annotations

import logging
import base64
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel, Field

from sakhi.apps.api.deps.auth import get_current_user_id
from sakhi.apps.api.services.agent.protocol import (
    AgentCapability,
    AgentRegistration,
    AgentRegistrationResponse,
    AgentHeartbeat,
    HeartbeatResponse,
    SessionRequest,
    SessionResponse,
    AgentAction,
    ActionResult,
    ScreenCapture,
    ScreenUnderstanding,
    UpdateCheck,
    UpdateInfo,
    ActionType,
    SessionStatus,
)
from sakhi.apps.api.services.agent.sessions import (
    register_agent,
    get_agent,
    get_agents_for_person,
    verify_agent_token,
    update_agent_heartbeat,
    create_session,
    get_active_session,
    get_session,
    update_session_screen,
    end_session,
    check_agent_update,
    approve_capability,
    revoke_capability,
)
from sakhi.apps.api.services.agent.actions import (
    queue_action,
    queue_action_batch,
    get_pending_actions,
    get_action,
    mark_action_sent,
    mark_action_completed,
    mark_action_failed,
    cancel_action,
    cancel_session_actions,
    approve_action,
    get_actions_needing_approval,
    store_screenshot,
    update_screenshot_analysis,
    get_latest_screenshot,
    generate_actions_for_task,
)
from sakhi.apps.api.services.vision.processor import process_image

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

# Storage path for screenshots
SCREENSHOT_STORAGE = os.getenv("AGENT_SCREENSHOT_PATH", "/tmp/sakhi/agent/screenshots")


# =============================================================================
# Authentication Helper
# =============================================================================

async def verify_agent_auth(
    agent_id: str,
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
) -> str:
    """Verify agent authentication token."""
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent token",
        )
    return agent_id


# =============================================================================
# Registration Endpoints
# =============================================================================

@router.post("/register", response_model=AgentRegistrationResponse)
async def register_new_agent(
    registration: AgentRegistration,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Register a new agent or re-register existing one.

    Called when:
    - User installs desktop agent and links to their account
    - Agent starts up and needs to authenticate

    Returns auth token for future requests.
    """
    response = await register_agent(
        person_id=current_user_id,
        registration=registration,
    )

    LOGGER.info(
        "[agent/register] Agent %s registered for user %s",
        response.agent_id,
        current_user_id,
    )

    return response


class AgentListResponse(BaseModel):
    """List of registered agents."""
    agents: List[Dict[str, Any]]


@router.get("/list", response_model=AgentListResponse)
async def list_agents(
    current_user_id: str = Depends(get_current_user_id),
):
    """Get all agents registered to the current user."""
    agents = await get_agents_for_person(current_user_id)

    return AgentListResponse(
        agents=[
            {
                "id": a.id,
                "name": a.agent_name,
                "type": a.agent_type,
                "platform": a.platform,
                "version": a.agent_version,
                "status": a.status,
                "capabilities": a.capabilities,
                "approved_capabilities": a.approved_capabilities,
                "last_heartbeat": str(a.last_heartbeat_at) if a.last_heartbeat_at else None,
            }
            for a in agents
        ]
    )


# =============================================================================
# Heartbeat Endpoints
# =============================================================================

@router.post("/{agent_id}/heartbeat", response_model=HeartbeatResponse)
async def agent_heartbeat(
    agent_id: str,
    heartbeat: AgentHeartbeat,
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
):
    """
    Periodic heartbeat from agent.

    Agent should call this every 30-60 seconds to:
    - Confirm it's still online
    - Check for pending actions
    - Check for updates
    """
    # Verify token
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")

    # Ensure agent_id matches
    heartbeat.agent_id = agent_id

    response = await update_agent_heartbeat(heartbeat)

    return response


# =============================================================================
# Session Endpoints
# =============================================================================

class StartSessionRequest(BaseModel):
    """Request to start a new session."""
    task_description: str = Field(..., description="What the user wants to do")
    target_app: Optional[str] = None
    target_url: Optional[str] = None


class StartSessionResponse(BaseModel):
    """Response with session details and initial actions."""
    session_id: str
    status: str
    plan_summary: Optional[str] = None
    estimated_steps: Optional[int] = None
    initial_actions: List[Dict[str, Any]] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


@router.post("/{agent_id}/session/start", response_model=StartSessionResponse)
async def start_session(
    agent_id: str,
    request: StartSessionRequest,
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Start a new agent session for a task.

    Called when user requests something that needs computer control.
    Returns initial actions to execute.
    """
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")

    # Create session
    session_request = SessionRequest(
        agent_id=agent_id,
        task_description=request.task_description,
        target_app=request.target_app,
        target_url=request.target_url,
    )

    session = await create_session(
        person_id=current_user_id,
        agent_id=agent_id,
        request=session_request,
    )

    # Generate initial actions using LLM
    actions = await generate_actions_for_task(
        task_description=request.task_description,
        screen_context=None,  # No screen context yet
    )

    # Queue actions
    initial_actions = []
    if actions:
        await queue_action_batch(
            session_id=session.id,
            agent_id=agent_id,
            person_id=current_user_id,
            actions=actions,
        )

        initial_actions = [
            {
                "action_id": str(a.action_id),
                "action_type": a.action_type.value,
                "parameters": a.parameters,
                "description": a.description,
                "sequence": a.sequence,
            }
            for a in actions[:5]  # Return first 5 actions
        ]

    LOGGER.info(
        "[agent/session] Started session %s with %d initial actions",
        session.id,
        len(actions),
    )

    return StartSessionResponse(
        session_id=session.id,
        status=session.status,
        plan_summary=f"Will execute {len(actions)} steps to: {request.task_description}",
        estimated_steps=len(actions),
        initial_actions=initial_actions,
        requires_confirmation=len(actions) > 5,
        confirmation_prompt="I've planned the steps. Should I proceed?" if len(actions) > 5 else None,
    )


@router.post("/{agent_id}/session/{session_id}/end")
async def end_agent_session(
    agent_id: str,
    session_id: str,
    status: str = "completed",
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
):
    """End an agent session."""
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")

    try:
        session_status = SessionStatus(status)
    except ValueError:
        session_status = SessionStatus.COMPLETED

    await end_session(session_id, session_status)

    # Cancel any pending actions
    cancelled = await cancel_session_actions(session_id)

    return {
        "success": True,
        "session_id": session_id,
        "status": status,
        "actions_cancelled": cancelled,
    }


@router.get("/{agent_id}/session/current")
async def get_current_session(
    agent_id: str,
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
):
    """Get the current active session for an agent."""
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")

    session = await get_active_session(agent_id)

    if not session:
        return {"active": False, "session": None}

    return {
        "active": True,
        "session": {
            "id": session.id,
            "status": session.status,
            "task_description": session.task_description,
            "current_step": session.current_step,
            "total_steps": session.total_steps,
            "actions_executed": session.actions_executed,
            "started_at": str(session.started_at),
        },
    }


# =============================================================================
# Action Endpoints
# =============================================================================

@router.get("/{agent_id}/actions/pending")
async def get_agent_pending_actions(
    agent_id: str,
    limit: int = 10,
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
):
    """
    Get pending actions for an agent to execute.

    Agent polls this endpoint to get work to do.
    """
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")

    actions = await get_pending_actions(agent_id, limit=limit)

    # Mark actions as sent
    for action in actions:
        await mark_action_sent(action.id)

    return {
        "actions": [
            {
                "action_id": a.id,
                "session_id": a.session_id,
                "action_type": a.action_type,
                "parameters": a.parameters,
                "sequence": a.sequence,
                "description": a.description,
            }
            for a in actions
        ]
    }


class ActionResultRequest(BaseModel):
    """Report action execution result."""
    action_id: str
    success: bool
    error: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    screenshot_base64: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


@router.post("/{agent_id}/actions/result")
async def report_action_result(
    agent_id: str,
    result: ActionResultRequest,
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Report the result of an action execution.

    Agent calls this after executing each action.
    """
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")

    # Get action to verify ownership
    action = await get_action(result.action_id)
    if not action or action.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Handle screenshot if provided
    screenshot_id = None
    if result.screenshot_base64:
        try:
            image_bytes = base64.b64decode(result.screenshot_base64)

            # Save to storage
            os.makedirs(SCREENSHOT_STORAGE, exist_ok=True)
            filename = f"{result.action_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(SCREENSHOT_STORAGE, filename)

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            # Store in database
            capture = ScreenCapture(
                agent_id=agent_id,
                session_id=action.session_id,
                image_base64="",  # Don't store in DB
                format="png",
                width=0,  # Will be updated by analysis
                height=0,
                trigger="action_result",
                preceding_action_id=result.action_id,
                captured_at=result.completed_at,
            )

            screenshot_id = await store_screenshot(
                capture=capture,
                person_id=current_user_id,
                storage_path=filepath,
            )

            # Analyze screenshot with vision
            try:
                analysis = await process_image(
                    image_bytes,
                    mime_type="image/png",
                    context=f"Screenshot after: {action.action_type}",
                )

                understanding = ScreenUnderstanding(
                    screenshot_id=screenshot_id,
                    description=analysis.description,
                    detected_elements=[],  # Could extract from analysis
                    ocr_text=analysis.extracted_text,
                    confidence=0.9,
                )

                await update_screenshot_analysis(screenshot_id, understanding)

                # Update session with screen understanding
                await update_session_screen(
                    action.session_id,
                    {
                        "description": analysis.description,
                        "extracted_text": analysis.extracted_text,
                        "objects": analysis.objects,
                    },
                )

            except Exception as analysis_err:
                LOGGER.warning("[agent] Screenshot analysis failed: %s", analysis_err)

        except Exception as e:
            LOGGER.error("[agent] Failed to save screenshot: %s", e)

    # Create result object
    action_result = ActionResult(
        action_id=result.action_id,
        success=result.success,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_ms=result.duration_ms,
        screenshot_id=screenshot_id,
        data=result.data,
    )

    # Update action status
    if result.success:
        await mark_action_completed(result.action_id, action_result)
    else:
        await mark_action_failed(result.action_id, result.error or "Unknown error")

    # Check if we need to generate more actions
    next_actions = []
    if result.success:
        # Get current session state
        session = await get_session(action.session_id)
        if session and session.status == "active":
            # Check if more actions are needed
            pending = await get_pending_actions(agent_id, limit=1)
            if not pending:
                # No more pending actions - might need to generate more
                # based on current screen state
                latest = await get_latest_screenshot(action.session_id)
                if latest and latest.get("analysis"):
                    # Generate next actions based on screen
                    more_actions = await generate_actions_for_task(
                        task_description=session.task_description or "",
                        screen_context=ScreenUnderstanding(
                            screenshot_id=latest["id"],
                            description=latest["analysis"].get("description", ""),
                            detected_elements=latest["analysis"].get("detected_elements", []),
                        ),
                    )

                    if more_actions:
                        await queue_action_batch(
                            session_id=session.id,
                            agent_id=agent_id,
                            person_id=current_user_id,
                            actions=more_actions,
                        )
                        next_actions = [
                            {
                                "action_id": str(a.action_id),
                                "action_type": a.action_type.value,
                                "parameters": a.parameters,
                            }
                            for a in more_actions[:3]
                        ]

    return {
        "acknowledged": True,
        "action_id": result.action_id,
        "screenshot_id": screenshot_id,
        "next_actions": next_actions,
    }


# =============================================================================
# Screenshot Endpoints
# =============================================================================

class ScreenshotRequest(BaseModel):
    """Submit a screenshot for analysis."""
    image_base64: str
    format: str = "png"
    width: int
    height: int
    session_id: Optional[str] = None
    trigger: str = "user_request"
    current_app: Optional[str] = None


@router.post("/{agent_id}/screenshot")
async def submit_screenshot(
    agent_id: str,
    request: ScreenshotRequest,
    x_agent_token: str = Header(..., alias="X-Agent-Token"),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Submit a screenshot for vision analysis.

    Called when agent captures screen for understanding.
    Returns analysis results.
    """
    if not await verify_agent_token(agent_id, x_agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")

    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    # Save to storage
    os.makedirs(SCREENSHOT_STORAGE, exist_ok=True)
    filename = f"{agent_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(SCREENSHOT_STORAGE, filename)

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    # Store in database
    capture = ScreenCapture(
        agent_id=agent_id,
        session_id=request.session_id,
        image_base64="",
        format=request.format,
        width=request.width,
        height=request.height,
        trigger=request.trigger,
        captured_at=datetime.utcnow(),
        current_app=request.current_app,
    )

    screenshot_id = await store_screenshot(
        capture=capture,
        person_id=current_user_id,
        storage_path=filepath,
    )

    # Analyze with vision
    try:
        analysis = await process_image(
            image_bytes,
            mime_type=f"image/{request.format}",
            context=f"Screen capture from {request.current_app or 'desktop'}",
        )

        understanding = ScreenUnderstanding(
            screenshot_id=screenshot_id,
            description=analysis.description,
            detected_elements=[],
            ocr_text=analysis.extracted_text,
            current_app=request.current_app,
            confidence=0.9,
        )

        await update_screenshot_analysis(screenshot_id, understanding)

        # Update session if active
        if request.session_id:
            await update_session_screen(
                request.session_id,
                {
                    "description": analysis.description,
                    "extracted_text": analysis.extracted_text,
                    "objects": analysis.objects,
                },
            )

        return {
            "screenshot_id": screenshot_id,
            "analysis": {
                "description": analysis.description,
                "extracted_text": analysis.extracted_text,
                "objects": analysis.objects,
                "tags": analysis.tags,
            },
        }

    except Exception as e:
        LOGGER.error("[agent] Screenshot analysis failed: %s", e)
        return {
            "screenshot_id": screenshot_id,
            "analysis": None,
            "error": str(e),
        }


# =============================================================================
# Update Check Endpoints
# =============================================================================

@router.post("/update/check", response_model=UpdateInfo)
async def check_for_update(
    request: UpdateCheck,
):
    """
    Check if an agent update is available.

    Called by agent on startup and periodically.
    """
    update_info = await check_agent_update(
        agent_type=request.agent_type,
        platform=request.platform,
        current_version=request.current_version,
        architecture=request.architecture,
    )

    return update_info or UpdateInfo(has_update=False)


# =============================================================================
# Capability Management
# =============================================================================

class CapabilityRequest(BaseModel):
    """Request to approve/revoke a capability."""
    capability: str


@router.post("/{agent_id}/capabilities/approve")
async def approve_agent_capability(
    agent_id: str,
    request: CapabilityRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Approve a capability for an agent."""
    # Verify ownership
    agent = await get_agent(agent_id)
    if not agent or agent.person_id != current_user_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    await approve_capability(agent_id, request.capability)

    return {"success": True, "capability": request.capability, "status": "approved"}


@router.post("/{agent_id}/capabilities/revoke")
async def revoke_agent_capability(
    agent_id: str,
    request: CapabilityRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Revoke a capability from an agent."""
    agent = await get_agent(agent_id)
    if not agent or agent.person_id != current_user_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    await revoke_capability(agent_id, request.capability)

    return {"success": True, "capability": request.capability, "status": "revoked"}


# =============================================================================
# Approval Queue (for User in App)
# =============================================================================

@router.get("/approvals/pending")
async def get_pending_approvals(
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get actions needing user approval.

    Called by Sakhi App to show approval prompts.
    """
    actions = await get_actions_needing_approval(current_user_id)

    return {
        "pending_approvals": [
            {
                "action_id": a.id,
                "session_id": a.session_id,
                "action_type": a.action_type,
                "parameters": a.parameters,
                "description": a.description,
            }
            for a in actions
        ]
    }


@router.post("/approvals/{action_id}/approve")
async def approve_pending_action(
    action_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """Approve a pending action."""
    action = await get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Verify ownership through session
    session = await get_session(action.session_id)
    if not session or session.person_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await approve_action(action_id, approver="user")

    return {"success": True, "action_id": action_id, "status": "approved"}


@router.post("/approvals/{action_id}/reject")
async def reject_pending_action(
    action_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """Reject a pending action."""
    action = await get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    session = await get_session(action.session_id)
    if not session or session.person_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await cancel_action(action_id)

    return {"success": True, "action_id": action_id, "status": "rejected"}


# =============================================================================
# Device Linking Endpoints
# =============================================================================

# In-memory store for link codes (in production, use Redis or database)
import secrets
from datetime import timedelta

_link_codes: Dict[str, Dict[str, Any]] = {}


class LinkCodeRequest(BaseModel):
    """Request for a new device link code."""
    device_id: str
    platform: str
    architecture: Optional[str] = None
    agent_type: str = "desktop"
    agent_name: Optional[str] = None


class LinkCodeResponse(BaseModel):
    """Response with the link code."""
    code: str
    expires_at: str
    link_url: str


class LinkStatusRequest(BaseModel):
    """Request to check link status."""
    code: str
    device_id: str


class LinkStatusResponse(BaseModel):
    """Response with link status."""
    linked: bool
    agent_id: Optional[str] = None
    auth_token: Optional[str] = None
    person_id: Optional[str] = None
    user_name: Optional[str] = None


class LinkConfirmRequest(BaseModel):
    """Request to confirm a device link (from web app)."""
    code: str


@router.post("/link/request", response_model=LinkCodeResponse)
async def request_link_code(request: LinkCodeRequest):
    """
    Request a new device link code.

    Called by the desktop/mobile agent when user wants to link their device.
    Returns a short code the user enters in the web app.
    """
    # Generate a random 8-character code
    code = secrets.token_hex(4).upper()  # e.g., "A1B2C3D4"

    # Store code with device info
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    _link_codes[code] = {
        "device_id": request.device_id,
        "platform": request.platform,
        "architecture": request.architecture,
        "agent_type": request.agent_type,
        "agent_name": request.agent_name,
        "expires_at": expires_at,
        "linked": False,
        "person_id": None,
        "agent_id": None,
        "auth_token": None,
        "user_name": None,
    }

    # Clean up expired codes
    now = datetime.utcnow()
    expired = [c for c, data in _link_codes.items() if data["expires_at"] < now]
    for c in expired:
        del _link_codes[c]

    LOGGER.info("[agent/link] Created link code %s for device %s", code, request.device_id[:8])

    return LinkCodeResponse(
        code=code,
        expires_at=expires_at.isoformat(),
        link_url=f"https://sakhi.ai/link?code={code}",
    )


@router.post("/link/status", response_model=LinkStatusResponse)
async def check_link_status(request: LinkStatusRequest):
    """
    Check if a link code has been confirmed.

    Called by the desktop/mobile agent to poll for confirmation.
    """
    code = request.code.upper().replace("-", "")

    if code not in _link_codes:
        return LinkStatusResponse(linked=False)

    link_data = _link_codes[code]

    # Check if expired
    if link_data["expires_at"] < datetime.utcnow():
        del _link_codes[code]
        return LinkStatusResponse(linked=False)

    # Check if device ID matches
    if link_data["device_id"] != request.device_id:
        return LinkStatusResponse(linked=False)

    if link_data["linked"]:
        # Return the auth info and clean up
        response = LinkStatusResponse(
            linked=True,
            agent_id=link_data["agent_id"],
            auth_token=link_data["auth_token"],
            person_id=link_data["person_id"],
            user_name=link_data["user_name"],
        )

        # Clean up after successful retrieval
        del _link_codes[code]

        return response

    return LinkStatusResponse(linked=False)


@router.post("/link/confirm")
async def confirm_link(
    request: LinkConfirmRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Confirm a device link from the web app.

    Called when user enters the code in the web app while logged in.
    This completes the linking process.
    """
    code = request.code.upper().replace("-", "")

    if code not in _link_codes:
        raise HTTPException(
            status_code=404,
            detail="Invalid or expired link code",
        )

    link_data = _link_codes[code]

    # Check if expired
    if link_data["expires_at"] < datetime.utcnow():
        del _link_codes[code]
        raise HTTPException(
            status_code=410,
            detail="Link code has expired",
        )

    # Register the agent
    registration = AgentRegistration(
        agent_name=link_data["agent_name"] or f"Desktop Agent",
        agent_type=link_data["agent_type"],
        device_id=link_data["device_id"],
        platform=link_data["platform"],
        agent_version=link_data.get("agent_version", "1.0.0"),
        protocol_version=link_data.get("protocol_version", "1.0"),
        capabilities=[
            AgentCapability.SCREEN_CAPTURE,
            AgentCapability.MOUSE_CLICK,
            AgentCapability.MOUSE_MOVE,
            AgentCapability.KEYBOARD_TYPE,
            AgentCapability.SCROLL,
        ],
    )

    agent_response = await register_agent(
        person_id=current_user_id,
        registration=registration,
    )

    # Get user name for display
    # In a real app, you'd fetch this from the user profile
    user_name = "User"  # Default

    # Update link data with auth info
    link_data["linked"] = True
    link_data["agent_id"] = agent_response.agent_id
    link_data["auth_token"] = agent_response.auth_token
    link_data["person_id"] = current_user_id
    link_data["user_name"] = user_name

    LOGGER.info(
        "[agent/link] Confirmed link code %s for user %s, agent %s",
        code,
        current_user_id,
        agent_response.agent_id,
    )

    return {
        "success": True,
        "agent_id": agent_response.agent_id,
        "agent_name": link_data["agent_name"],
        "platform": link_data["platform"],
    }


# =============================================================================
# Dev-Only Registration (bypasses OAuth for local testing)
# =============================================================================

class DevRegisterRequest(BaseModel):
    """Dev-only: Register an agent without OAuth flow."""
    device_id: str = Field(..., description="Unique device identifier")
    agent_name: str = Field("Dev Agent", description="Name for this agent")
    platform: str = Field("macos", description="Platform: macos, windows, linux")


class DevRegisterResponse(BaseModel):
    """Response from dev registration."""
    agent_id: str
    auth_token: str
    person_id: str


@router.post("/dev/register", response_model=DevRegisterResponse)
async def dev_register_agent(
    request: DevRegisterRequest,
    user: str = Query(None, description="Dev user shortcut (a, b) OR full UUID"),
    person_id: str = Query(None, description="Person UUID (alternative to user param)"),
):
    """
    DEV ONLY: Register an agent without OAuth flow.

    This is for local development and testing only.
    Use: curl -X POST "http://localhost:8080/api/v1/agent/dev/register?person_id=<uuid>" \\
         -H "Content-Type: application/json" \\
         -d '{"device_id": "test-device-123", "agent_name": "My Dev Agent", "platform": "macos"}'
    """
    from sakhi.config.dev_persons import DEV_PERSONS
    import re

    UUID_PATTERN = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

    # Resolve person_id from various sources
    resolved_person_id = None

    # Priority: explicit person_id > user param as UUID > user param as shortcut > default "a"
    if person_id and UUID_PATTERN.match(person_id):
        resolved_person_id = person_id
    elif user and UUID_PATTERN.match(user):
        resolved_person_id = user
    elif user and user in DEV_PERSONS:
        resolved_person_id = DEV_PERSONS[user]["id"]
    else:
        # Default to dev person "a"
        resolved_person_id = DEV_PERSONS["a"]["id"]

    # Create registration
    registration = AgentRegistration(
        agent_name=request.agent_name,
        agent_type="desktop",
        device_id=request.device_id,
        platform=request.platform,
        agent_version="1.0.0",
        protocol_version="1.0",
        capabilities=[
            AgentCapability.SCREEN_CAPTURE,
            AgentCapability.MOUSE_CLICK,
            AgentCapability.MOUSE_MOVE,
            AgentCapability.KEYBOARD_TYPE,
            AgentCapability.SCROLL,
            AgentCapability.BROWSER_NAVIGATE,
        ],
    )

    response = await register_agent(
        person_id=resolved_person_id,
        registration=registration,
    )

    LOGGER.info(
        "[agent/dev] Registered dev agent %s for person %s",
        response.agent_id,
        resolved_person_id[:8],
    )

    return DevRegisterResponse(
        agent_id=response.agent_id,
        auth_token=response.auth_token,
        person_id=resolved_person_id,
    )


@router.get("/dev/lookup/{agent_id}")
async def dev_lookup_agent(agent_id: str):
    """DEV ONLY: Look up any agent by ID (bypasses person filter)."""
    from sakhi.apps.api.core.db import q as dbfetch

    row = await dbfetch(
        "SELECT id, person_id, agent_name, status, last_heartbeat_at FROM registered_agents WHERE id = $1",
        agent_id,
        one=True,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": str(row["id"]),
        "person_id": row["person_id"],
        "agent_name": row["agent_name"],
        "status": row["status"],
        "last_heartbeat": row["last_heartbeat_at"].isoformat() if row["last_heartbeat_at"] else None,
    }


# =============================================================================
# Task Orchestrator Endpoints
# =============================================================================
# These endpoints expose the preference-aware task orchestration system.
# This is the "planner + executor" that gives Sakhi multi-hop reasoning.

class TaskRequest(BaseModel):
    """Request to execute a preference-aware task."""
    task_description: str = Field(..., description="What you want Sakhi to do")
    agent_id: str = Field(..., description="Which agent should execute")
    starting_url: Optional[str] = Field(None, description="Optional URL to start at")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ShoppingTaskRequest(BaseModel):
    """Request for a shopping-specific task."""
    product_query: str = Field(..., description="What to search for")
    agent_id: str
    site: str = Field("amazon", description="Shopping site to use")
    max_price: Optional[float] = Field(None, description="Maximum price")


class RestaurantTaskRequest(BaseModel):
    """Request for a restaurant finding task."""
    agent_id: str
    cuisine: Optional[str] = None
    location: Optional[str] = None
    party_size: Optional[int] = None
    date: Optional[str] = None
    price_range: Optional[str] = None


class TaskPlanRequest(BaseModel):
    """Request to preview a task plan without executing."""
    task_description: str


@router.post("/task/execute")
async def execute_orchestrated_task(
    request: TaskRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Execute a preference-aware autonomous task.

    This is the main entry point for intelligent task execution.
    Sakhi will:
    1. Gather your preferences and relevant memories
    2. Plan the task with multi-step reasoning
    3. Execute via the vision loop
    4. Return results

    Example:
        POST /api/v1/agent/task/execute
        {
            "task_description": "Find me the best noise-canceling headphones under $300",
            "agent_id": "your-agent-id",
            "starting_url": "https://amazon.com"
        }
    """
    from sakhi.apps.api.services.agent.task_orchestrator import execute_task

    try:
        result = await execute_task(
            person_id=current_user_id,
            agent_id=request.agent_id,
            task_description=request.task_description,
            starting_url=request.starting_url,
        )

        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "steps_completed": result.steps_completed,
            "total_steps": len(result.plan.steps) if result.plan else 0,
            "plan_summary": result.plan.context_summary if result.plan else None,
            "constraints_applied": result.plan.constraints if result.plan else [],
            "results": result.results,
            "errors": result.errors,
            "context_used": {
                "memories_recalled": len(result.context_used.get("memories", [])),
                "has_preferences": bool(result.context_used.get("preferences")),
                "constraints": result.context_used.get("constraints", []),
            },
        }

    except Exception as e:
        LOGGER.exception("[agent/task] Task execution failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Task execution failed: {str(e)}",
        )


@router.post("/task/shopping")
async def execute_shopping_task(
    request: ShoppingTaskRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Execute a preference-aware shopping task.

    Sakhi will search the specified site for products matching
    the query, considering your preferences and past purchases.

    Example:
        POST /api/v1/agent/task/shopping
        {
            "product_query": "running shoes for marathon training",
            "agent_id": "your-agent-id",
            "site": "amazon",
            "max_price": 150.00
        }
    """
    from sakhi.apps.api.services.agent.task_orchestrator import execute_shopping_task as _execute_shopping

    try:
        result = await _execute_shopping(
            person_id=current_user_id,
            agent_id=request.agent_id,
            product_query=request.product_query,
            site=request.site,
            max_price=request.max_price,
        )

        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "product_query": request.product_query,
            "site": request.site,
            "max_price": request.max_price,
            "steps_completed": result.steps_completed,
            "results": result.results,
            "errors": result.errors,
        }

    except Exception as e:
        LOGGER.exception("[agent/task/shopping] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task/restaurant")
async def execute_restaurant_task(
    request: RestaurantTaskRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Execute a preference-aware restaurant finding task.

    Sakhi will find restaurants matching your criteria while
    considering your dining preferences, dietary restrictions,
    and past food experiences.

    Example:
        POST /api/v1/agent/task/restaurant
        {
            "agent_id": "your-agent-id",
            "cuisine": "Italian",
            "location": "San Francisco",
            "party_size": 2,
            "date": "tonight",
            "price_range": "moderate"
        }
    """
    from sakhi.apps.api.services.agent.task_orchestrator import execute_restaurant_task as _execute_restaurant

    try:
        criteria = {
            k: v for k, v in {
                "cuisine": request.cuisine,
                "location": request.location,
                "party_size": request.party_size,
                "date": request.date,
                "price_range": request.price_range,
            }.items() if v is not None
        }

        result = await _execute_restaurant(
            person_id=current_user_id,
            agent_id=request.agent_id,
            criteria=criteria,
        )

        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "search_criteria": criteria,
            "steps_completed": result.steps_completed,
            "results": result.results,
            "food_context_used": bool(result.context_used.get("food_context")),
            "errors": result.errors,
        }

    except Exception as e:
        LOGGER.exception("[agent/task/restaurant] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task/plan")
async def preview_task_plan(
    request: TaskPlanRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Preview what Sakhi would do without executing.

    Returns the task plan including:
    - Steps Sakhi would take
    - User preferences that would be considered
    - Constraints that would be applied

    Useful for previewing before committing to execution.

    Example:
        POST /api/v1/agent/task/plan
        {
            "task_description": "Order groceries for the week"
        }
    """
    from sakhi.apps.api.services.agent.task_orchestrator import get_task_plan

    try:
        plan = await get_task_plan(
            person_id=current_user_id,
            task_description=request.task_description,
        )

        return {
            "task_type": plan.task_type.value,
            "original_request": plan.original_request,
            "steps": [
                {
                    "step_number": s.step_number,
                    "action": s.action,
                    "description": s.description,
                    "success_criteria": s.success_criteria,
                    "estimated_actions": s.estimated_actions,
                }
                for s in plan.steps
            ],
            "total_estimated_actions": plan.total_estimated_actions,
            "context_summary": plan.context_summary,
            "constraints": plan.constraints,
            "success_criteria": plan.success_criteria,
        }

    except Exception as e:
        LOGGER.exception("[agent/task/plan] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Action Approval Endpoints
# =============================================================================
# These endpoints handle user approval for high-risk actions.
# Critical actions (purchase, delete, post) require explicit user confirmation.

class ApprovalDecision(BaseModel):
    """User's decision on an approval request."""
    approved: bool
    selected_option: Optional[str] = None
    comment: Optional[str] = None


@router.get("/task/approvals/pending")
async def get_pending_task_approvals(
    user: Optional[str] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get all pending approval requests and task status for the user.

    Returns actions that are waiting for user confirmation,
    along with the current task execution status if task_id is provided.

    Response:
    ```json
    {
        "pending": [...],
        "task_status": {
            "task_id": "abc123",
            "status": "running|completed|failed|waiting_approval",
            "current_step": 1,
            "total_steps": 3,
            "error": null
        }
    }
    ```
    """
    from sakhi.apps.api.services.agent.action_approval import get_pending_user_approvals
    from sakhi.apps.api.services.agent.chat_bridge import (
        get_task_execution_state,
        get_active_task_executions_for_person,
    )
    from datetime import datetime

    # Use query param 'user' if provided, otherwise use authenticated user
    effective_user_id = user or current_user_id

    try:
        pending = await get_pending_user_approvals(
            person_id=effective_user_id,
            session_id=session_id,
        )

        # Get task status if task_id is provided, or get all active tasks
        task_status = None
        active_tasks = []

        if task_id:
            state = await get_task_execution_state(task_id)
            if state:
                task_status = {
                    "task_id": state.task_id,
                    "status": state.status,
                    "current_step": state.current_step,
                    "total_steps": state.total_steps,
                    "error": state.error,
                    "result": state.result,
                }
        else:
            # Return all active tasks for this user
            states = await get_active_task_executions_for_person(effective_user_id)
            LOGGER.info(
                "[agent/approvals] Getting active tasks for user %s, found %d tasks",
                effective_user_id,
                len(states),
            )
            active_tasks = [
                {
                    "task_id": state.task_id,
                    "status": state.status,
                    "current_step": state.current_step,
                    "total_steps": state.total_steps,
                    "error": state.error,
                    "result": state.result,
                }
                for state in states
            ]
            if active_tasks:
                LOGGER.info("[agent/approvals] Active tasks: %s", active_tasks)

        return {
            "pending": [
                {
                    "request_id": req.request_id,
                    "session_id": req.session_id,
                    "task_id": req.task_id,
                    "action_type": req.action_type,
                    "action_description": req.action_description,
                    "risk_level": req.risk_level.value,
                    "context_summary": req.context_summary,
                    "why_approval_needed": req.why_approval_needed,
                    "if_approved": req.if_approved,
                    "if_rejected": req.if_rejected,
                    "options": req.options,
                    "screenshot_id": req.screenshot_id,
                    "created_at": req.created_at.isoformat(),
                    "expires_in_seconds": (
                        int((req.expires_at - datetime.utcnow()).total_seconds())
                        if req.expires_at else None
                    ),
                }
                for req in pending
            ],
            "count": len(pending),
            "task_status": task_status,
            "active_tasks": active_tasks,
        }

    except Exception as e:
        LOGGER.exception("[agent/approvals] Failed to get pending: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task/approvals/{request_id}/respond")
async def respond_to_approval(
    request_id: str,
    decision: ApprovalDecision,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Respond to an approval request.

    Called when user clicks "Yes, proceed" or "No, cancel" in the chat.
    This resumes the paused vision loop with the user's decision.

    Request:
    ```json
    {
        "approved": true,
        "selected_option": "approve",
        "comment": "Looks good!"
    }
    ```

    Response:
    ```json
    {
        "success": true,
        "request_id": "abc123",
        "status": "approved",
        "message": "Action will proceed"
    }
    ```
    """
    from sakhi.apps.api.services.agent.action_approval import submit_approval_response

    try:
        request = await submit_approval_response(
            request_id=request_id,
            approved=decision.approved,
            selected_option=decision.selected_option,
        )

        return {
            "success": True,
            "request_id": request_id,
            "status": request.status.value,
            "message": (
                "Action will proceed" if decision.approved
                else "Action cancelled"
            ),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        LOGGER.exception("[agent/approvals] Failed to respond: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/approvals/{request_id}")
async def get_approval_details(
    request_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get details of a specific approval request.

    Useful for showing approval context in the chat interface.
    """
    from sakhi.apps.api.services.agent.action_approval import get_approval_manager

    try:
        manager = get_approval_manager()
        request = manager._pending.get(request_id)

        if not request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if request.person_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        return {
            "request_id": request.request_id,
            "session_id": request.session_id,
            "task_id": request.task_id,
            "action_type": request.action_type,
            "action_description": request.action_description,
            "action_parameters": request.action_parameters,
            "risk_level": request.risk_level.value,
            "context_summary": request.context_summary,
            "why_approval_needed": request.why_approval_needed,
            "if_approved": request.if_approved,
            "if_rejected": request.if_rejected,
            "options": request.options,
            "status": request.status.value,
            "screenshot_id": request.screenshot_id,
            "created_at": request.created_at.isoformat(),
            "expires_at": request.expires_at.isoformat() if request.expires_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        LOGGER.exception("[agent/approvals] Failed to get details: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Browser Automation Endpoints
# =============================================================================
# Server-side browser automation using Playwright.
# DOM-first strategy with vision fallback for cost efficiency.

class BrowserTaskRequest(BaseModel):
    """Request to execute a browser automation task."""
    task_description: str = Field(..., description="What to accomplish")
    starting_url: str = Field(..., description="URL to start at")
    headless: bool = Field(True, description="Run browser in headless mode")
    max_steps: int = Field(20, description="Maximum automation steps")
    strategy: str = Field("dom_first", description="dom_first|vision_only|dom_only")


class BrowserSessionRequest(BaseModel):
    """Request to create a browser session."""
    task_description: Optional[str] = None
    headless: bool = True


class BrowserActionRequest(BaseModel):
    """Request to execute a single browser action."""
    session_id: str
    action_type: str = Field(..., description="click|type|navigate|scroll|wait")
    target: Optional[str] = Field(None, description="Selector, text, or URL")
    text: Optional[str] = Field(None, description="Text to type (for type action)")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options")


class CredentialRequest(BaseModel):
    """Request to store a credential."""
    site_pattern: str = Field(..., description="Regex pattern for URL matching")
    username: str
    password: str
    extra_fields: Optional[Dict[str, str]] = None


@router.post("/browser/task")
async def execute_browser_task(
    request: BrowserTaskRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Execute an automated browser task.

    Uses DOM-first strategy (free) with vision fallback (paid) for reliability.
    This runs server-side, no desktop agent needed.

    Example:
        POST /api/v1/agent/browser/task
        {
            "task_description": "Search for Italian restaurants in SF",
            "starting_url": "https://google.com",
            "max_steps": 15
        }

    Returns:
        Task result with success status, steps taken, and extracted data.
    """
    from sakhi.apps.api.services.agent.browser_session import run_browser_task_with_session
    from sakhi.apps.api.services.agent.browser_automation import ActionStrategy

    try:
        # Map strategy string to enum
        strategy_map = {
            "dom_first": ActionStrategy.DOM_FIRST,
            "vision_only": ActionStrategy.VISION_ONLY,
            "dom_only": ActionStrategy.DOM_ONLY,
        }
        strategy = strategy_map.get(request.strategy, ActionStrategy.DOM_FIRST)

        result = await run_browser_task_with_session(
            person_id=current_user_id,
            task=request.task_description,
            starting_url=request.starting_url,
            headless=request.headless,
            max_steps=request.max_steps,
        )

        return {
            "success": result.get("success", False),
            "completed": result.get("completed", False),
            "steps_taken": result.get("steps", 0),
            "session_id": result.get("session_id"),
            "result": result.get("result"),
            "stats": result.get("stats", {}),
            "errors": result.get("errors", []),
        }

    except Exception as e:
        LOGGER.exception("[browser/task] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/browser/session")
async def create_browser_session(
    request: BrowserSessionRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Create a new browser session for manual control.

    Returns a session ID that can be used with /browser/action endpoint.
    Sessions expire after 30 minutes of inactivity.

    Example:
        POST /api/v1/agent/browser/session
        {"task_description": "Shopping session", "headless": false}
    """
    from sakhi.apps.api.services.agent.browser_session import create_browser_session as _create_session

    try:
        session = await _create_session(
            person_id=current_user_id,
            task=request.task_description,
            headless=request.headless,
        )

        # Start the browser
        await session.browser.start()

        return {
            "session_id": session.id,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "expires_in_minutes": 30,
        }

    except Exception as e:
        LOGGER.exception("[browser/session] Failed to create: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/browser/action")
async def execute_browser_action(
    request: BrowserActionRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Execute a single browser action in an existing session.

    Action types:
    - click: Click element by selector or text
    - type: Type text into input field
    - navigate: Go to URL
    - scroll: Scroll page (up/down)
    - wait: Wait for element or time

    Example:
        POST /api/v1/agent/browser/action
        {
            "session_id": "abc123",
            "action_type": "click",
            "target": "button.submit"
        }
    """
    from sakhi.apps.api.services.agent.browser_session import get_session_manager

    try:
        manager = get_session_manager()
        session = await manager.get_session(request.session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")

        if session.person_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        browser = session.browser
        options = request.options or {}

        # Execute action
        if request.action_type == "click":
            result = await browser.click(request.target or "")
        elif request.action_type == "type":
            result = await browser.type_text(
                request.target or "",
                request.text or "",
                press_enter=options.get("press_enter", False),
            )
        elif request.action_type == "navigate":
            result = await browser.navigate(request.target or "")
        elif request.action_type == "scroll":
            result = await browser.scroll(
                options.get("direction", "down"),
                options.get("amount", 300),
            )
        elif request.action_type == "wait":
            if request.target:
                result = await browser.wait_for_selector(request.target)
            else:
                result = await browser.wait(options.get("ms", 1000))
        elif request.action_type == "screenshot":
            path = await browser.screenshot(save=True)
            result = {"success": bool(path), "path": path}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action_type}")

        session.touch()
        session.actions_executed += 1

        return {
            "success": result.get("success", False),
            "action": request.action_type,
            "method": result.get("method"),
            "details": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        LOGGER.exception("[browser/action] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/browser/session/{session_id}")
async def close_browser_session(
    session_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """Close a browser session."""
    from sakhi.apps.api.services.agent.browser_session import get_session_manager

    try:
        manager = get_session_manager()
        session = await manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.person_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        await manager.close_session(session_id)

        return {"success": True, "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        LOGGER.exception("[browser/session] Failed to close: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browser/sessions")
async def list_browser_sessions(
    current_user_id: str = Depends(get_current_user_id),
):
    """List all active browser sessions for the user."""
    from sakhi.apps.api.services.agent.browser_session import get_session_manager

    try:
        manager = get_session_manager()
        sessions = await manager.get_user_sessions(current_user_id)

        return {
            "sessions": [s.to_dict() for s in sessions],
            "count": len(sessions),
        }

    except Exception as e:
        LOGGER.exception("[browser/sessions] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# Credential management endpoints
@router.post("/browser/credentials")
async def store_browser_credential(
    request: CredentialRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Store a credential for automated login.

    Credentials are stored per-user and matched to sites via regex pattern.

    Example:
        POST /api/v1/agent/browser/credentials
        {
            "site_pattern": ".*amazon\\.com.*",
            "username": "user@example.com",
            "password": "secret"
        }
    """
    from sakhi.apps.api.services.agent.browser_session import get_session_manager

    try:
        manager = get_session_manager()
        manager.store_credential(
            person_id=current_user_id,
            site_pattern=request.site_pattern,
            username=request.username,
            password=request.password,
            extra_fields=request.extra_fields,
        )

        return {"success": True, "site_pattern": request.site_pattern}

    except Exception as e:
        LOGGER.exception("[browser/credentials] Failed to store: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browser/credentials")
async def list_browser_credentials(
    current_user_id: str = Depends(get_current_user_id),
):
    """List stored credentials (without passwords)."""
    from sakhi.apps.api.services.agent.browser_session import get_session_manager

    try:
        manager = get_session_manager()
        creds = manager.list_credentials(current_user_id)

        return {"credentials": creds, "count": len(creds)}

    except Exception as e:
        LOGGER.exception("[browser/credentials] Failed to list: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/browser/credentials/{site_pattern}")
async def delete_browser_credential(
    site_pattern: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """Delete a stored credential."""
    from sakhi.apps.api.services.agent.browser_session import get_session_manager

    try:
        manager = get_session_manager()
        deleted = manager.delete_credential(current_user_id, site_pattern)

        if not deleted:
            raise HTTPException(status_code=404, detail="Credential not found")

        return {"success": True, "site_pattern": site_pattern}

    except HTTPException:
        raise
    except Exception as e:
        LOGGER.exception("[browser/credentials] Failed to delete: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Personalized Search Endpoints
# =============================================================================
# Browser automation + preference engine integration.
# Products are searched and ranked by user's stored preferences.

class PersonalizedSearchRequest(BaseModel):
    """Request for a personalized product search."""
    query: str = Field(..., description="What to search for (e.g., 'car air freshener')")
    budget: Optional[float] = Field(None, description="Maximum price in USD")
    premium_max: Optional[float] = Field(None, description="Max price for premium suggestions")
    site: str = Field("amazon", description="Shopping site to search")
    explain_preferences: bool = Field(True, description="Include preference explanations")


@router.post("/browser/search/personalized")
async def personalized_product_search(
    request: PersonalizedSearchRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Search for products ranked by user's stored preferences.

    This integrates browser automation with the preference engine:
    1. Searches the website for products matching the query
    2. Extracts product information (title, price, rating, reviews)
    3. Scores each product against user's stored preferences
    4. Returns results sorted by combined score (preference match + review quality)

    Example:
        POST /api/v1/agent/browser/search/personalized
        {
            "query": "car air freshener",
            "budget": 20.0,
            "site": "amazon"
        }

    Response:
        {
            "query": "car air freshener",
            "budget": 20.0,
            "your_preferences": {
                "domain": "fragrance",
                "preferences": ["woodiness (strong)", "citrus (like)"],
                "avoids": ["florals (dislike)"]
            },
            "budget_results": [
                {
                    "title": "Woody Cedar Car Freshener...",
                    "price_usd": 15.99,
                    "rating": 4.5,
                    "reviews": 1234,
                    "combined_score": 0.85,
                    "match": {
                        "score": 0.92,
                        "level": "perfect",
                        "reasons": ["Matches your preference for woodiness"]
                    }
                }
            ],
            "premium_suggestions": [...]
        }
    """
    from sakhi.apps.api.services.agent.personalized_search import search_with_preferences

    try:
        result = await search_with_preferences(
            person_id=current_user_id,
            query=request.query,
            budget=request.budget,
            explain_preferences=request.explain_preferences,
        )

        return result

    except Exception as e:
        LOGGER.exception("[browser/search/personalized] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browser/search/preferences/{domain}")
async def get_search_preferences(
    domain: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get user's stored preferences for a domain.

    Useful for showing users what Sakhi knows about their preferences
    before running a personalized search.

    Domains: food, fragrance, travel, fashion, wellness, environment, media

    Example:
        GET /api/v1/agent/browser/search/preferences/fragrance

    Response:
        {
            "domain": "fragrance",
            "has_preferences": true,
            "preferences": ["woodiness (strong)", "citrus (like)"],
            "avoids": ["florals (dislike)", "musk (avoid)"],
            "dimension_count": 5
        }
    """
    from sakhi.apps.api.services.memory.product_matching import get_preference_summary_for_domain

    try:
        summary = await get_preference_summary_for_domain(current_user_id, domain)
        return summary

    except Exception as e:
        LOGGER.exception("[browser/search/preferences] Failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
