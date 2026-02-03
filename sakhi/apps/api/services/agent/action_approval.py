"""
Action Approval System
----------------------
Classifies actions by risk level and manages user approval flow.

Critical actions (purchase, post, delete) require explicit user confirmation.
This ensures Sakhi never takes irreversible actions without consent.

The approval flow integrates with the chat interface:
1. Vision loop detects high-risk action coming
2. Loop PAUSES, emits approval request
3. Chat shows: "Should I add this to your cart?"
4. User approves/rejects via chat
5. Loop resumes or cancels

This is what makes Sakhi trustworthy - it asks before acting on your behalf.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Risk Classification
# =============================================================================

class ActionRisk(str, Enum):
    """Risk level of an action."""
    LOW = "low"          # Navigate, scroll, view - no approval needed
    MEDIUM = "medium"    # Search, filter, add to wishlist - optional approval
    HIGH = "high"        # Add to cart, book, subscribe - approval required
    CRITICAL = "critical"  # Purchase, delete, post publicly - always confirm


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"  # User has pre-approved this action type


# Actions that require approval by risk level
ACTION_RISK_MAP: Dict[str, ActionRisk] = {
    # LOW - Safe browsing actions
    "navigate": ActionRisk.LOW,
    "scroll": ActionRisk.LOW,
    "wait": ActionRisk.LOW,
    "back": ActionRisk.LOW,
    "forward": ActionRisk.LOW,
    "refresh": ActionRisk.LOW,

    # MEDIUM - Data gathering, reversible
    "search": ActionRisk.LOW,  # Searching is safe
    "filter": ActionRisk.LOW,
    "sort": ActionRisk.LOW,
    "click_view": ActionRisk.LOW,  # Click to view details
    "type_search": ActionRisk.LOW,  # Typing in search box
    "add_wishlist": ActionRisk.MEDIUM,
    "save_for_later": ActionRisk.MEDIUM,

    # HIGH - Commits user to something
    "add_to_cart": ActionRisk.HIGH,
    "book": ActionRisk.HIGH,
    "reserve": ActionRisk.HIGH,
    "subscribe": ActionRisk.HIGH,
    "sign_up": ActionRisk.HIGH,
    "apply": ActionRisk.HIGH,
    "submit_form": ActionRisk.HIGH,

    # CRITICAL - Irreversible or financial
    "purchase": ActionRisk.CRITICAL,
    "checkout": ActionRisk.CRITICAL,
    "buy_now": ActionRisk.CRITICAL,
    "place_order": ActionRisk.CRITICAL,
    "confirm_payment": ActionRisk.CRITICAL,
    "delete": ActionRisk.CRITICAL,
    "remove": ActionRisk.CRITICAL,
    "post": ActionRisk.CRITICAL,
    "publish": ActionRisk.CRITICAL,
    "send": ActionRisk.CRITICAL,
    "share": ActionRisk.CRITICAL,
    "cancel_subscription": ActionRisk.CRITICAL,
}

# Keywords that indicate risk level (for dynamic classification)
HIGH_RISK_KEYWORDS = [
    "add to cart", "add to bag", "book now", "reserve", "subscribe",
    "sign up", "register", "apply", "submit", "confirm",
]

CRITICAL_RISK_KEYWORDS = [
    "buy", "purchase", "checkout", "place order", "pay", "payment",
    "delete", "remove permanently", "post", "publish", "send message",
    "share publicly", "cancel", "unsubscribe",
]


# =============================================================================
# Approval Request Model
# =============================================================================

class ApprovalRequest(BaseModel):
    """A request for user approval of an action."""
    request_id: str
    session_id: str
    task_id: str
    person_id: str

    # Action details
    action_type: str
    action_parameters: Dict[str, Any]
    action_description: str

    # Context
    risk_level: ActionRisk
    context_summary: str  # What Sakhi found/decided
    why_approval_needed: str

    # What happens next
    if_approved: str  # "Will add Nike Air Zoom to cart"
    if_rejected: str  # "Will continue searching for alternatives"

    # Options for user
    options: List[Dict[str, str]]  # [{label: "Add to cart", value: "approve"}, ...]

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = datetime.utcnow()
    expires_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # "user" or "timeout" or "auto"

    # Screenshot context
    screenshot_id: Optional[str] = None
    screenshot_url: Optional[str] = None


class ApprovalResponse(BaseModel):
    """User's response to an approval request."""
    request_id: str
    approved: bool
    selected_option: Optional[str] = None  # Which option user chose
    user_comment: Optional[str] = None  # Optional feedback


