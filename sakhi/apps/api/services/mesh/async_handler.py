"""
A.6 Async Response Handler
--------------------------
Handle delayed responses when Sakhi instances are offline.

Features:
1. Message queue with retry logic
2. Exponential backoff for retries
3. Response correlation (link responses to original requests)
4. Message expiration and cleanup
5. Online detection and delivery
"""

from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.services.mesh.inter_sakhi import (
    MeshMessage,
    MeshMessageType,
    MeshSendResult,
    lookup_sakhi_endpoint,
    mark_message_delivered,
)

LOGGER = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 5
BASE_RETRY_DELAY_SECONDS = 60  # 1 minute
MAX_RETRY_DELAY_SECONDS = 3600  # 1 hour
MESSAGE_EXPIRY_HOURS = 48
DEFAULT_TIMEOUT = 30.0


# =============================================================================
# Models
# =============================================================================

class QueuedMessage(BaseModel):
    """A message in the offline queue."""
    message_id: str
    from_sakhi_id: str
    to_sakhi_id: str
    message_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    reply_to: Optional[str] = None
    created_at: datetime
    last_attempt: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    attempts: int = 0
    max_retries: int = MAX_RETRIES
    status: str = "pending"  # pending, delivered, failed, expired


class MessageStatus(BaseModel):
    """Status of a queued message."""
    message_id: str
    status: str  # pending, delivered, failed, expired
    created_at: datetime
    delivered_at: Optional[datetime] = None
    attempts: int = 0
    next_retry_at: Optional[datetime] = None
    error: Optional[str] = None


class DeliveryResult(BaseModel):
    """Result of attempting message delivery."""
    message_id: str
    delivered: bool
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_scheduled: bool = False
    next_retry_at: Optional[datetime] = None


class ConversationThread(BaseModel):
    """A thread of related messages (request + responses)."""
    original_message_id: str
    messages: List[MeshMessage] = []
    status: str = "open"  # open, completed, expired


# =============================================================================
# Queue Management
# =============================================================================

async def queue_message_for_delivery(
    message: MeshMessage,
    max_retries: int = MAX_RETRIES,
) -> str:
    """
    Add a message to the delivery queue.

    Args:
        message: The message to queue
        max_retries: Maximum delivery attempts

    Returns:
        Message ID
    """
    next_retry = datetime.utcnow() + timedelta(seconds=BASE_RETRY_DELAY_SECONDS)

    await dbexec(
        """
        INSERT INTO mesh_message_queue (
            message_id, from_sakhi_id, to_sakhi_id, message_type,
            payload, reply_to, created_at, attempts, max_retries,
            next_retry_at, status
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), 0, $7, $8, 'pending')
        ON CONFLICT (message_id) DO UPDATE
        SET attempts = mesh_message_queue.attempts + 1,
            last_attempt = NOW(),
            next_retry_at = $8
        """,
        message.message_id,
        message.from_sakhi_id,
        message.to_sakhi_id,
        message.message_type.value,
        json.dumps(message.payload),
        message.reply_to,
        max_retries,
        next_retry,
    )

    LOGGER.info(
        "[async_handler] Queued message %s for %s (retry at %s)",
        message.message_id[:8], message.to_sakhi_id[:8], next_retry
    )

    return message.message_id


async def get_pending_messages(
    to_sakhi_id: Optional[str] = None,
    limit: int = 50,
) -> List[QueuedMessage]:
    """
    Get messages ready for delivery attempt.

    Args:
        to_sakhi_id: Optional filter by recipient
        limit: Max messages to return

    Returns:
        List of queued messages ready for retry
    """
    if to_sakhi_id:
        rows = await dbfetch(
            """
            SELECT message_id, from_sakhi_id, to_sakhi_id, message_type,
                   payload, reply_to, created_at, last_attempt, next_retry_at,
                   attempts, COALESCE(max_retries, $3) as max_retries, status
            FROM mesh_message_queue
            WHERE to_sakhi_id = $1
              AND status = 'pending'
              AND (next_retry_at IS NULL OR next_retry_at <= NOW())
            ORDER BY created_at ASC
            LIMIT $2
            """,
            to_sakhi_id,
            limit,
            MAX_RETRIES,
        )
    else:
        rows = await dbfetch(
            """
            SELECT message_id, from_sakhi_id, to_sakhi_id, message_type,
                   payload, reply_to, created_at, last_attempt, next_retry_at,
                   attempts, COALESCE(max_retries, $2) as max_retries, status
            FROM mesh_message_queue
            WHERE status = 'pending'
              AND (next_retry_at IS NULL OR next_retry_at <= NOW())
            ORDER BY created_at ASC
            LIMIT $1
            """,
            limit,
            MAX_RETRIES,
        )

    messages = []
    for row in rows or []:
        payload = row.get("payload")
        if isinstance(payload, str):
            payload = json.loads(payload)

        messages.append(QueuedMessage(
            message_id=row["message_id"],
            from_sakhi_id=row["from_sakhi_id"],
            to_sakhi_id=row["to_sakhi_id"],
            message_type=row["message_type"],
            payload=payload or {},
            reply_to=row.get("reply_to"),
            created_at=row["created_at"],
            last_attempt=row.get("last_attempt"),
            next_retry_at=row.get("next_retry_at"),
            attempts=row.get("attempts", 0),
            max_retries=row.get("max_retries", MAX_RETRIES),
            status=row.get("status", "pending"),
        ))

    return messages


