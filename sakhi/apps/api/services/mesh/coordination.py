"""
Sakhi Coordination Service
--------------------------
The heart of Sakhi-to-Sakhi mesh.
Handles all coordination types between entities.

Coordination Types:
- scheduling: Find time to meet
- inquiry: Ask a question
- transaction: Buy/sell
- booking: Reserve something
- feedback: Review/rating
- request: General ask
"""

from __future__ import annotations

import logging
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.services.mesh.entities import get_entity_by_person, SakhiEntity
from sakhi.apps.api.services.mesh.connections import (
    are_connected,
    get_trust_level,
    TrustLevel,
)
from sakhi.apps.api.services.calendar.availability import (
    find_best_times,
    get_availability_windows,
)
# Optional: use new mesh availability module for better privacy control
try:
    from sakhi.apps.api.services.mesh.availability import (
        find_overlapping_times as mesh_find_overlapping,
        compute_shareable_availability,
    )
    HAS_MESH_AVAILABILITY = True
except ImportError:
    HAS_MESH_AVAILABILITY = False
from sakhi.apps.api.services.calendar.events import (
    create_event,
    CreateEventRequest,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class CoordinationType(str, Enum):
    """Types of coordination."""
    SCHEDULING = "scheduling"
    INQUIRY = "inquiry"
    TRANSACTION = "transaction"
    BOOKING = "booking"
    FEEDBACK = "feedback"
    REQUEST = "request"
    # Legacy aliases
    RESCHEDULING = "scheduling"
    AVAILABILITY_CHECK = "inquiry"
    NUDGE = "request"


class CoordinationStatus(str, Enum):
    """Status of a coordination thread."""
    OPEN = "open"
    PENDING_RESPONSE = "pending_response"
    NEGOTIATING = "negotiating"
    AGREED = "agreed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    # Legacy aliases
    PROPOSED = "pending_response"
    ACCEPTED = "agreed"
    DECLINED = "cancelled"


class MessageType(str, Enum):
    """Types of coordination messages."""
    # Universal
    INFO = "info"
    QUESTION = "question"
    ANSWER = "answer"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    # Scheduling
    PROPOSE_TIMES = "propose_times"
    ACCEPT_TIME = "accept_time"
    COUNTER_TIMES = "counter_times"
    # Transaction
    QUOTE = "quote"
    OFFER = "offer"
    COUNTER_OFFER = "counter_offer"
    ACCEPT = "accept"
    DECLINE = "decline"
    # Inquiry
    INQUIRY = "inquiry"
    RESPONSE = "response"
    FOLLOWUP = "followup"
    # Legacy aliases
    PROPOSAL = "propose_times"
    COUNTER_PROPOSAL = "counter_times"
    NUDGE = "info"


class CoordinationThread(BaseModel):
    """A coordination thread between two entities."""
    id: str
    initiator_entity_id: str
    recipient_entity_id: str
    coordination_type: CoordinationType
    subject: Optional[str] = None
    context: Dict[str, Any] = {}
    proposed_options: Optional[List[Dict[str, Any]]] = None
    status: CoordinationStatus
    outcome: Optional[Dict[str, Any]] = None
    related_event_id: Optional[str] = None
    related_transaction_id: Optional[str] = None
    relationship_context: Optional[Dict[str, Any]] = None
    priority: str = "normal"
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Backward compatibility
    @property
    def initiator_id(self) -> str:
        return self.initiator_entity_id

    @property
    def recipient_id(self) -> str:
        return self.recipient_entity_id

    @property
    def event_type(self) -> Optional[str]:
        return self.context.get("event_type")

    @property
    def timeframe(self) -> Optional[str]:
        return self.context.get("timeframe")

    @property
    def preferred_times(self) -> Optional[List[Dict[str, Any]]]:
        return self.proposed_options

    @property
    def duration_minutes(self) -> int:
        return self.context.get("duration", 60)

    @property
    def location_hint(self) -> Optional[str]:
        return self.context.get("location_hint")


class CoordinationMessage(BaseModel):
    """A message within a coordination thread."""
    id: str
    thread_id: str
    sender_entity_id: str
    sender_type: str  # 'sakhi', 'user', 'system'
    message_type: MessageType
    content: Dict[str, Any]
    requires_response: bool = False
    response_deadline: Optional[datetime] = None
    read_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Backward compatibility
    @property
    def sender_id(self) -> str:
        return self.sender_entity_id


class ProposalRequest(BaseModel):
    """Request to propose coordination to another entity."""
    recipient_id: str  # person_id for backward compatibility
    coordination_type: CoordinationType = CoordinationType.SCHEDULING
    event_type: Optional[str] = None
    timeframe: Optional[str] = None
    duration_minutes: int = 60
    location_hint: Optional[str] = None
    preferred_times: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    # New fields for other coordination types
    subject: Optional[str] = None
    question: Optional[str] = None  # For inquiries
    item: Optional[str] = None  # For transactions
    price: Optional[float] = None  # For transactions


class ProposalResponse(BaseModel):
    """Response to a proposal."""
    status: str
    thread_id: Optional[str] = None
    proposed_times: Optional[List[Dict[str, Any]]] = None
    message: str
    # New fields
    event_created: bool = False
    event_id: Optional[str] = None
    agreed_time: Optional[Dict[str, str]] = None


# =============================================================================
# Core Coordination Functions
# =============================================================================

async def initiate_coordination(
    initiator_id: str,  # person_id
    request: ProposalRequest,
) -> ProposalResponse:
    """
    Start coordination with another entity.

    1. Get entities for both parties
    2. Check if connected
    3. For scheduling: find overlapping times
    4. Create thread and send proposal
    """
    # Get initiator entity
    initiator_entity = await get_entity_by_person(initiator_id)
    if not initiator_entity:
        return ProposalResponse(
            status="error",
            message="You need to set up your Sakhi profile first.",
        )

    # Get recipient entity
    recipient_entity = await get_entity_by_person(request.recipient_id)
    if not recipient_entity:
        return ProposalResponse(
            status="no_sakhi",
            message="This person doesn't have Sakhi yet. You can still schedule manually.",
        )

    # Check connection
    connected = await are_connected(initiator_id, request.recipient_id)
    if not connected:
        return ProposalResponse(
            status="needs_connection",
            message="You're not connected with this person's Sakhi yet. Would you like to send a connection request?",
        )

    # Get trust level
    trust_level = await get_trust_level(initiator_id, request.recipient_id)

    # Build context based on coordination type
    context: Dict[str, Any] = {}
    proposed_options: List[Dict[str, Any]] = []

    if request.coordination_type == CoordinationType.SCHEDULING:
        context = {
            "event_type": request.event_type,
            "duration": request.duration_minutes,
            "timeframe": request.timeframe,
            "location_hint": request.location_hint,
        }

        # Get initiator's best times
        my_times = await find_best_times(
            person_id=initiator_id,
            event_type=request.event_type or "meeting",
            duration_minutes=request.duration_minutes,
            days_ahead=14 if request.timeframe == "next_week" else 7,
            max_suggestions=5,
        )

        # Find overlapping times
        if HAS_MESH_AVAILABILITY:
            now = datetime.utcnow()
            days_ahead = 14 if request.timeframe == "next_week" else 7
            proposed_options = await mesh_find_overlapping(
                person_a_id=initiator_id,
                person_b_id=request.recipient_id,
                start=now,
                end=now + timedelta(days=days_ahead),
                duration_minutes=request.duration_minutes,
            )
        else:
            their_availability = await get_shared_availability_legacy(
                person_id=request.recipient_id,
                requester_id=initiator_id,
                trust_level=trust_level,
                days_ahead=7,
            )
            proposed_options = find_overlapping_times_legacy(
                my_times=my_times,
                their_availability=their_availability,
                duration_minutes=request.duration_minutes,
            )

        if not proposed_options:
            return ProposalResponse(
                status="no_overlap",
                message="I couldn't find times that work for both of you this week. Would you like to try a different timeframe?",
            )

    elif request.coordination_type == CoordinationType.INQUIRY:
        context = {
            "question": request.question or request.message,
            "category": request.event_type,  # Reuse for category
            "urgency": "normal",
        }

    elif request.coordination_type == CoordinationType.TRANSACTION:
        context = {
            "item": request.item or request.subject,
            "price_asked": request.price,
            "quantity": 1,
        }

    # Get relationship context
    relationship_context = await get_relationship_context(initiator_id, request.recipient_id)

    # Create coordination thread
    thread_row = await dbfetch(
        """
        INSERT INTO coordination_threads (
            initiator_entity_id, recipient_entity_id, coordination_type,
            subject, context, proposed_options, status,
            relationship_context, expires_at
        )
        VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, 'pending_response', $7::jsonb, NOW() + INTERVAL '48 hours')
        RETURNING id, created_at
        """,
        initiator_entity.id,
        recipient_entity.id,
        request.coordination_type.value,
        request.subject or request.event_type or "Coordination",
        json.dumps(context),
        json.dumps([
            {
                "start": t["start"].isoformat() if hasattr(t["start"], "isoformat") else t["start"],
                "end": t["end"].isoformat() if hasattr(t["end"], "isoformat") else t["end"],
                "quality": t.get("quality"),
            }
            for t in proposed_options[:3]
        ]) if proposed_options else None,
        json.dumps(relationship_context),
        one=True,
    )

    thread_id = str(thread_row["id"])

    # Create proposal message
    message_type = MessageType.PROPOSE_TIMES if request.coordination_type == CoordinationType.SCHEDULING else MessageType.INQUIRY

    await dbexec(
        """
        INSERT INTO coordination_messages (
            thread_id, sender_entity_id, sender_type, message_type, content, requires_response
        )
        VALUES ($1, $2, 'sakhi', $3, $4::jsonb, TRUE)
        """,
        thread_id,
        initiator_entity.id,
        message_type.value,
        json.dumps({
            "text": request.message or f"Would love to coordinate!",
            "data": {
                "proposed_times": [
                    {
                        "start": t["start"].isoformat() if hasattr(t["start"], "isoformat") else t["start"],
                        "end": t["end"].isoformat() if hasattr(t["end"], "isoformat") else t["end"],
                        "quality": t.get("quality"),
                    }
                    for t in proposed_options[:3]
                ] if proposed_options else None,
                "context": context,
            },
        }),
    )

    LOGGER.info(
        "[coordination] Thread %s created: %s → %s type=%s",
        thread_id, initiator_entity.id, recipient_entity.id, request.coordination_type.value,
    )

    return ProposalResponse(
        status="proposed",
        thread_id=thread_id,
        proposed_times=[
            {
                "start": t["start"].isoformat() if hasattr(t["start"], "isoformat") else t["start"],
                "end": t["end"].isoformat() if hasattr(t["end"], "isoformat") else t["end"],
                "quality": t.get("quality"),
            }
            for t in proposed_options[:3]
        ] if proposed_options else None,
        message=f"I've sent a proposal to their Sakhi. They'll get back to us soon!",
    )


async def respond_to_proposal(
    responder_id: str,  # person_id
    thread_id: str,
    accept: bool,
    selected_time: Optional[Dict[str, str]] = None,
    counter_times: Optional[List[Dict[str, Any]]] = None,
    message: Optional[str] = None,
) -> Optional[ProposalResponse]:
    """
    Respond to a coordination proposal.

    accept=True + selected_time: Accept
    accept=False + counter_times: Counter-propose
    accept=False: Decline
    """
    # Get responder entity
    responder_entity = await get_entity_by_person(responder_id)
    if not responder_entity:
        return None

    # Get thread
    thread = await dbfetch(
        """
        SELECT * FROM coordination_threads
        WHERE id = $1 AND recipient_entity_id = $2 AND status = 'pending_response'
        """,
        thread_id,
        responder_entity.id,
        one=True,
    )

    if not thread:
        return ProposalResponse(
            status="error",
            message="Couldn't find that proposal. It may have expired.",
        )

    proposed_options = thread.get("proposed_options") or []
    if isinstance(proposed_options, str):
        proposed_options = json.loads(proposed_options)

    coordination_type = thread.get("coordination_type", "scheduling")

    if accept:
        # For scheduling: need selected time
        if coordination_type == "scheduling" and proposed_options:
            # Find selected time or use first option
            if selected_time:
                selected = selected_time
            elif proposed_options:
                selected = proposed_options[0]
            else:
                return ProposalResponse(
                    status="error",
                    message="No time selected.",
                )

            start_time = datetime.fromisoformat(str(selected["start"]).replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(str(selected["end"]).replace("Z", "+00:00"))

            # Update thread
            await dbexec(
                """
                UPDATE coordination_threads
                SET status = 'agreed',
                    outcome = $2::jsonb,
                    completed_at = NOW()
                WHERE id = $1
                """,
                thread_id,
                json.dumps({
                    "agreed_time": {"start": str(selected["start"]), "end": str(selected["end"])},
                }),
            )

            # Create accept message
            await dbexec(
                """
                INSERT INTO coordination_messages (
                    thread_id, sender_entity_id, sender_type, message_type, content
                )
                VALUES ($1, $2, 'sakhi', 'accept_time', $3::jsonb)
                """,
                thread_id,
                responder_entity.id,
                json.dumps({
                    "text": message or "That time works!",
                    "data": {"selected_time": selected},
                }),
            )

            # Create events for both parties
            context = thread.get("context") or {}
            if isinstance(context, str):
                context = json.loads(context)

            event_type = context.get("event_type", "meeting")

            # Get initiator display name
            initiator_name = await get_display_name_by_entity(str(thread["initiator_entity_id"]))

            # Create event for responder
            await create_event(
                person_id=responder_id,
                request=CreateEventRequest(
                    title=f"{event_type.title()} with {initiator_name}",
                    start_time=start_time,
                    end_time=end_time,
                    location=context.get("location_hint"),
                    event_type=event_type,
                    created_by="sakhi_coordination",
                    coordination_id=thread_id,
                ),
            )

            # Get initiator person_id
            initiator_row = await dbfetch(
                "SELECT person_id FROM sakhi_entities WHERE id = $1",
                thread["initiator_entity_id"],
                one=True,
            )
            initiator_person_id = initiator_row["person_id"] if initiator_row else None

            # Create event for initiator
            responder_name = await get_display_name_by_entity(responder_entity.id)
            if initiator_person_id:
                event = await create_event(
                    person_id=initiator_person_id,
                    request=CreateEventRequest(
                        title=f"{event_type.title()} with {responder_name}",
                        start_time=start_time,
                        end_time=end_time,
                        location=context.get("location_hint"),
                        event_type=event_type,
                        created_by="sakhi_coordination",
                        coordination_id=thread_id,
                    ),
                )

                # Update thread with event
                await dbexec(
                    "UPDATE coordination_threads SET related_event_id = $2, status = 'completed' WHERE id = $1",
                    thread_id,
                    event.id,
                )

            LOGGER.info("[coordination] Thread %s accepted: %s", thread_id, selected["start"])

            return ProposalResponse(
                status="accepted",
                thread_id=thread_id,
                message=f"Done! {event_type.title()} is scheduled for {start_time.strftime('%A, %B %d at %I:%M %p')}. Both calendars are updated.",
                event_created=True,
                event_id=str(event.id) if initiator_person_id else None,
                agreed_time={"start": str(selected["start"]), "end": str(selected["end"])},
            )

        else:
            # Non-scheduling accept
            await dbexec(
                """
                UPDATE coordination_threads
                SET status = 'agreed', completed_at = NOW()
                WHERE id = $1
                """,
                thread_id,
            )

            await dbexec(
                """
                INSERT INTO coordination_messages (
                    thread_id, sender_entity_id, sender_type, message_type, content
                )
                VALUES ($1, $2, 'sakhi', 'accept', $3::jsonb)
                """,
                thread_id,
                responder_entity.id,
                json.dumps({"text": message or "Agreed!"}),
            )

            return ProposalResponse(
                status="accepted",
                thread_id=thread_id,
                message="Agreement confirmed!",
            )

    elif counter_times:
        # Counter-propose
        await dbexec(
            """
            UPDATE coordination_threads
            SET proposed_options = $2::jsonb,
                status = 'negotiating'
            WHERE id = $1
            """,
            thread_id,
            json.dumps(counter_times),
        )

        await dbexec(
            """
            INSERT INTO coordination_messages (
                thread_id, sender_entity_id, sender_type, message_type, content, requires_response
            )
            VALUES ($1, $2, 'sakhi', 'counter_times', $3::jsonb, TRUE)
            """,
            thread_id,
            responder_entity.id,
            json.dumps({
                "text": message or "Those times don't work, but these do:",
                "data": {"proposed_times": counter_times},
            }),
        )

        # Swap roles for counter
        await dbexec(
            """
            UPDATE coordination_threads
            SET initiator_entity_id = recipient_entity_id,
                recipient_entity_id = initiator_entity_id,
                status = 'pending_response'
            WHERE id = $1
            """,
            thread_id,
        )

        return ProposalResponse(
            status="counter_proposed",
            thread_id=thread_id,
            proposed_times=counter_times,
            message="I've sent alternative times. Waiting for their response.",
        )

    else:
        # Decline
        await dbexec(
            "UPDATE coordination_threads SET status = 'cancelled' WHERE id = $1",
            thread_id,
        )

        await dbexec(
            """
            INSERT INTO coordination_messages (
                thread_id, sender_entity_id, sender_type, message_type, content
            )
            VALUES ($1, $2, 'sakhi', 'decline', $3::jsonb)
            """,
            thread_id,
            responder_entity.id,
            json.dumps({"text": message or "Can't make it work right now."}),
        )

        return ProposalResponse(
            status="declined",
            thread_id=thread_id,
            message="I've let them know. Maybe another time!",
        )


async def get_pending_proposals(person_id: str) -> List[CoordinationThread]:
    """Get all pending coordination proposals for a user."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return []

    rows = await dbfetch(
        """
        SELECT t.*, e.display_name as initiator_name
        FROM coordination_threads t
        LEFT JOIN sakhi_entities e ON e.id = t.initiator_entity_id
        WHERE t.recipient_entity_id = $1
          AND t.status = 'pending_response'
          AND (t.expires_at IS NULL OR t.expires_at > NOW())
        ORDER BY t.created_at DESC
        """,
        entity.id,
    )

    return [_row_to_thread(r) for r in (rows or [])]


async def get_active_threads(person_id: str) -> List[CoordinationThread]:
    """Get all active coordination threads for a user."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return []

    rows = await dbfetch(
        """
        SELECT * FROM coordination_threads
        WHERE (initiator_entity_id = $1 OR recipient_entity_id = $1)
          AND status IN ('open', 'pending_response', 'negotiating', 'agreed')
        ORDER BY created_at DESC
        """,
        entity.id,
    )

    return [_row_to_thread(r) for r in (rows or [])]


# =============================================================================
# Helper Functions
# =============================================================================

def _row_to_thread(row: Dict[str, Any]) -> CoordinationThread:
    """Convert database row to CoordinationThread."""
    context = row.get("context") or {}
    if isinstance(context, str):
        context = json.loads(context)

    proposed_options = row.get("proposed_options")
    if isinstance(proposed_options, str):
        proposed_options = json.loads(proposed_options)

    outcome = row.get("outcome")
    if isinstance(outcome, str):
        outcome = json.loads(outcome)

    relationship_context = row.get("relationship_context")
    if isinstance(relationship_context, str):
        relationship_context = json.loads(relationship_context)

    return CoordinationThread(
        id=str(row["id"]),
        initiator_entity_id=str(row["initiator_entity_id"]),
        recipient_entity_id=str(row["recipient_entity_id"]),
        coordination_type=CoordinationType(row["coordination_type"]),
        subject=row.get("subject"),
        context=context,
        proposed_options=proposed_options,
        status=CoordinationStatus(row["status"]),
        outcome=outcome,
        related_event_id=str(row["related_event_id"]) if row.get("related_event_id") else None,
        related_transaction_id=str(row["related_transaction_id"]) if row.get("related_transaction_id") else None,
        relationship_context=relationship_context,
        priority=row.get("priority", "normal"),
        expires_at=row.get("expires_at"),
        completed_at=row.get("completed_at"),
        created_at=row.get("created_at"),
    )


async def get_shared_availability_legacy(
    person_id: str,
    requester_id: str,
    trust_level: Optional[TrustLevel],
    days_ahead: int = 7,
) -> List[Dict[str, Any]]:
    """Get availability (legacy fallback)."""
    if not trust_level:
        return []

    windows = await get_availability_windows(
        person_id=person_id,
        days_ahead=days_ahead,
    )

    if trust_level == TrustLevel.MINIMAL:
        return [
            {"start": w["start"], "end": w["end"], "status": "free"}
            for w in windows
            if w.get("quality") in ["preferred", "available"]
        ]
    elif trust_level == TrustLevel.STANDARD:
        return [
            {"start": w["start"], "end": w["end"], "quality": w.get("quality")}
            for w in windows
        ]
    else:
        return windows


def find_overlapping_times_legacy(
    my_times: List[Dict[str, Any]],
    their_availability: List[Dict[str, Any]],
    duration_minutes: int,
) -> List[Dict[str, Any]]:
    """Find times that work for both parties (legacy fallback)."""
    overlaps = []

    for my_time in my_times:
        my_start = my_time["start"]
        my_end = my_time["end"]

        if isinstance(my_start, str):
            my_start = datetime.fromisoformat(my_start.replace("Z", "+00:00"))
        if isinstance(my_end, str):
            my_end = datetime.fromisoformat(my_end.replace("Z", "+00:00"))

        for their_time in their_availability:
            their_start = their_time["start"]
            their_end = their_time["end"]

            if isinstance(their_start, str):
                their_start = datetime.fromisoformat(their_start.replace("Z", "+00:00"))
            if isinstance(their_end, str):
                their_end = datetime.fromisoformat(their_end.replace("Z", "+00:00"))

            overlap_start = max(my_start, their_start)
            overlap_end = min(my_end, their_end)

            if (overlap_end - overlap_start).total_seconds() >= duration_minutes * 60:
                overlaps.append({
                    "start": overlap_start,
                    "end": overlap_start + timedelta(minutes=duration_minutes),
                    "quality": my_time.get("quality", "available"),
                })

    quality_order = {"preferred": 0, "available": 1, "suboptimal": 2}
    overlaps.sort(key=lambda x: quality_order.get(x.get("quality", "available"), 1))

    return overlaps[:5]


async def get_relationship_context(
    person_a: str,
    person_b: str,
) -> Dict[str, Any]:
    """Get relationship context for coordination."""
    row = await dbfetch(
        """
        SELECT
            r.name,
            r.relationship_type,
            r.last_seen_at,
            EXTRACT(DAY FROM (NOW() - COALESCE(r.last_seen_at, r.created_at)))::INTEGER as days_since,
            r.frequency_target,
            r.patterns->>'usual_activities' as usual_activities
        FROM relationships r
        WHERE r.person_id = $1
        LIMIT 1
        """,
        person_a,
        one=True,
    )

    if row:
        return {
            "name": row.get("name"),
            "relationship_type": row.get("relationship_type"),
            "last_seen": row.get("days_since"),
            "frequency_target": row.get("frequency_target"),
            "usual_activities": row.get("usual_activities"),
        }

    return {}


async def get_display_name_by_entity(entity_id: str) -> str:
    """Get display name for an entity."""
    row = await dbfetch(
        "SELECT display_name FROM sakhi_entities WHERE id = $1",
        entity_id,
        one=True,
    )
    return row["display_name"] if row else "Someone"


# Legacy alias
async def get_display_name(person_id: str) -> str:
    """Get display name for a person (legacy)."""
    entity = await get_entity_by_person(person_id)
    if entity:
        return entity.display_name
    return person_id


__all__ = [
    "CoordinationType",
    "CoordinationStatus",
    "MessageType",
    "CoordinationThread",
    "CoordinationMessage",
    "ProposalRequest",
    "ProposalResponse",
    "initiate_coordination",
    "respond_to_proposal",
    "get_pending_proposals",
    "get_active_threads",
]
