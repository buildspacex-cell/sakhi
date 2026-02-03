"""
Inter-Sakhi Communication
-------------------------
Real cross-instance Sakhi-to-Sakhi messaging.

Enables two Sakhi instances (on different servers/ports) to:
- Discover each other
- Send coordination messages
- Receive and process incoming requests
- Handle offline/async responses

Architecture:
    Your Sakhi (8080)                    Mom's Sakhi (8081)
         │                                    │
         ├─── POST /mesh/send ────────────────►
         │    {to: "mom-sakhi-id",            │
         │     type: "scheduling_request",    │
         │     payload: {...}}                │
         │                                    │
         ◄─── POST /mesh/receive ─────────────┤
              {from: "mom-sakhi-id",          │
               type: "scheduling_response",   │
               payload: {...}}                │
"""

from __future__ import annotations

import logging
import uuid
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)

# Default timeout for cross-instance calls
DEFAULT_TIMEOUT = 30.0


# =============================================================================
# Models
# =============================================================================

class MeshMessageType(str, Enum):
    """Types of inter-Sakhi messages."""
    # Discovery
    PING = "ping"
    PONG = "pong"
    REGISTER = "register"

    # Coordination
    SCHEDULING_REQUEST = "scheduling_request"
    SCHEDULING_RESPONSE = "scheduling_response"
    AVAILABILITY_REQUEST = "availability_request"
    AVAILABILITY_RESPONSE = "availability_response"

    # Transactions
    INQUIRY = "inquiry"
    INQUIRY_RESPONSE = "inquiry_response"

    # System
    ACK = "ack"
    ERROR = "error"


class MeshMessage(BaseModel):
    """A message sent between Sakhi instances."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_sakhi_id: str
    to_sakhi_id: str
    message_type: MeshMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    reply_to: Optional[str] = None  # ID of message this is replying to
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signature: Optional[str] = None  # HMAC signature for auth


class SakhiEndpoint(BaseModel):
    """A registered Sakhi instance endpoint."""
    sakhi_id: str
    person_id: str
    endpoint_url: str  # e.g., "https://sakhi.example.com:8080/mesh"
    public_key: Optional[str] = None
    display_name: Optional[str] = None
    last_seen: Optional[datetime] = None
    is_online: bool = True


class MeshSendResult(BaseModel):
    """Result of sending a mesh message."""
    success: bool
    message_id: str
    delivered: bool = False
    queued: bool = False
    error: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


# =============================================================================
# Sakhi Discovery
# =============================================================================

async def register_sakhi_endpoint(
    sakhi_id: str,
    person_id: str,
    endpoint_url: str,
    display_name: Optional[str] = None,
    public_key: Optional[str] = None,
) -> SakhiEndpoint:
    """
    Register this Sakhi instance's endpoint for discovery.

    Call this on startup to announce this Sakhi to the mesh.
    """
    await dbexec(
        """
        INSERT INTO mesh_endpoints (sakhi_id, person_id, endpoint_url, display_name, public_key, last_seen)
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (sakhi_id) DO UPDATE
        SET endpoint_url = $3,
            display_name = COALESCE($4, mesh_endpoints.display_name),
            public_key = COALESCE($5, mesh_endpoints.public_key),
            last_seen = NOW()
        """,
        sakhi_id,
        person_id,
        endpoint_url,
        display_name,
        public_key,
    )

    LOGGER.info("[inter_sakhi] Registered endpoint: %s -> %s", sakhi_id, endpoint_url)

    return SakhiEndpoint(
        sakhi_id=sakhi_id,
        person_id=person_id,
        endpoint_url=endpoint_url,
        display_name=display_name,
        public_key=public_key,
        last_seen=datetime.utcnow(),
        is_online=True,
    )


async def lookup_sakhi_endpoint(sakhi_id: str) -> Optional[SakhiEndpoint]:
    """Look up a Sakhi's endpoint by ID."""
    row = await dbfetch(
        """
        SELECT sakhi_id, person_id, endpoint_url, display_name, public_key, last_seen
        FROM mesh_endpoints
        WHERE sakhi_id = $1
        """,
        sakhi_id,
        one=True,
    )

    if not row:
        return None

    # Check if online (seen in last 5 minutes)
    last_seen = row.get("last_seen")
    is_online = False
    if last_seen:
        if isinstance(last_seen, str):
            last_seen = datetime.fromisoformat(last_seen)
        is_online = (datetime.utcnow() - last_seen) < timedelta(minutes=5)

    return SakhiEndpoint(
        sakhi_id=row["sakhi_id"],
        person_id=row["person_id"],
        endpoint_url=row["endpoint_url"],
        display_name=row.get("display_name"),
        public_key=row.get("public_key"),
        last_seen=last_seen,
        is_online=is_online,
    )


