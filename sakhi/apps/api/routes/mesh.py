"""
Sakhi Mesh API Routes
---------------------
Sakhi-to-Sakhi coordination endpoints.

Your Sakhi talks to other Sakhis so you don't have to
coordinate manually. Share availability, propose times,
and let your Sakhis figure out when to meet.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sakhi.apps.api.services.mesh import (
    # Profiles
    SakhiProfile,
    CreateProfileRequest,
    UpdateProfileRequest,
    get_profile,
    create_profile,
    update_profile,
    find_by_handle,
    search_profiles,
    add_auto_accept,
    remove_auto_accept,
    update_last_active,
    # Connections
    TrustLevel,
    ConnectionStatus,
    SakhiConnection,
    ConnectRequest,
    get_connection,
    are_connected,
    get_trust_level,
    request_connection,
    accept_connection,
    decline_connection,
    update_trust_level,
    disconnect,
    block,
    get_connections,
    get_pending_requests,
    link_relationship,
    # Coordination
    CoordinationType,
    CoordinationStatus,
    MessageType,
    CoordinationThread,
    CoordinationMessage,
    ProposalRequest,
    ProposalResponse,
    initiate_coordination,
    respond_to_proposal,
    get_pending_proposals,
    get_active_threads,
)
from sakhi.apps.api.services.mesh.inter_sakhi import (
    MeshMessageType,
    MeshMessage,
    SakhiEndpoint,
    MeshSendResult,
    register_sakhi_endpoint,
    lookup_sakhi_endpoint,
    send_mesh_message,
    process_incoming_message,
    ping_sakhi,
    request_scheduling,
    get_queued_messages,
    mark_message_delivered,
)
from sakhi.apps.api.services.mesh.discovery import (
    DiscoveryResult,
    DiscoveryIndex,
    discover_sakhi,
    discover_sakhis_batch,
    register_for_discovery,
    unregister_from_discovery,
    search_discoverable,
    search_businesses,
    get_discovery_stats,
)
from sakhi.apps.api.services.mesh.auth import (
    generate_key_pair,
    rotate_sakhi_keys,
    create_mesh_jwt_async,
    verify_mesh_jwt_async,
    sign_mesh_message_async,
    verify_mesh_message,
    is_trusted_sender,
    get_auth_requirements,
    store_private_key,
)
from sakhi.apps.api.services.mesh.async_handler import (
    QueuedMessage,
    MessageStatus,
    DeliveryResult,
    queue_message_for_delivery,
    get_pending_messages,
    get_message_status,
    attempt_delivery,
    process_message_queue,
    correlate_response,
    get_conversation_thread,
    deliver_on_online,
    cleanup_old_messages,
)

import logging

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/mesh", tags=["Mesh"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ProfileCreateRequest(BaseModel):
    """Request to create a Sakhi profile for mesh coordination."""
    display_name: str = Field(..., description="Display name for other Sakhis")
    sakhi_handle: Optional[str] = Field(None, description="Unique @handle for discovery")
    share_availability: bool = Field(True, description="Whether to share availability")
    availability_detail: str = Field(
        "windows",
        description="Detail level: none, busy_free, windows, full"
    )
    discoverable: bool = Field(True, description="Can be found via search")


class ProfileUpdateRequest(BaseModel):
    """Request to update Sakhi profile."""
    display_name: Optional[str] = None
    sakhi_handle: Optional[str] = None
    share_availability: Optional[bool] = None
    availability_detail: Optional[str] = None
    require_confirmation: Optional[bool] = None
    discoverable: Optional[bool] = None


class ConnectionRequest(BaseModel):
    """Request to connect with another Sakhi."""
    to_handle: str = Field(..., description="Handle of person to connect with")
    trust_level: str = Field("friend", description="Initial trust level")
    message: Optional[str] = Field(None, description="Optional message with request")


class ConnectionResponse(BaseModel):
    """Response for connection operations."""
    to_person_id: str
    to_handle: Optional[str]
    status: str
    trust_level: Optional[str]
    message: Optional[str]


class TrustUpdateRequest(BaseModel):
    """Request to update trust level for a connection."""
    trust_level: str = Field(..., description="New trust level")


class CoordinationInitRequest(BaseModel):
    """Request to initiate scheduling coordination."""
    with_handle: str = Field(..., description="Handle of person to coordinate with")
    coordination_type: str = Field("scheduling", description="Type of coordination")
    event_type: Optional[str] = Field(None, description="Event type: dinner, coffee, call")
    timeframe: Optional[str] = Field(None, description="Timeframe: this week, next few days")
    duration_minutes: int = Field(60, description="Expected duration")
    location_hint: Optional[str] = Field(None, description="Location preference")
    preferred_times: Optional[List[Dict[str, Any]]] = Field(
        None, description="Specific preferred times"
    )


class CoordinationResponseRequest(BaseModel):
    """Request to respond to a coordination proposal."""
    accept: bool = Field(..., description="Whether to accept")
    selected_time: Optional[Dict[str, str]] = Field(
        None, description="Selected time slot if accepting"
    )
    counter_times: Optional[List[Dict[str, Any]]] = Field(
        None, description="Counter-proposal times if declining"
    )
    message: Optional[str] = Field(None, description="Optional message")


# =============================================================================
# Profile Endpoints
# =============================================================================

@router.get("/profile/{person_id}")
async def get_mesh_profile(person_id: str) -> Dict[str, Any]:
    """Get a user's Sakhi mesh profile."""
    profile = await get_profile(person_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile.model_dump()


@router.post("/profile/{person_id}")
async def create_mesh_profile(
    person_id: str,
    data: ProfileCreateRequest,
) -> Dict[str, Any]:
    """Create a Sakhi mesh profile for coordination."""
    request = CreateProfileRequest(
        person_id=person_id,
        display_name=data.display_name,
        sakhi_handle=data.sakhi_handle,
        share_availability=data.share_availability,
        availability_detail=data.availability_detail,
        discoverable=data.discoverable,
    )

    profile = await create_profile(request)

    return {
        "status": "created",
        "profile": profile.model_dump(),
    }


@router.patch("/profile/{person_id}")
async def update_mesh_profile(
    person_id: str,
    data: ProfileUpdateRequest,
) -> Dict[str, Any]:
    """Update Sakhi mesh profile."""
    request = UpdateProfileRequest(
        display_name=data.display_name,
        sakhi_handle=data.sakhi_handle,
        share_availability=data.share_availability,
        availability_detail=data.availability_detail,
        require_confirmation=data.require_confirmation,
        discoverable=data.discoverable,
    )

    profile = await update_profile(person_id, request)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "status": "updated",
        "profile": profile.model_dump(),
    }