async def get_message_status(message_id: str) -> Optional[MessageStatus]:
    """Get the current status of a queued message."""
    row = await dbfetch(
        """
        SELECT message_id, status, created_at, delivered_at, attempts,
               next_retry_at, error_message
        FROM mesh_message_queue
        WHERE message_id = $1
        """,
        message_id,
        one=True,
    )

    if not row:
        return None

    return MessageStatus(
        message_id=row["message_id"],
        status=row.get("status", "pending"),
        created_at=row["created_at"],
        delivered_at=row.get("delivered_at"),
        attempts=row.get("attempts", 0),
        next_retry_at=row.get("next_retry_at"),
        error=row.get("error_message"),
    )


# =============================================================================
# Delivery Logic
# =============================================================================

def _calculate_next_retry(attempts: int) -> datetime:
    """Calculate next retry time with exponential backoff."""
    delay = min(
        BASE_RETRY_DELAY_SECONDS * (2 ** attempts),
        MAX_RETRY_DELAY_SECONDS
    )
    return datetime.utcnow() + timedelta(seconds=delay)


async def attempt_delivery(queued: QueuedMessage) -> DeliveryResult:
    """
    Attempt to deliver a queued message.

    Args:
        queued: The queued message to deliver

    Returns:
        DeliveryResult with outcome
    """
    # Look up target endpoint
    target = await lookup_sakhi_endpoint(queued.to_sakhi_id)

    if not target:
        LOGGER.warning(
            "[async_handler] Target %s not found for %s",
            queued.to_sakhi_id[:8], queued.message_id[:8]
        )
        return await _handle_delivery_failure(
            queued, "Target Sakhi not found"
        )

    if not target.is_online:
        # Schedule retry
        next_retry = _calculate_next_retry(queued.attempts)
        await _schedule_retry(queued.message_id, next_retry)

        return DeliveryResult(
            message_id=queued.message_id,
            delivered=False,
            error="Target offline",
            retry_scheduled=True,
            next_retry_at=next_retry,
        )

    # Attempt delivery
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            message = MeshMessage(
                message_id=queued.message_id,
                from_sakhi_id=queued.from_sakhi_id,
                to_sakhi_id=queued.to_sakhi_id,
                message_type=MeshMessageType(queued.message_type),
                payload=queued.payload,
                reply_to=queued.reply_to,
                timestamp=queued.created_at,
            )

            response = await client.post(
                f"{target.endpoint_url}/receive",
                json=message.model_dump(mode="json"),
            )

            if response.status_code == 200:
                # Mark delivered
                await _mark_delivered(queued.message_id)
                data = response.json()

                LOGGER.info(
                    "[async_handler] Delivered %s to %s",
                    queued.message_id[:8], queued.to_sakhi_id[:8]
                )

                return DeliveryResult(
                    message_id=queued.message_id,
                    delivered=True,
                    response=data,
                )
            else:
                return await _handle_delivery_failure(
                    queued, f"HTTP {response.status_code}"
                )

    except httpx.RequestError as e:
        return await _handle_delivery_failure(queued, str(e))


async def _handle_delivery_failure(
    queued: QueuedMessage,
    error: str,
) -> DeliveryResult:
    """Handle a delivery failure - schedule retry or mark failed."""
    new_attempts = queued.attempts + 1

    if new_attempts >= queued.max_retries:
        # Max retries exceeded
        await _mark_failed(queued.message_id, error)
        return DeliveryResult(
            message_id=queued.message_id,
            delivered=False,
            error=f"Max retries exceeded: {error}",
            retry_scheduled=False,
        )

    # Schedule retry
    next_retry = _calculate_next_retry(new_attempts)
    await _schedule_retry(queued.message_id, next_retry, error)

    return DeliveryResult(
        message_id=queued.message_id,
        delivered=False,
        error=error,
        retry_scheduled=True,
        next_retry_at=next_retry,
    )