# =============================================================================
# Action Classifier
# =============================================================================

def classify_action_risk(
    action_type: str,
    action_parameters: Dict[str, Any],
    button_text: Optional[str] = None,
    context: Optional[str] = None,
) -> ActionRisk:
    """
    Classify the risk level of an action.

    Args:
        action_type: Type of action (click, type, etc.)
        action_parameters: Action parameters
        button_text: Text of button being clicked (if applicable)
        context: Additional context about the action

    Returns:
        Risk level of the action
    """
    # Check explicit action type mapping
    if action_type in ACTION_RISK_MAP:
        return ACTION_RISK_MAP[action_type]

    # For click actions, analyze what's being clicked
    if action_type == "click":
        target_text = (
            button_text or
            action_parameters.get("text", "") or
            action_parameters.get("description", "")
        ).lower()

        # Check for critical keywords
        for keyword in CRITICAL_RISK_KEYWORDS:
            if keyword in target_text:
                return ActionRisk.CRITICAL

        # Check for high-risk keywords
        for keyword in HIGH_RISK_KEYWORDS:
            if keyword in target_text:
                return ActionRisk.HIGH

    # For type actions, check what's being typed where
    if action_type == "type":
        # Typing in search is safe
        if action_parameters.get("field_type") == "search":
            return ActionRisk.LOW
        # Typing in payment fields is critical
        if action_parameters.get("field_type") in ["credit_card", "cvv", "payment"]:
            return ActionRisk.CRITICAL

    # Default to low risk for unknown actions
    return ActionRisk.LOW