async def lookup_sakhi_by_person(person_id: str) -> Optional[SakhiEndpoint]:
    """Look up a Sakhi's endpoint by person ID."""
    row = await dbfetch(
        """
        SELECT sakhi_id, person_id, endpoint_url, display_name, public_key, last_seen
        FROM mesh_endpoints
        WHERE person_id = $1
        ORDER BY last_seen DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )

    if not row:
        return None

    last_seen = row.get("last_seen")
    is_online = False
    if last_seen:
        if isinstance(last_seen, str):
            last_seen = datetime.fromisoformat(last_seen)
        is_online = (datetime.utcnow() - last_seen) < timedelta(minutes=5)

    return SakhiEndpoint(
        sakhi_id=row["sakhi_id"],
        person_id=row["person_id"],
        endpoint_url=row["endpoint_url"],
        display_name=row.get("display_name"),
        public_key=row.get("public_key"),
        last_seen=last_seen,
        is_online=is_online,
    )


async def update_sakhi_heartbeat(sakhi_id: str) -> None:
    """Update the last_seen timestamp for a Sakhi."""
    await dbexec(
        "UPDATE mesh_endpoints SET last_seen = NOW() WHERE sakhi_id = $1",
        sakhi_id,
    )


# =============================================================================
# Message Signing
# =============================================================================

def sign_message(message: MeshMessage, secret: str) -> str:
    """Sign a message using HMAC-SHA256."""
    payload = json.dumps({
        "message_id": message.message_id,
        "from_sakhi_id": message.from_sakhi_id,
        "to_sakhi_id": message.to_sakhi_id,
        "message_type": message.message_type.value,
        "timestamp": message.timestamp.isoformat(),
    }, sort_keys=True)

    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_signature(message: MeshMessage, signature: str, secret: str) -> bool:
    """Verify a message signature."""
    expected = sign_message(message, secret)
    return hmac.compare_digest(expected, signature)


# =============================================================================
# Send Messages
# =============================================================================

async def send_mesh_message(
    from_sakhi_id: str,
    to_sakhi_id: str,
    message_type: MeshMessageType,
    payload: Dict[str, Any],
    reply_to: Optional[str] = None,
    secret: Optional[str] = None,
) -> MeshSendResult:
    """
    Send a message to another Sakhi instance.

    Args:
        from_sakhi_id: This Sakhi's ID
        to_sakhi_id: Target Sakhi's ID
        message_type: Type of message
        payload: Message payload
        reply_to: ID of message this is responding to
        secret: Shared secret for signing (optional)

    Returns:
        MeshSendResult with delivery status
    """
    # Create message
    message = MeshMessage(
        from_sakhi_id=from_sakhi_id,
        to_sakhi_id=to_sakhi_id,
        message_type=message_type,
        payload=payload,
        reply_to=reply_to,
    )

    # Sign if secret provided
    if secret:
        message.signature = sign_message(message, secret)

    # Look up target endpoint
    target = await lookup_sakhi_endpoint(to_sakhi_id)

    if not target:
        # Try to find by person ID in payload
        if "person_id" in payload:
            target = await lookup_sakhi_by_person(payload["person_id"])

    if not target:
        # Queue for later delivery
        await queue_message(message)
        return MeshSendResult(
            success=True,
            message_id=message.message_id,
            delivered=False,
            queued=True,
            error="Target Sakhi not found - message queued",
        )

    # Send to target endpoint
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"{target.endpoint_url}/receive",
                json=message.model_dump(mode="json"),
            )

            if response.status_code == 200:
                data = response.json()
                return MeshSendResult(
                    success=True,
                    message_id=message.message_id,
                    delivered=True,
                    response=data,
                )
            else:
                # Queue for retry
                await queue_message(message)
                return MeshSendResult(
                    success=False,
                    message_id=message.message_id,
                    delivered=False,
                    queued=True,
                    error=f"Target returned {response.status_code}",
                )

    except httpx.RequestError as e:
        # Target offline - queue for later
        LOGGER.warning(
            "[inter_sakhi] Failed to reach %s: %s - queuing",
            target.endpoint_url, e
        )
        await queue_message(message)
        return MeshSendResult(
            success=True,
            message_id=message.message_id,
            delivered=False,
            queued=True,
            error="Target offline - message queued",
        )


async def queue_message(message: MeshMessage) -> None:
    """Queue a message for later delivery."""
    await dbexec(
        """
        INSERT INTO mesh_message_queue (
            message_id, from_sakhi_id, to_sakhi_id, message_type,
            payload, reply_to, created_at, attempts
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), 0)
        ON CONFLICT (message_id) DO UPDATE
        SET attempts = mesh_message_queue.attempts + 1,
            last_attempt = NOW()
        """,
        message.message_id,
        message.from_sakhi_id,
        message.to_sakhi_id,
        message.message_type.value,
        json.dumps(message.payload),
        message.reply_to,
    )


async def get_queued_messages(to_sakhi_id: str, limit: int = 10) -> List[MeshMessage]:
    """Get queued messages for a Sakhi (called when it comes online)."""
    rows = await dbfetch(
        """
        SELECT message_id, from_sakhi_id, to_sakhi_id, message_type,
               payload, reply_to, created_at
        FROM mesh_message_queue
        WHERE to_sakhi_id = $1
          AND delivered_at IS NULL
        ORDER BY created_at ASC
        LIMIT $2
        """,
        to_sakhi_id,
        limit,
    )

    messages = []
    for row in rows or []:
        payload = row.get("payload")
        if isinstance(payload, str):
            payload = json.loads(payload)

        messages.append(MeshMessage(
            message_id=row["message_id"],
            from_sakhi_id=row["from_sakhi_id"],
            to_sakhi_id=row["to_sakhi_id"],
            message_type=MeshMessageType(row["message_type"]),
            payload=payload or {},
            reply_to=row.get("reply_to"),
            timestamp=row.get("created_at", datetime.utcnow()),
        ))

    return messages


async def mark_message_delivered(message_id: str) -> None:
    """Mark a queued message as delivered."""
    await dbexec(
        "UPDATE mesh_message_queue SET delivered_at = NOW() WHERE message_id = $1",
        message_id,
    )


# =============================================================================
# Receive Messages
# =============================================================================

async def process_incoming_message(
    message: MeshMessage,
    my_sakhi_id: str,
    secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process an incoming mesh message.

    Args:
        message: The received message
        my_sakhi_id: This Sakhi's ID
        secret: Shared secret for verifying signatures

    Returns:
        Response to send back
    """
    # Verify target
    if message.to_sakhi_id != my_sakhi_id:
        return {"success": False, "error": "Message not for this Sakhi"}

    # Verify signature if provided
    if message.signature and secret:
        if not verify_signature(message, message.signature, secret):
            return {"success": False, "error": "Invalid signature"}

    # Log receipt
    LOGGER.info(
        "[inter_sakhi] Received %s from %s",
        message.message_type.value,
        message.from_sakhi_id,
    )

    # Update sender's heartbeat
    await update_sakhi_heartbeat(message.from_sakhi_id)

    # Store incoming message
    await store_message(message)

    # Process by type
    if message.message_type == MeshMessageType.PING:
        return {
            "success": True,
            "message_type": "pong",
            "sakhi_id": my_sakhi_id,
        }

    elif message.message_type == MeshMessageType.SCHEDULING_REQUEST:
        # Handle scheduling request
        return await handle_scheduling_request(message)

    elif message.message_type == MeshMessageType.AVAILABILITY_REQUEST:
        # Handle availability request
        return await handle_availability_request(message)

    elif message.message_type == MeshMessageType.INQUIRY:
        # Handle inquiry
        return await handle_inquiry(message)

    else:
        return {
            "success": True,
            "message_id": message.message_id,
            "message": "Received",
        }


