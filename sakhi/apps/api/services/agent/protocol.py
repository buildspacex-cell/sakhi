"""
Agent Protocol
--------------
Message types and models for agent-API communication.

Protocol Design Principles:
1. Versioned - Agent sends protocol_version, API responds accordingly
2. Capability-based - Agent declares what it can do, API only sends compatible commands
3. Backward-compatible - New API works with old agents (graceful degradation)
4. Auto-update - API can signal when agent should update
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class AgentCapability(str, Enum):
    """Capabilities an agent can declare."""
    SCREEN_CAPTURE = "screen_capture"
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    KEYBOARD_TYPE = "keyboard_type"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    SCROLL = "scroll"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    APP_LAUNCH = "app_launch"
    BROWSER_NAVIGATE = "browser_navigate"
    CLIPBOARD_READ = "clipboard_read"
    CLIPBOARD_WRITE = "clipboard_write"


class ActionType(str, Enum):
    """Types of actions an agent can execute."""
    # Screen
    SCREENSHOT = "screenshot"

    # Mouse
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    MOVE_MOUSE = "move_mouse"
    DRAG = "drag"

    # Keyboard
    TYPE = "type"
    KEY = "key"
    SHORTCUT = "shortcut"

    # Scroll
    SCROLL = "scroll"

    # System
    LAUNCH_APP = "launch_app"
    NAVIGATE = "navigate"

    # Clipboard
    COPY = "copy"
    PASTE = "paste"

    # Flow control
    WAIT = "wait"


class ActionStatus(str, Enum):
    """Status of an action."""
    PENDING = "pending"
    SENT = "sent"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionStatus(str, Enum):
    """Status of an agent session."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Status of a registered agent."""
    REGISTERED = "registered"
    ONLINE = "online"
    OFFLINE = "offline"
    SUSPENDED = "suspended"


# =============================================================================
# Agent Registration
# =============================================================================

class AgentRegistration(BaseModel):
    """Registration request from a new agent."""
    agent_name: str = Field(..., description="User-friendly name like 'My MacBook'")
    agent_type: str = Field(..., description="desktop, mobile, or browser_extension")
    device_id: str = Field(..., description="Unique device identifier (hashed)")

    # Version info
    agent_version: str = Field(..., description="Agent software version")
    protocol_version: str = Field(default="1.0", description="Protocol version")

    # Capabilities
    capabilities: List[AgentCapability] = Field(default_factory=list)

    # Platform info
    platform: str = Field(..., description="macos, windows, linux, ios, android")
    platform_version: Optional[str] = None
    architecture: Optional[str] = None  # arm64, x86_64


class AgentRegistrationResponse(BaseModel):
    """Response to agent registration."""
    agent_id: str
    auth_token: str  # Token for future requests
    status: str = "registered"

    # Capability approval
    approved_capabilities: List[str] = Field(default_factory=list)
    pending_approval: List[str] = Field(default_factory=list)

    # Update info
    update_available: bool = False
    latest_version: Optional[str] = None


# =============================================================================
# Agent Heartbeat
# =============================================================================

class AgentHeartbeat(BaseModel):
    """Periodic heartbeat from agent to API."""
    agent_id: str
    status: str = "online"

    # Current state
    active_session_id: Optional[str] = None
    current_app: Optional[str] = None
    screen_resolution: Optional[str] = None  # "1920x1080"

    # Metrics
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None


class HeartbeatResponse(BaseModel):
    """Response to agent heartbeat."""
    acknowledged: bool = True

    # Pending work
    has_pending_actions: bool = False
    pending_action_count: int = 0

    # Update notification
    update_available: bool = False
    update_mandatory: bool = False
    latest_version: Optional[str] = None

    # Commands from API
    commands: List[Dict[str, Any]] = Field(default_factory=list)
    # e.g., [{"command": "start_session", "session_id": "..."}]


# =============================================================================
# Actions
# =============================================================================

class AgentAction(BaseModel):
    """An action for the agent to execute."""
    action_id: str
    action_type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    """
    Parameters by action type:

    click: {"x": 150, "y": 200, "button": "left"}
    double_click: {"x": 150, "y": 200}
    right_click: {"x": 150, "y": 200}
    move_mouse: {"x": 150, "y": 200}
    drag: {"from_x": 100, "from_y": 100, "to_x": 200, "to_y": 200}

    type: {"text": "Hello world", "delay_ms": 50}
    key: {"key": "enter"}  # enter, tab, escape, backspace, etc.
    shortcut: {"keys": ["cmd", "c"]}  # or ["ctrl", "shift", "s"]

    scroll: {"direction": "down", "amount": 300}  # or "up"

    launch_app: {"app_name": "Chrome"}
    navigate: {"url": "https://example.com"}

    copy: {}  # Triggers Cmd+C
    paste: {}  # Triggers Cmd+V

    screenshot: {"region": null}  # null = full screen, or {"x", "y", "w", "h"}

    wait: {"ms": 1000}
    """

    # Execution hints
    sequence: int = 0
    timeout_ms: int = 30000
    retry_on_fail: bool = False
    max_retries: int = 1

    # Description for user
    description: Optional[str] = None  # "Clicking the Search button"