@router.get("/profile/handle/{handle}")
async def find_profile_by_handle(handle: str) -> Dict[str, Any]:
    """Find a Sakhi profile by handle."""
    profile = await find_by_handle(handle)

    if not profile:
        raise HTTPException(status_code=404, detail="Handle not found")

    return profile.model_dump()


@router.get("/search")
async def search_sakhi_profiles(
    q: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search for discoverable Sakhi profiles."""
    profiles = await search_profiles(q, limit=limit)

    return {
        "query": q,
        "count": len(profiles),
        "profiles": [p.model_dump() for p in profiles],
    }


# =============================================================================
# Connection Endpoints
# =============================================================================

@router.post("/connect/{person_id}")
async def request_mesh_connection(
    person_id: str,
    data: ConnectionRequest,
) -> Dict[str, Any]:
    """Request to connect with another Sakhi user."""
    # Find target by handle
    target = await find_by_handle(data.to_handle)
    if not target:
        raise HTTPException(status_code=404, detail="Handle not found")

    request = ConnectRequest(
        to_person_id=target.person_id,
        trust_level=TrustLevel(data.trust_level),
        message=data.message,
    )

    connection = await request_connection(person_id, request)

    return {
        "status": "pending",
        "connection_id": connection.id,
        "to_person_id": connection.to_person_id,
        "message": "Connection request sent",
    }


@router.post("/connect/{person_id}/accept/{connection_id}")
async def accept_mesh_connection(
    person_id: str,
    connection_id: str,
    trust_level: str = "friend",
) -> Dict[str, Any]:
    """Accept a pending connection request."""
    connection = await accept_connection(person_id, connection_id, TrustLevel(trust_level))

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {
        "status": "connected",
        "connection": connection.model_dump(),
    }


@router.post("/connect/{person_id}/decline/{connection_id}")
async def decline_mesh_connection(
    person_id: str,
    connection_id: str,
) -> Dict[str, Any]:
    """Decline a pending connection request."""
    success = await decline_connection(person_id, connection_id)

    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {"status": "declined"}


@router.get("/connections/{person_id}")
async def list_connections(
    person_id: str,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List all connections for a user."""
    conn_status = ConnectionStatus(status) if status else None
    connections = await get_connections(person_id, status=conn_status)

    return {
        "person_id": person_id,
        "count": len(connections),
        "connections": [c.model_dump() for c in connections],
    }


@router.get("/connections/{person_id}/pending")
async def list_pending_requests(person_id: str) -> Dict[str, Any]:
    """List pending connection requests."""
    pending = await get_pending_requests(person_id)

    return {
        "person_id": person_id,
        "count": len(pending),
        "pending": [c.model_dump() for c in pending],
    }


@router.patch("/connections/{person_id}/{connection_id}/trust")
async def update_connection_trust(
    person_id: str,
    connection_id: str,
    data: TrustUpdateRequest,
) -> Dict[str, Any]:
    """Update the trust level for a connection."""
    connection = await update_trust_level(
        person_id, connection_id, TrustLevel(data.trust_level)
    )

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {
        "status": "updated",
        "trust_level": connection.trust_level.value,
    }


@router.delete("/connections/{person_id}/{connection_id}")
async def remove_connection(
    person_id: str,
    connection_id: str,
) -> Dict[str, Any]:
    """Disconnect from a Sakhi connection."""
    success = await disconnect(person_id, connection_id)

    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {"status": "disconnected"}


@router.post("/connections/{person_id}/{connection_id}/block")
async def block_connection(
    person_id: str,
    connection_id: str,
) -> Dict[str, Any]:
    """Block a Sakhi connection."""
    success = await block(person_id, connection_id)

    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {"status": "blocked"}


@router.post("/connections/{person_id}/{connection_id}/link-relationship")
async def link_connection_relationship(
    person_id: str,
    connection_id: str,
    relationship_id: str,
) -> Dict[str, Any]:
    """Link a mesh connection to an existing relationship."""
    success = await link_relationship(person_id, connection_id, relationship_id)

    if not success:
        raise HTTPException(status_code=404, detail="Connection or relationship not found")

    return {"status": "linked", "relationship_id": relationship_id}


# =============================================================================
# Coordination Endpoints
# =============================================================================

@router.post("/coordinate/{person_id}")
async def initiate_mesh_coordination(
    person_id: str,
    data: CoordinationInitRequest,
) -> Dict[str, Any]:
    """
    Initiate Sakhi-to-Sakhi scheduling coordination.

    Your Sakhi will find overlapping availability and
    propose times to the other person's Sakhi.
    """
    # Find target by handle
    target = await find_by_handle(data.with_handle)
    if not target:
        raise HTTPException(status_code=404, detail="Handle not found")

    # Check if connected
    connected = await are_connected(person_id, target.person_id)
    if not connected:
        raise HTTPException(
            status_code=403,
            detail="Not connected. Send a connection request first."
        )

    request = ProposalRequest(
        recipient_id=target.person_id,
        coordination_type=CoordinationType(data.coordination_type),
        event_type=data.event_type,
        timeframe=data.timeframe,
        duration_minutes=data.duration_minutes,
        location_hint=data.location_hint,
        preferred_times=data.preferred_times,
    )

    response = await initiate_coordination(person_id, request)

    return {
        "status": "proposed",
        "thread_id": response.thread_id,
        "proposed_times": response.proposed_times,
        "message": response.message,
    }


@router.post("/coordinate/{person_id}/respond/{thread_id}")
async def respond_to_coordination(
    person_id: str,
    thread_id: str,
    data: CoordinationResponseRequest,
) -> Dict[str, Any]:
    """
    Respond to a coordination proposal.

    Accept to schedule the event, or counter-propose alternative times.
    """
    response = await respond_to_proposal(
        responder_id=person_id,
        thread_id=thread_id,
        accept=data.accept,
        selected_time=data.selected_time,
        counter_times=data.counter_times,
        message=data.message,
    )

    if not response:
        raise HTTPException(status_code=404, detail="Thread not found")

    result: Dict[str, Any] = {
        "status": response.status.value,
        "thread_id": thread_id,
    }

    if response.event_created:
        result["event_created"] = True
        result["event_id"] = response.event_id
        result["agreed_time"] = response.agreed_time
        result["message"] = "Event scheduled for both calendars!"
    elif response.proposed_times:
        result["counter_proposed"] = True
        result["proposed_times"] = response.proposed_times
        result["message"] = response.message
    else:
        result["message"] = response.message

    return result


@router.get("/coordinate/{person_id}/pending")
async def list_pending_proposals(person_id: str) -> Dict[str, Any]:
    """List pending coordination proposals awaiting response."""
    proposals = await get_pending_proposals(person_id)

    return {
        "person_id": person_id,
        "count": len(proposals),
        "pending": [
            {
                "thread_id": p.id,
                "from": p.initiator_id,
                "coordination_type": p.coordination_type.value,
                "event_type": p.event_type,
                "timeframe": p.timeframe,
                "proposed_times": p.preferred_times,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in proposals
        ],
    }


@router.get("/coordinate/{person_id}/active")
async def list_active_threads(person_id: str) -> Dict[str, Any]:
    """List all active coordination threads."""
    threads = await get_active_threads(person_id)

    return {
        "person_id": person_id,
        "count": len(threads),
        "threads": [
            {
                "thread_id": t.id,
                "with": t.recipient_id if t.initiator_id == person_id else t.initiator_id,
                "coordination_type": t.coordination_type.value,
                "status": t.status.value,
                "event_type": t.event_type,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in threads
        ],
    }


# =============================================================================
# Auto-accept Management
# =============================================================================

@router.post("/profile/{person_id}/auto-accept/{target_person_id}")
async def add_auto_accept_person(
    person_id: str,
    target_person_id: str,
) -> Dict[str, Any]:
    """Add someone to auto-accept list (can schedule without confirmation)."""
    success = await add_auto_accept(person_id, target_person_id)

    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {"status": "added", "auto_accept_for": target_person_id}


@router.delete("/profile/{person_id}/auto-accept/{target_person_id}")
async def remove_auto_accept_person(
    person_id: str,
    target_person_id: str,
) -> Dict[str, Any]:
    """Remove someone from auto-accept list."""
    success = await remove_auto_accept(person_id, target_person_id)

    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {"status": "removed", "auto_accept_for": target_person_id}


# =============================================================================
# Mesh Status Check
# =============================================================================

@router.get("/check/{person_id}/{target_handle}")
async def check_mesh_status(
    person_id: str,
    target_handle: str,
) -> Dict[str, Any]:
    """
    Check if someone has Sakhi and connection status.

    Used to determine if Sakhi-to-Sakhi coordination is available.
    """
    target = await find_by_handle(target_handle)

    if not target:
        return {
            "has_sakhi": False,
            "connected": False,
            "can_coordinate": False,
            "message": f"@{target_handle} is not on Sakhi mesh yet",
        }

    connected = await are_connected(person_id, target.person_id)
    trust = await get_trust_level(person_id, target.person_id) if connected else None

    return {
        "has_sakhi": True,
        "target_person_id": target.person_id,
        "display_name": target.display_name,
        "connected": connected,
        "trust_level": trust.value if trust else None,
        "can_coordinate": connected,
        "shares_availability": target.share_availability if connected else None,
        "message": (
            f"Ready to coordinate with @{target_handle}" if connected
            else f"@{target_handle} is on Sakhi. Send a connection request to coordinate."
        ),
    }


# =============================================================================
# Inter-Sakhi Messaging (Cross-Instance)
# =============================================================================

class RegisterEndpointRequest(BaseModel):
    """Request to register this Sakhi's endpoint."""
    sakhi_id: str = Field(..., description="Unique ID for this Sakhi instance")
    endpoint_url: str = Field(..., description="URL for this Sakhi's mesh endpoint")
    display_name: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Request to send a message to another Sakhi."""
    to_sakhi_id: str = Field(..., description="Target Sakhi's ID")
    message_type: str = Field("inquiry", description="Type of message")
    payload: Dict[str, Any] = Field(default_factory=dict)


class SchedulingRequest(BaseModel):
    """Request to send a scheduling message to another Sakhi."""
    to_sakhi_id: str = Field(..., description="Target Sakhi's ID")
    event_type: str = Field(..., description="Event type: dinner, coffee, call")
    timeframe: str = Field(..., description="Timeframe: this week, next few days")
    duration_minutes: int = Field(60, description="Expected duration")
    preferred_times: Optional[List[Dict[str, Any]]] = None


@router.post("/register")
async def register_endpoint(
    person_id: str,
    data: RegisterEndpointRequest,
) -> Dict[str, Any]:
    """
    Register this Sakhi instance's endpoint for discovery.

    Call this on startup so other Sakhis can find and message this instance.
    """
    endpoint = await register_sakhi_endpoint(
        sakhi_id=data.sakhi_id,
        person_id=person_id,
        endpoint_url=data.endpoint_url,
        display_name=data.display_name,
    )

    return {
        "status": "registered",
        "sakhi_id": endpoint.sakhi_id,
        "endpoint_url": endpoint.endpoint_url,
    }


@router.get("/endpoint/{sakhi_id}")
async def get_endpoint(sakhi_id: str) -> Dict[str, Any]:
    """Look up a Sakhi's endpoint by ID."""
    endpoint = await lookup_sakhi_endpoint(sakhi_id)

    if not endpoint:
        raise HTTPException(status_code=404, detail="Sakhi endpoint not found")

    return {
        "sakhi_id": endpoint.sakhi_id,
        "person_id": endpoint.person_id,
        "endpoint_url": endpoint.endpoint_url,
        "display_name": endpoint.display_name,
        "is_online": endpoint.is_online,
        "last_seen": endpoint.last_seen.isoformat() if endpoint.last_seen else None,
    }


@router.post("/send")
async def send_message(
    person_id: str,
    data: SendMessageRequest,
) -> Dict[str, Any]:
    """
    Send a message to another Sakhi instance.

    Used for cross-instance communication when Sakhis are on different servers.
    """
    # Get sender's Sakhi ID
    from sakhi.apps.api.services.mesh.inter_sakhi import lookup_sakhi_by_person

    sender = await lookup_sakhi_by_person(person_id)
    if not sender:
        raise HTTPException(
            status_code=400,
            detail="Register your Sakhi endpoint first via POST /mesh/register"
        )

    try:
        msg_type = MeshMessageType(data.message_type)
    except ValueError:
        msg_type = MeshMessageType.INQUIRY

    result = await send_mesh_message(
        from_sakhi_id=sender.sakhi_id,
        to_sakhi_id=data.to_sakhi_id,
        message_type=msg_type,
        payload=data.payload,
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "delivered": result.delivered,
        "queued": result.queued,
        "error": result.error,
        "response": result.response,
    }


@router.post("/send/scheduling")
async def send_scheduling_request(
    person_id: str,
    data: SchedulingRequest,
) -> Dict[str, Any]:
    """
    Send a scheduling request to another Sakhi.

    Your Sakhi → Other Sakhi: "Let's find time for dinner this weekend"
    """
    from sakhi.apps.api.services.mesh.inter_sakhi import lookup_sakhi_by_person

    sender = await lookup_sakhi_by_person(person_id)
    if not sender:
        raise HTTPException(
            status_code=400,
            detail="Register your Sakhi endpoint first"
        )

    result = await request_scheduling(
        from_sakhi_id=sender.sakhi_id,
        to_sakhi_id=data.to_sakhi_id,
        event_type=data.event_type,
        timeframe=data.timeframe,
        duration_minutes=data.duration_minutes,
        preferred_times=data.preferred_times,
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "delivered": result.delivered,
        "queued": result.queued,
        "response": result.response,
    }


@router.post("/receive")
async def receive_message(
    message: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Receive a message from another Sakhi instance.

    This is called by OTHER Sakhis when they send messages to this instance.
    """
    try:
        # Parse the incoming message
        msg = MeshMessage(
            message_id=message.get("message_id", ""),
            from_sakhi_id=message.get("from_sakhi_id", ""),
            to_sakhi_id=message.get("to_sakhi_id", ""),
            message_type=MeshMessageType(message.get("message_type", "inquiry")),
            payload=message.get("payload", {}),
            reply_to=message.get("reply_to"),
            signature=message.get("signature"),
        )

        # Get this Sakhi's ID from the to_sakhi_id
        my_sakhi_id = msg.to_sakhi_id

        # Process the message
        result = await process_incoming_message(
            message=msg,
            my_sakhi_id=my_sakhi_id,
        )

        return result

    except Exception as e:
        LOGGER.exception("[mesh] Failed to process incoming message: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/ping/{to_sakhi_id}")
async def ping_other_sakhi(
    person_id: str,
    to_sakhi_id: str,
) -> Dict[str, Any]:
    """Ping another Sakhi to check if online."""
    from sakhi.apps.api.services.mesh.inter_sakhi import lookup_sakhi_by_person

    sender = await lookup_sakhi_by_person(person_id)
    if not sender:
        raise HTTPException(status_code=400, detail="Register your Sakhi first")

    is_online = await ping_sakhi(sender.sakhi_id, to_sakhi_id)

    return {
        "target_sakhi_id": to_sakhi_id,
        "is_online": is_online,
    }


@router.get("/queued/{sakhi_id}")
async def get_queued(sakhi_id: str) -> Dict[str, Any]:
    """
    Get queued messages for this Sakhi.

    Call this when coming online to receive messages sent while offline.
    """
    messages = await get_queued_messages(sakhi_id)

    return {
        "sakhi_id": sakhi_id,
        "count": len(messages),
        "messages": [m.model_dump(mode="json") for m in messages],
    }


@router.post("/queued/{message_id}/delivered")
async def mark_delivered(message_id: str) -> Dict[str, Any]:
    """Mark a queued message as delivered."""
    await mark_message_delivered(message_id)
    return {"status": "delivered", "message_id": message_id}


# =============================================================================
# Discovery Routes (A.6)
# =============================================================================

class DiscoverRequest(BaseModel):
    """Request to discover a Sakhi."""
    identifier: str = Field(..., description="sakhi_id, person_id, or @handle")


class BatchDiscoverRequest(BaseModel):
    """Request to discover multiple Sakhis."""
    identifiers: List[str] = Field(..., description="List of identifiers")


class RegisterDiscoveryRequest(BaseModel):
    """Request to register for discovery."""
    handle: str = Field(..., description="Unique @handle (will be lowercased)")
    display_name: str = Field(..., description="Display name")
    entity_type: str = Field("personal", description="personal, business, or service")


@router.get("/discover/{identifier}")
async def discover_by_identifier(identifier: str) -> Dict[str, Any]:
    """
    Discover a Sakhi by any identifier.

    Accepts:
    - sakhi_id (UUID-like string)
    - person_id (UUID)
    - @handle (with or without @)
    """
    result = await discover_sakhi(identifier)

    if not result or not result.found:
        raise HTTPException(status_code=404, detail="Sakhi not found")

    return result.model_dump()


@router.post("/discover/batch")
async def discover_batch(data: BatchDiscoverRequest) -> Dict[str, Any]:
    """
    Batch discover multiple Sakhis.

    Returns dict mapping identifier -> discovery result (only found entries).
    """
    results = await discover_sakhis_batch(data.identifiers)

    return {
        "found": len(results),
        "results": {k: v.model_dump() for k, v in results.items()},
    }


@router.post("/discover/register/{person_id}")
async def register_discovery(
    person_id: str,
    data: RegisterDiscoveryRequest,
) -> Dict[str, Any]:
    """
    Register this Sakhi for discovery with a @handle.
    """
    from sakhi.apps.api.services.mesh.entities import EntityType

    try:
        entity_type = EntityType(data.entity_type)
    except ValueError:
        entity_type = EntityType.PERSONAL

    success = await register_for_discovery(
        person_id=person_id,
        handle=data.handle,
        display_name=data.display_name,
        entity_type=entity_type,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Handle @{data.handle} may already be taken"
        )

    return {
        "status": "registered",
        "handle": f"@{data.handle.lower()}",
        "person_id": person_id,
    }


@router.delete("/discover/register/{person_id}")
async def unregister_discovery_endpoint(person_id: str) -> Dict[str, Any]:
    """Remove this Sakhi from discovery."""
    success = await unregister_from_discovery(person_id)
    return {"status": "unregistered" if success else "failed"}


@router.get("/discover/search")
async def search_discovery(
    q: str,
    entity_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Search for discoverable Sakhis by name or handle.
    """
    from sakhi.apps.api.services.mesh.entities import EntityType

    e_type = None
    if entity_type:
        try:
            e_type = EntityType(entity_type)
        except ValueError:
            pass

    results = await search_discoverable(q, entity_type=e_type, limit=limit)

    return {
        "query": q,
        "count": len(results),
        "results": [r.model_dump() for r in results],
    }


@router.get("/discover/businesses")
async def search_business_sakhis(
    q: Optional[str] = None,
    business_type: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Search for business Sakhis.
    """
    results = await search_businesses(
        query=q,
        business_type=business_type,
        category=category,
        location=location,
        limit=limit,
    )

    return {
        "count": len(results),
        "results": [r.model_dump() for r in results],
    }


@router.get("/discover/stats")
async def get_network_stats() -> Dict[str, Any]:
    """Get stats about the discovery network."""
    return await get_discovery_stats()


# =============================================================================
# Auth Routes (A.6)
# =============================================================================

class GenerateKeysRequest(BaseModel):
    """Request to generate new key pair."""
    sakhi_id: str = Field(..., description="Sakhi ID to generate keys for")


class CreateTokenRequest(BaseModel):
    """Request to create a mesh JWT."""
    sakhi_id: str = Field(..., description="This Sakhi's ID (issuer)")
    subject: str = Field(..., description="Subject (message ID or purpose)")
    audience: Optional[str] = Field(None, description="Target Sakhi ID")
    message_type: Optional[str] = Field(None, description="Message type")
    payload: Optional[Dict[str, Any]] = Field(None, description="Payload for hash")


class VerifyTokenRequest(BaseModel):
    """Request to verify a mesh JWT."""
    token: str = Field(..., description="JWT to verify")
    issuer_sakhi_id: str = Field(..., description="Expected issuer")
    expected_audience: Optional[str] = Field(None, description="Expected audience")


@router.post("/auth/keys/generate")
async def generate_keys(data: GenerateKeysRequest) -> Dict[str, Any]:
    """
    Generate new RSA key pair for a Sakhi.

    Returns public key (private key should be stored securely by caller).
    """
    private_key, public_key = await rotate_sakhi_keys(data.sakhi_id)

    if not public_key:
        return {
            "status": "fallback",
            "message": "Using HMAC fallback (cryptography not installed)",
        }

    # Store private key securely
    stored = await store_private_key(data.sakhi_id, private_key)

    return {
        "status": "generated",
        "sakhi_id": data.sakhi_id,
        "public_key": public_key,
        "private_key_stored": stored,
    }


@router.post("/auth/token/create")
async def create_token(data: CreateTokenRequest) -> Dict[str, Any]:
    """Create a signed JWT for mesh communication."""
    token = await create_mesh_jwt_async(
        sakhi_id=data.sakhi_id,
        subject=data.subject,
        audience=data.audience,
        message_type=data.message_type,
        payload=data.payload,
    )

    return {
        "token": token,
        "sakhi_id": data.sakhi_id,
    }


@router.post("/auth/token/verify")
async def verify_token(data: VerifyTokenRequest) -> Dict[str, Any]:
    """Verify a mesh JWT token."""
    result = await verify_mesh_jwt_async(
        token=data.token,
        issuer_sakhi_id=data.issuer_sakhi_id,
        expected_audience=data.expected_audience,
    )

    return result.model_dump()


@router.get("/auth/trust/{from_sakhi_id}/{to_sakhi_id}")
async def check_trust(from_sakhi_id: str, to_sakhi_id: str) -> Dict[str, Any]:
    """Check if a sender is trusted by a receiver."""
    is_trusted, reason = await is_trusted_sender(from_sakhi_id, to_sakhi_id)

    return {
        "from_sakhi_id": from_sakhi_id,
        "to_sakhi_id": to_sakhi_id,
        "is_trusted": is_trusted,
        "reason": reason,
    }


@router.get("/auth/requirements/{to_sakhi_id}/{message_type}")
async def get_requirements(to_sakhi_id: str, message_type: str) -> Dict[str, Any]:
    """Get authentication requirements for sending to a Sakhi."""
    return await get_auth_requirements(to_sakhi_id, message_type)


# =============================================================================
# Async Handler Routes (A.6)
# =============================================================================

@router.get("/async/status/{message_id}")
async def get_async_message_status(message_id: str) -> Dict[str, Any]:
    """Get the delivery status of an async message."""
    status = await get_message_status(message_id)

    if not status:
        raise HTTPException(status_code=404, detail="Message not found")

    return status.model_dump()


@router.get("/async/pending")
async def get_all_pending(
    sakhi_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Get all pending messages ready for delivery."""
    pending = await get_pending_messages(to_sakhi_id=sakhi_id, limit=limit)

    return {
        "count": len(pending),
        "messages": [p.model_dump() for p in pending],
    }


@router.post("/async/process")
async def process_queue(
    batch_size: int = 20,
    max_age_hours: int = 48,
) -> Dict[str, Any]:
    """
    Process the message queue - attempt deliveries and expire old messages.

    This can be called as a background job or manually triggered.
    """
    stats = await process_message_queue(
        batch_size=batch_size,
        max_age_hours=max_age_hours,
    )

    return stats


@router.post("/async/deliver/{sakhi_id}")
async def trigger_delivery(sakhi_id: str) -> Dict[str, Any]:
    """
    Trigger delivery of all queued messages for a Sakhi that just came online.

    Called when heartbeat received or Sakhi explicitly comes online.
    """
    stats = await deliver_on_online(sakhi_id)

    return {
        "sakhi_id": sakhi_id,
        "stats": stats,
    }


@router.get("/async/thread/{message_id}")
async def get_thread(message_id: str) -> Dict[str, Any]:
    """Get the full conversation thread for a message."""
    thread = await get_conversation_thread(message_id)

    return {
        "original_message_id": thread.original_message_id,
        "status": thread.status,
        "message_count": len(thread.messages),
        "messages": [m.model_dump(mode="json") for m in thread.messages],
    }


@router.post("/async/cleanup")
async def cleanup_messages(days: int = 7) -> Dict[str, Any]:
    """
    Clean up old delivered/failed/expired messages.

    Should be run periodically as a maintenance job.
    """
    stats = await cleanup_old_messages(days=days)

    return {
        "cleaned_up": True,
        "stats": stats,
    }


__all__ = ["router"]