async def store_message(message: MeshMessage) -> None:
    """Store a received message for history."""
    await dbexec(
        """
        INSERT INTO mesh_messages (
            message_id, from_sakhi_id, to_sakhi_id, message_type,
            payload, reply_to, received_at
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (message_id) DO NOTHING
        """,
        message.message_id,
        message.from_sakhi_id,
        message.to_sakhi_id,
        message.message_type.value,
        json.dumps(message.payload),
        message.reply_to,
    )


# =============================================================================
# Message Handlers
# =============================================================================

async def handle_scheduling_request(message: MeshMessage) -> Dict[str, Any]:
    """Handle an incoming scheduling request."""
    payload = message.payload

    # Get the person ID for this Sakhi
    endpoint = await lookup_sakhi_endpoint(message.to_sakhi_id)
    if not endpoint:
        return {"success": False, "error": "Sakhi not found"}

    person_id = endpoint.person_id

    # Use coordination service to handle
    try:
        from sakhi.apps.api.services.mesh.coordination import (
            initiate_coordination,
            ProposalRequest,
            CoordinationType,
        )

        # Find initiator endpoint
        initiator = await lookup_sakhi_endpoint(message.from_sakhi_id)
        if not initiator:
            return {"success": False, "error": "Initiator not found"}

        # Create proposal request
        request = ProposalRequest(
            recipient_id=person_id,
            coordination_type=CoordinationType(payload.get("type", "scheduling")),
            event_type=payload.get("event_type"),
            timeframe=payload.get("timeframe"),
            duration_minutes=payload.get("duration_minutes", 60),
            location_hint=payload.get("location_hint"),
            preferred_times=payload.get("preferred_times"),
        )

        response = await initiate_coordination(initiator.person_id, request)

        return {
            "success": True,
            "thread_id": response.thread_id,
            "proposed_times": response.proposed_times,
            "message": response.message,
        }

    except Exception as e:
        LOGGER.exception("[inter_sakhi] Failed to handle scheduling request: %s", e)
        return {"success": False, "error": str(e)}