async def _mark_delivered(message_id: str) -> None:
    """Mark a message as successfully delivered."""
    await dbexec(
        """
        UPDATE mesh_message_queue
        SET status = 'delivered', delivered_at = NOW()
        WHERE message_id = $1
        """,
        message_id,
    )


async def _mark_failed(message_id: str, error: str) -> None:
    """Mark a message as permanently failed."""
    await dbexec(
        """
        UPDATE mesh_message_queue
        SET status = 'failed', error_message = $2
        WHERE message_id = $1
        """,
        message_id,
        error,
    )


async def _schedule_retry(
    message_id: str,
    next_retry: datetime,
    error: Optional[str] = None,
) -> None:
    """Schedule a retry for a message."""
    await dbexec(
        """
        UPDATE mesh_message_queue
        SET attempts = attempts + 1,
            last_attempt = NOW(),
            next_retry_at = $2,
            error_message = $3
        WHERE message_id = $1
        """,
        message_id,
        next_retry,
        error,
    )


# =============================================================================
# Batch Processing
# =============================================================================

async def process_message_queue(
    batch_size: int = 20,
    max_age_hours: int = MESSAGE_EXPIRY_HOURS,
) -> Dict[str, int]:
    """
    Process the message queue - attempt deliveries and expire old messages.

    This should be run as a background job (e.g., every 5 minutes).

    Args:
        batch_size: Number of messages to process per run
        max_age_hours: Expire messages older than this

    Returns:
        Stats: {delivered, failed, expired, pending}
    """
    stats = {"delivered": 0, "failed": 0, "expired": 0, "pending": 0}

    # Expire old messages
    expired = await _expire_old_messages(max_age_hours)
    stats["expired"] = expired

    # Get pending messages
    pending = await get_pending_messages(limit=batch_size)
    stats["pending"] = len(pending)

    # Attempt delivery for each
    for queued in pending:
        result = await attempt_delivery(queued)

        if result.delivered:
            stats["delivered"] += 1
        elif not result.retry_scheduled:
            stats["failed"] += 1

    LOGGER.info(
        "[async_handler] Queue processing: delivered=%d, failed=%d, expired=%d, pending=%d",
        stats["delivered"], stats["failed"], stats["expired"], stats["pending"]
    )

    return stats


async def _expire_old_messages(max_age_hours: int) -> int:
    """Expire messages older than max_age_hours."""
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

    result = await dbfetch(
        """
        UPDATE mesh_message_queue
        SET status = 'expired'
        WHERE status = 'pending'
          AND created_at < $1
        RETURNING message_id
        """,
        cutoff,
    )

    return len(result) if result else 0


# =============================================================================
# Response Correlation
# =============================================================================

async def correlate_response(
    original_message_id: str,
    response_message: MeshMessage,
) -> bool:
    """
    Link a response to its original request message.

    Args:
        original_message_id: The ID of the original request
        response_message: The response message

    Returns:
        True if correlation succeeded
    """
    try:
        await dbexec(
            """
            INSERT INTO mesh_response_correlation (
                request_message_id, response_message_id, correlated_at
            ) VALUES ($1, $2, NOW())
            ON CONFLICT (request_message_id, response_message_id) DO NOTHING
            """,
            original_message_id,
            response_message.message_id,
        )

        # Also update the original message with response reference
        await dbexec(
            """
            UPDATE mesh_message_queue
            SET response_received_at = NOW(),
                response_payload = $2
            WHERE message_id = $1
            """,
            original_message_id,
            json.dumps(response_message.payload),
        )

        LOGGER.info(
            "[async_handler] Correlated response %s to request %s",
            response_message.message_id[:8], original_message_id[:8]
        )
        return True

    except Exception as e:
        LOGGER.exception("[async_handler] Failed to correlate response: %s", e)
        return False


async def get_conversation_thread(message_id: str) -> ConversationThread:
    """
    Get all messages in a conversation thread.

    Follows reply_to chains to build full thread.

    Args:
        message_id: Any message ID in the thread

    Returns:
        ConversationThread with all related messages
    """
    messages = []
    seen_ids = set()

    # Find the root message
    root_id = await _find_root_message(message_id)

    # Get all messages in the thread
    async def collect_thread(msg_id: str):
        if msg_id in seen_ids:
            return
        seen_ids.add(msg_id)

        # Get this message
        row = await dbfetch(
            """
            SELECT message_id, from_sakhi_id, to_sakhi_id, message_type,
                   payload, reply_to, created_at
            FROM mesh_message_queue
            WHERE message_id = $1
            UNION
            SELECT message_id, from_sakhi_id, to_sakhi_id, message_type,
                   payload, reply_to, received_at as created_at
            FROM mesh_messages
            WHERE message_id = $1
            """,
            msg_id,
            one=True,
        )

        if row:
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

        # Get replies to this message
        replies = await dbfetch(
            """
            SELECT message_id FROM mesh_message_queue WHERE reply_to = $1
            UNION
            SELECT message_id FROM mesh_messages WHERE reply_to = $1
            """,
            msg_id,
        )

        for reply in replies or []:
            await collect_thread(reply["message_id"])

    await collect_thread(root_id)

    # Sort by timestamp
    messages.sort(key=lambda m: m.timestamp)

    return ConversationThread(
        original_message_id=root_id,
        messages=messages,
        status="completed" if len(messages) > 1 else "open",
    )