class ActionResult(BaseModel):
    """Result of action execution from agent."""
    action_id: str
    success: bool
    error: Optional[str] = None

    # Timing
    started_at: datetime
    completed_at: datetime
    duration_ms: int

    # Screenshot after action (if applicable)
    screenshot_id: Optional[str] = None

    # Additional result data
    data: Dict[str, Any] = Field(default_factory=dict)
    # e.g., for clipboard_read: {"content": "copied text"}


# =============================================================================
# Screen Capture
# =============================================================================

class ScreenCapture(BaseModel):
    """Screenshot sent from agent to API."""
    agent_id: str
    session_id: Optional[str] = None

    # Image data
    image_base64: str
    format: str = "png"  # png or jpeg
    width: int
    height: int

    # Context
    trigger: str = "user_request"  # action_result, periodic, user_request, error
    preceding_action_id: Optional[str] = None

    # Metadata
    captured_at: datetime
    current_app: Optional[str] = None
    current_window_title: Optional[str] = None


class ScreenUnderstanding(BaseModel):
    """Vision analysis of a screenshot."""
    screenshot_id: str
    description: str

    # Detected UI elements
    detected_elements: List[Dict[str, Any]] = Field(default_factory=list)
    """
    [
        {
            "type": "button",
            "text": "Search",
            "bounds": {"x": 100, "y": 200, "width": 80, "height": 40},
            "clickable": true
        },
        {
            "type": "input",
            "label": "Email",
            "bounds": {...},
            "value": "user@example.com"
        }
    ]
    """

    # Detected text (OCR)
    ocr_text: Optional[str] = None

    # Context
    current_app: Optional[str] = None
    current_url: Optional[str] = None  # If browser

    # Confidence
    confidence: float = 0.0


# =============================================================================
# Commands (API → Agent)
# =============================================================================

class AgentCommand(BaseModel):
    """Command from API to agent."""
    command: str
    """
    Commands:
    - start_session: Begin a new task session
    - end_session: End current session
    - pause_session: Pause execution
    - resume_session: Resume execution
    - take_screenshot: Capture screen now
    - execute_action: Execute a specific action
    - check_update: Check for agent updates
    """
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"  # low, normal, high, urgent


class AgentResponse(BaseModel):
    """Response from agent to a command."""
    command: str
    success: bool
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Updates
# =============================================================================

class UpdateCheck(BaseModel):
    """Request to check for agent updates."""
    agent_type: str
    platform: str
    current_version: str
    architecture: Optional[str] = None
    protocol_version: str = "1.0"


class UpdateInfo(BaseModel):
    """Information about available update."""
    has_update: bool
    latest_version: Optional[str] = None
    download_url: Optional[str] = None
    checksum: Optional[str] = None
    file_size_bytes: Optional[int] = None
    is_mandatory: bool = False
    release_notes: Optional[str] = None
    min_required_version: Optional[str] = None


# =============================================================================
# Session Messages
# =============================================================================

class SessionRequest(BaseModel):
    """Request to start a new agent session."""
    agent_id: str
    task_description: str
    """
    What the user wants to do:
    - "Book a flight to NYC for next Friday"
    - "Search for the best coffee shops nearby"
    - "Fill out this form with my info"
    """

    # Optional hints
    target_app: Optional[str] = None  # "Chrome", "Safari"
    target_url: Optional[str] = None


class SessionResponse(BaseModel):
    """Response with session details."""
    session_id: str
    status: SessionStatus

    # Initial plan (if available)
    plan_summary: Optional[str] = None
    estimated_steps: Optional[int] = None

    # First actions to execute
    initial_actions: List[AgentAction] = Field(default_factory=list)

    # User confirmation needed?
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


# =============================================================================
# Batch Messages (for efficiency)
# =============================================================================

class ActionBatch(BaseModel):
    """Batch of actions for efficient execution."""
    session_id: str
    actions: List[AgentAction]
    execute_sequentially: bool = True


class ResultBatch(BaseModel):
    """Batch of action results."""
    session_id: str
    results: List[ActionResult]
    screenshot: Optional[ScreenCapture] = None  # Final screenshot


__all__ = [
    # Enums
    "AgentCapability",
    "ActionType",
    "ActionStatus",
    "SessionStatus",
    "AgentStatus",
    # Registration
    "AgentRegistration",
    "AgentRegistrationResponse",
    # Heartbeat
    "AgentHeartbeat",
    "HeartbeatResponse",
    # Actions
    "AgentAction",
    "ActionResult",
    # Screen
    "ScreenCapture",
    "ScreenUnderstanding",
    # Commands
    "AgentCommand",
    "AgentResponse",
    # Updates
    "UpdateCheck",
    "UpdateInfo",
    # Session
    "SessionRequest",
    "SessionResponse",
    # Batch
    "ActionBatch",
    "ResultBatch",
]