def requires_approval(
    action_type: str,
    action_parameters: Dict[str, Any],
    button_text: Optional[str] = None,
    user_settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Check if an action requires user approval.

    Args:
        action_type: Type of action
        action_parameters: Action parameters
        button_text: Text of button being clicked
        user_settings: User's approval preferences

    Returns:
        True if approval is required
    """
    risk = classify_action_risk(action_type, action_parameters, button_text)

    # Critical actions always require approval
    if risk == ActionRisk.CRITICAL:
        return True

    # High-risk actions require approval by default
    if risk == ActionRisk.HIGH:
        # Check if user has pre-approved this action type
        if user_settings:
            auto_approve = user_settings.get("auto_approve_actions", [])
            if action_type in auto_approve:
                return False
        return True

    # Medium risk - check user preference
    if risk == ActionRisk.MEDIUM:
        if user_settings and user_settings.get("approve_medium_risk", False):
            return True
        return False

    # Low risk - no approval needed
    return False


# =============================================================================
# Approval Manager
# =============================================================================

class ApprovalManager:
    """
    Manages the approval flow for actions.

    Integrates with:
    - Vision loop (pauses when approval needed)
    - Chat interface (shows approval prompts)
    - Database (persists approval history)
    """

    def __init__(
        self,
        on_approval_requested: Optional[Callable[[ApprovalRequest], None]] = None,
        approval_timeout_seconds: int = 300,  # 5 minutes
    ):
        self.on_approval_requested = on_approval_requested
        self.approval_timeout = timedelta(seconds=approval_timeout_seconds)

        # In-memory pending approvals (for quick lookup)
        # In production, this should be Redis-backed
        self._pending: Dict[str, ApprovalRequest] = {}
        self._waiting: Dict[str, asyncio.Event] = {}

    async def request_approval(
        self,
        session_id: str,
        task_id: str,
        person_id: str,
        action_type: str,
        action_parameters: Dict[str, Any],
        action_description: str,
        context_summary: str,
        screenshot_id: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Create an approval request and wait for response.

        This is called by the vision loop when it detects a high-risk action.
        The loop will pause until the user responds.
        """
        request_id = str(uuid.uuid4())[:12]

        risk = classify_action_risk(action_type, action_parameters)

        # Build approval request
        request = ApprovalRequest(
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            person_id=person_id,
            action_type=action_type,
            action_parameters=action_parameters,
            action_description=action_description,
            risk_level=risk,
            context_summary=context_summary,
            why_approval_needed=self._get_approval_reason(action_type, risk),
            if_approved=f"Will {action_description.lower()}",
            if_rejected="Will continue with alternatives or stop",
            options=self._get_approval_options(action_type, risk),
            expires_at=datetime.utcnow() + self.approval_timeout,
            screenshot_id=screenshot_id,
        )

        # Store pending request
        self._pending[request_id] = request
        self._waiting[request_id] = asyncio.Event()

        # Persist to database
        await self._store_approval_request(request)

        # Notify listeners (chat interface, etc.)
        if self.on_approval_requested:
            self.on_approval_requested(request)

        LOGGER.info(
            "[approval] Created request %s for %s action (risk: %s)",
            request_id,
            action_type,
            risk.value,
        )

        return request

    async def wait_for_approval(
        self,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> ApprovalRequest:
        """
        Wait for user to respond to approval request.

        Returns the updated request with status.
        """
        if request_id not in self._waiting:
            raise ValueError(f"Unknown approval request: {request_id}")

        event = self._waiting[request_id]

        try:
            # Wait for approval or timeout
            wait_time = timeout or self.approval_timeout.total_seconds()
            await asyncio.wait_for(event.wait(), timeout=wait_time)
        except asyncio.TimeoutError:
            # Mark as expired
            request = self._pending.get(request_id)
            if request:
                request.status = ApprovalStatus.EXPIRED
                request.resolved_at = datetime.utcnow()
                request.resolved_by = "timeout"
                await self._update_approval_status(request)

        return self._pending.get(request_id)

    async def submit_approval(
        self,
        request_id: str,
        approved: bool,
        selected_option: Optional[str] = None,
        user_comment: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Submit user's approval decision.

        Called by the chat interface when user responds.
        """
        if request_id not in self._pending:
            raise ValueError(f"Unknown or expired approval request: {request_id}")

        request = self._pending[request_id]

        # Update status
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.resolved_at = datetime.utcnow()
        request.resolved_by = "user"

        # Persist
        await self._update_approval_status(request)

        # Signal waiting coroutine
        if request_id in self._waiting:
            self._waiting[request_id].set()

        LOGGER.info(
            "[approval] Request %s %s by user",
            request_id,
            "approved" if approved else "rejected",
        )

        return request

    async def get_pending_approvals(
        self,
        person_id: str,
        session_id: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """Get all pending approval requests for a user."""
        pending = []
        for request in self._pending.values():
            if request.person_id != person_id:
                continue
            if session_id and request.session_id != session_id:
                continue
            if request.status == ApprovalStatus.PENDING:
                # Check if expired
                if request.expires_at and datetime.utcnow() > request.expires_at:
                    request.status = ApprovalStatus.EXPIRED
                else:
                    pending.append(request)
        return pending

    def _get_approval_reason(self, action_type: str, risk: ActionRisk) -> str:
        """Get human-readable reason for needing approval."""
        reasons = {
            "add_to_cart": "This will add an item to your shopping cart",
            "purchase": "This will complete a purchase using your payment method",
            "checkout": "This will proceed to checkout",
            "book": "This will make a booking/reservation",
            "subscribe": "This will start a subscription",
            "delete": "This will permanently delete something",
            "post": "This will post content publicly",
            "send": "This will send a message",
        }

        if action_type in reasons:
            return reasons[action_type]

        if risk == ActionRisk.CRITICAL:
            return "This action cannot be easily undone"
        if risk == ActionRisk.HIGH:
            return "This action commits you to something"

        return "This action may have consequences"

    def _get_approval_options(
        self,
        action_type: str,
        risk: ActionRisk,
    ) -> List[Dict[str, str]]:
        """Get approval options for the user."""
        # Default options
        options = [
            {"label": "Yes, proceed", "value": "approve"},
            {"label": "No, don't do this", "value": "reject"},
        ]

        # Add context-specific options
        if action_type in ["add_to_cart", "purchase"]:
            options.insert(1, {"label": "Show me other options", "value": "alternatives"})

        if action_type in ["book", "reserve"]:
            options.insert(1, {"label": "Check other times", "value": "other_times"})

        return options

    async def _store_approval_request(self, request: ApprovalRequest) -> None:
        """Store approval request in database."""
        try:
            await dbfetch(
                """
                INSERT INTO agent_approval_requests (
                    request_id, session_id, task_id, person_id,
                    action_type, action_parameters, action_description,
                    risk_level, status, context_summary,
                    created_at, expires_at, screenshot_id
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                )
                """,
                request.request_id,
                request.session_id,
                request.task_id,
                request.person_id,
                request.action_type,
                request.action_parameters,
                request.action_description,
                request.risk_level.value,
                request.status.value,
                request.context_summary,
                request.created_at,
                request.expires_at,
                request.screenshot_id,
            )
        except Exception as e:
            # Table might not exist yet - log and continue
            LOGGER.warning("[approval] Failed to store request: %s", e)

    async def _update_approval_status(self, request: ApprovalRequest) -> None:
        """Update approval status in database."""
        try:
            await dbfetch(
                """
                UPDATE agent_approval_requests
                SET status = $2, resolved_at = $3, resolved_by = $4
                WHERE request_id = $1
                """,
                request.request_id,
                request.status.value,
                request.resolved_at,
                request.resolved_by,
            )
        except Exception as e:
            LOGGER.warning("[approval] Failed to update status: %s", e)


# =============================================================================
# Convenience Functions
# =============================================================================

# Global approval manager instance
_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get the global approval manager instance."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


async def request_action_approval(
    session_id: str,
    task_id: str,
    person_id: str,
    action_type: str,
    action_parameters: Dict[str, Any],
    action_description: str,
    context_summary: str,
    screenshot_id: Optional[str] = None,
) -> ApprovalRequest:
    """Request approval for an action."""
    manager = get_approval_manager()
    return await manager.request_approval(
        session_id=session_id,
        task_id=task_id,
        person_id=person_id,
        action_type=action_type,
        action_parameters=action_parameters,
        action_description=action_description,
        context_summary=context_summary,
        screenshot_id=screenshot_id,
    )


async def submit_approval_response(
    request_id: str,
    approved: bool,
    selected_option: Optional[str] = None,
) -> ApprovalRequest:
    """Submit a response to an approval request."""
    manager = get_approval_manager()
    return await manager.submit_approval(
        request_id=request_id,
        approved=approved,
        selected_option=selected_option,
    )


async def get_pending_user_approvals(
    person_id: str,
    session_id: Optional[str] = None,
) -> List[ApprovalRequest]:
    """Get pending approvals for a user."""
    manager = get_approval_manager()
    return await manager.get_pending_approvals(person_id, session_id)


__all__ = [
    # Enums
    "ActionRisk",
    "ApprovalStatus",
    # Models
    "ApprovalRequest",
    "ApprovalResponse",
    # Classification
    "classify_action_risk",
    "requires_approval",
    # Manager
    "ApprovalManager",
    "get_approval_manager",
    # Convenience
    "request_action_approval",
    "submit_approval_response",
    "get_pending_user_approvals",
]