async def _find_root_message(message_id: str) -> str:
    """Find the root message ID by following reply_to chain."""
    current = message_id
    visited = set()

    while True:
        if current in visited:
            break
        visited.add(current)

        row = await dbfetch(
            """
            SELECT reply_to FROM mesh_message_queue WHERE message_id = $1
            UNION
            SELECT reply_to FROM mesh_messages WHERE message_id = $1
            """,
            current,
            one=True,
        )

        if not row or not row.get("reply_to"):
            break

        current = row["reply_to"]

    return current


# =============================================================================
# Online Detection & Delivery
# =============================================================================

async def deliver_on_online(sakhi_id: str) -> Dict[str, int]:
    """
    Attempt delivery of all queued messages when a Sakhi comes online.

    Called when heartbeat is received.

    Args:
        sakhi_id: The Sakhi that just came online

    Returns:
        Stats: {delivered, failed, pending}
    """
    stats = {"delivered": 0, "failed": 0, "pending": 0}

    # Get all pending messages for this Sakhi
    pending = await get_pending_messages(to_sakhi_id=sakhi_id, limit=100)
    stats["pending"] = len(pending)

    if not pending:
        return stats

    LOGGER.info(
        "[async_handler] %s online - attempting %d queued messages",
        sakhi_id[:8], len(pending)
    )

    for queued in pending:
        result = await attempt_delivery(queued)

        if result.delivered:
            stats["delivered"] += 1
        elif not result.retry_scheduled:
            stats["failed"] += 1

    return stats


async def notify_sender_delivered(
    message_id: str,
    response: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Notify the original sender that their message was delivered.

    Sends a delivery receipt back to the sender.

    Args:
        message_id: The delivered message ID
        response: Optional response data

    Returns:
        True if notification sent
    """
    # Get original message
    row = await dbfetch(
        "SELECT from_sakhi_id, to_sakhi_id FROM mesh_message_queue WHERE message_id = $1",
        message_id,
        one=True,
    )

    if not row:
        return False

    from sakhi.apps.api.services.mesh.inter_sakhi import send_mesh_message

    # Send ACK back to sender
    result = await send_mesh_message(
        from_sakhi_id=row["to_sakhi_id"],
        to_sakhi_id=row["from_sakhi_id"],
        message_type=MeshMessageType.ACK,
        payload={
            "original_message_id": message_id,
            "delivered_at": datetime.utcnow().isoformat(),
            "response": response,
        },
        reply_to=message_id,
    )

    return result.delivered


# =============================================================================
# Cleanup
# =============================================================================

async def cleanup_old_messages(days: int = 7) -> Dict[str, int]:
    """
    Clean up old delivered/failed/expired messages.

    Args:
        days: Delete messages older than this

    Returns:
        Stats: {deleted_queue, deleted_history}
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    stats = {"deleted_queue": 0, "deleted_history": 0}

    # Delete from queue
    result = await dbfetch(
        """
        DELETE FROM mesh_message_queue
        WHERE status IN ('delivered', 'failed', 'expired')
          AND created_at < $1
        RETURNING message_id
        """,
        cutoff,
    )
    stats["deleted_queue"] = len(result) if result else 0

    # Delete from history (keep longer)
    history_cutoff = datetime.utcnow() - timedelta(days=days * 2)
    result = await dbfetch(
        """
        DELETE FROM mesh_messages
        WHERE received_at < $1
        RETURNING message_id
        """,
        history_cutoff,
    )
    stats["deleted_history"] = len(result) if result else 0

    LOGGER.info(
        "[async_handler] Cleanup: deleted %d from queue, %d from history",
        stats["deleted_queue"], stats["deleted_history"]
    )

    return stats


__all__ = [
    "QueuedMessage",
    "MessageStatus",
    "DeliveryResult",
    "ConversationThread",
    "queue_message_for_delivery",
    "get_pending_messages",
    "get_message_status",
    "attempt_delivery",
    "process_message_queue",
    "correlate_response",
    "get_conversation_thread",
    "deliver_on_online",
    "notify_sender_delivered",
    "cleanup_old_messages",
]