async def handle_availability_request(message: MeshMessage) -> Dict[str, Any]:
    """Handle an incoming availability request."""
    payload = message.payload

    # Get person ID
    endpoint = await lookup_sakhi_endpoint(message.to_sakhi_id)
    if not endpoint:
        return {"success": False, "error": "Sakhi not found"}

    try:
        from sakhi.apps.api.services.mesh.availability import (
            compute_shareable_availability,
        )
        from sakhi.apps.api.services.mesh.connections import get_trust_level

        # Get initiator's person ID
        initiator = await lookup_sakhi_endpoint(message.from_sakhi_id)
        if not initiator:
            return {"success": False, "error": "Initiator not found"}

        # Get trust level to determine sharing
        trust = await get_trust_level(endpoint.person_id, initiator.person_id)

        # Get shareable availability
        start = datetime.fromisoformat(payload.get("start", datetime.utcnow().isoformat()))
        end = datetime.fromisoformat(payload.get("end", (datetime.utcnow() + timedelta(days=7)).isoformat()))

        availability = await compute_shareable_availability(
            person_id=endpoint.person_id,
            requester_id=initiator.person_id,
            start_date=start,
            end_date=end,
            trust_level=trust,
        )

        return {
            "success": True,
            "availability": availability,
        }

    except Exception as e:
        LOGGER.exception("[inter_sakhi] Failed to handle availability request: %s", e)
        return {"success": False, "error": str(e)}


async def handle_inquiry(message: MeshMessage) -> Dict[str, Any]:
    """Handle a general inquiry message."""
    payload = message.payload
    question = payload.get("question", "")

    # For now, just acknowledge and store
    return {
        "success": True,
        "message_id": message.message_id,
        "acknowledged": True,
        "message": f"Inquiry received: {question[:50]}...",
    }


# =============================================================================
# Convenience Functions
# =============================================================================

async def ping_sakhi(from_sakhi_id: str, to_sakhi_id: str) -> bool:
    """Ping another Sakhi to check if online."""
    result = await send_mesh_message(
        from_sakhi_id=from_sakhi_id,
        to_sakhi_id=to_sakhi_id,
        message_type=MeshMessageType.PING,
        payload={},
    )
    return result.delivered


async def request_scheduling(
    from_sakhi_id: str,
    to_sakhi_id: str,
    event_type: str,
    timeframe: str,
    duration_minutes: int = 60,
    preferred_times: Optional[List[Dict[str, Any]]] = None,
) -> MeshSendResult:
    """
    Send a scheduling request to another Sakhi.

    Example:
        >>> await request_scheduling(
        ...     from_sakhi_id="my-sakhi",
        ...     to_sakhi_id="mom-sakhi",
        ...     event_type="dinner",
        ...     timeframe="this weekend",
        ...     duration_minutes=120,
        ... )
    """
    return await send_mesh_message(
        from_sakhi_id=from_sakhi_id,
        to_sakhi_id=to_sakhi_id,
        message_type=MeshMessageType.SCHEDULING_REQUEST,
        payload={
            "type": "scheduling",
            "event_type": event_type,
            "timeframe": timeframe,
            "duration_minutes": duration_minutes,
            "preferred_times": preferred_times,
        },
    )


__all__ = [
    "MeshMessageType",
    "MeshMessage",
    "SakhiEndpoint",
    "MeshSendResult",
    "register_sakhi_endpoint",
    "lookup_sakhi_endpoint",
    "lookup_sakhi_by_person",
    "send_mesh_message",
    "process_incoming_message",
    "ping_sakhi",
    "request_scheduling",
    "get_queued_messages",
    "mark_message_delivered",
]
