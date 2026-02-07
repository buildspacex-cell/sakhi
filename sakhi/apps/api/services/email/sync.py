"""
Email Sync Orchestration
------------------------
Manages the sync lifecycle for email accounts:
- Initial full sync (metadata only)
- Incremental sync via history API
- Error handling and retry logic
- State management
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.email.adapters.base import (
    BaseEmailAdapter,
    EmailAdapterError,
    PermissionRevokedError,
    QuotaExceededError,
    TokenExpiredError,
)
from sakhi.apps.api.services.email.adapters.gmail import GmailAdapter
import json as _json

from sakhi.apps.api.services.email.models import (
    EmailEvent,
    EmailProvider,
    SyncProgress,
    SyncState,
    SyncStatus,
)

LOGGER = logging.getLogger(__name__)

# Sync configuration
INITIAL_SYNC_DAYS = 365  # 1 year of history
BATCH_SIZE = 100
MAX_CONSECUTIVE_ERRORS = 5
ERROR_BACKOFF_SECONDS = [5, 15, 60, 300, 900]  # Exponential backoff


def _get_adapter(provider: EmailProvider, person_id: str) -> BaseEmailAdapter:
    """Get the appropriate adapter for a provider."""
    if provider == EmailProvider.GMAIL:
        return GmailAdapter(person_id)
    else:
        raise EmailAdapterError(f"Unsupported provider: {provider}")


# =============================================================================
# Sync State Management
# =============================================================================

async def get_sync_state(person_id: str) -> Optional[SyncState]:
    """Get current sync state for a user."""
    row = await dbfetch(
        """
        SELECT * FROM email_sync_state
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    if not row:
        return None

    return SyncState(
        person_id=str(row["person_id"]),
        provider=EmailProvider(row["provider"]),
        status=SyncStatus(row["status"]),
        connected_at=row.get("connected_at"),
        access_token_encrypted=row.get("access_token_encrypted"),
        refresh_token_encrypted=row.get("refresh_token_encrypted"),
        token_expires_at=row.get("token_expires_at"),
        last_sync_at=row.get("last_sync_at"),
        last_history_id=row.get("last_history_id"),
        messages_synced=row.get("messages_synced", 0),
        error_message=row.get("error_message"),
        error_at=row.get("error_at"),
        consecutive_errors=row.get("consecutive_errors", 0),
        paused_at=row.get("paused_at"),
        paused_by_user=row.get("paused_by_user", False),
    )


async def save_sync_state(state: SyncState) -> None:
    """Save sync state to database."""
    await dbexec(
        """
        INSERT INTO email_sync_state (
            person_id, provider, status, connected_at,
            access_token_encrypted, refresh_token_encrypted, token_expires_at,
            last_sync_at, last_history_id, messages_synced,
            error_message, error_at, consecutive_errors,
            paused_at, paused_by_user
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
        )
        ON CONFLICT (person_id, provider) DO UPDATE SET
            provider = EXCLUDED.provider,
            status = EXCLUDED.status,
            connected_at = EXCLUDED.connected_at,
            access_token_encrypted = EXCLUDED.access_token_encrypted,
            refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
            token_expires_at = EXCLUDED.token_expires_at,
            last_sync_at = EXCLUDED.last_sync_at,
            last_history_id = EXCLUDED.last_history_id,
            messages_synced = EXCLUDED.messages_synced,
            error_message = EXCLUDED.error_message,
            error_at = EXCLUDED.error_at,
            consecutive_errors = EXCLUDED.consecutive_errors,
            paused_at = EXCLUDED.paused_at,
            paused_by_user = EXCLUDED.paused_by_user,
            updated_at = NOW()
        """,
        state.person_id,
        state.provider if isinstance(state.provider, str) else state.provider.value,
        state.status if isinstance(state.status, str) else state.status.value,
        state.connected_at,
        state.access_token_encrypted,
        state.refresh_token_encrypted,
        state.token_expires_at,
        state.last_sync_at,
        state.last_history_id,
        state.messages_synced,
        state.error_message,
        state.error_at,
        state.consecutive_errors,
        state.paused_at,
        state.paused_by_user,
    )


async def update_sync_status(
    person_id: str,
    status: SyncStatus,
    error_message: Optional[str] = None,
) -> None:
    """Quick update of sync status."""
    if error_message:
        await dbexec(
            """
            UPDATE email_sync_state
            SET status = $2,
                error_message = $3,
                error_at = NOW(),
                consecutive_errors = consecutive_errors + 1,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            status.value,
            error_message,
        )
    else:
        await dbexec(
            """
            UPDATE email_sync_state
            SET status = $2,
                error_message = NULL,
                consecutive_errors = 0,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            status.value,
        )


# =============================================================================
# Token Management
# =============================================================================

async def _get_valid_token(
    person_id: str,
    state: SyncState,
    adapter: BaseEmailAdapter,
) -> str:
    """Get a valid access token, refreshing if needed."""
    from sakhi.libs.encryption import decrypt_value, encrypt_value

    # Decrypt current token
    if not state.access_token_encrypted:
        raise EmailAdapterError("No access token stored")

    access_token = decrypt_value(state.access_token_encrypted)

    # Check if expired
    if state.token_expires_at and datetime.now(timezone.utc) >= state.token_expires_at:
        LOGGER.info("[EmailSync] Token expired for %s, refreshing...", person_id)

        if not state.refresh_token_encrypted:
            raise TokenExpiredError("No refresh token available")

        refresh_token = decrypt_value(state.refresh_token_encrypted)

        try:
            new_access_token, new_expires_at = await adapter.refresh_token(refresh_token)

            # Save new token
            state.access_token_encrypted = encrypt_value(new_access_token)
            state.token_expires_at = new_expires_at
            await save_sync_state(state)

            access_token = new_access_token
            LOGGER.info("[EmailSync] Token refreshed for %s", person_id)

        except PermissionRevokedError:
            state.status = SyncStatus.REVOKED
            await save_sync_state(state)
            raise

    return access_token


# =============================================================================
# Event Storage
# =============================================================================

async def store_email_events(
    person_id: str,
    events: List[EmailEvent],
) -> int:
    """Store email events in database."""
    if not events:
        return 0

    # Batch insert
    stored = 0
    for event in events:
        try:
            await dbexec(
                """
                INSERT INTO email_events (
                    person_id, message_id, thread_id, provider,
                    provider_message_id, timestamp, direction,
                    sender_email, sender_name, sender_domain,
                    subject, has_attachments, attachment_count,
                    labels, is_read, is_starred, is_important,
                    is_newsletter, is_automated,
                    header_list_unsubscribe, header_auto_submitted,
                    header_precedence
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19,
                    $20, $21, $22
                )
                ON CONFLICT (person_id, message_id) DO NOTHING
                """,
                person_id,
                event.message_id,
                event.thread_id,
                event.provider if isinstance(event.provider, str) else event.provider.value,
                event.provider_message_id,
                event.timestamp,
                event.direction if isinstance(event.direction, str) else event.direction.value,
                event.sender.email,
                event.sender.name,
                event.sender.domain,
                event.subject[:500] if event.subject else "",
                event.has_attachments,
                event.attachment_count,
                _json.dumps(event.labels) if isinstance(event.labels, list) else event.labels,
                event.is_read,
                event.is_starred,
                event.is_important,
                event.is_newsletter,
                event.is_automated,
                event.headers.list_unsubscribe,
                event.headers.auto_submitted,
                event.headers.precedence,
            )
            stored += 1
        except Exception as e:
            LOGGER.warning("[EmailSync] Failed to store event %s: %s", event.message_id, e)

    return stored


async def get_stored_events(
    person_id: str,
    *,
    after: Optional[datetime] = None,
    limit: int = 1000,
) -> List[EmailEvent]:
    """Retrieve stored email events."""
    if after:
        rows = await dbfetch(
            """
            SELECT * FROM email_events
            WHERE person_id = $1 AND timestamp >= $2
            ORDER BY timestamp DESC
            LIMIT $3
            """,
            person_id,
            after,
            limit,
        )
    else:
        rows = await dbfetch(
            """
            SELECT * FROM email_events
            WHERE person_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )

    events = []
    for row in rows or []:
        from sakhi.apps.api.services.email.models import (
            EmailDirection,
            EmailHeaders,
            EmailSender,
        )

        events.append(EmailEvent(
            message_id=row["message_id"],
            thread_id=row["thread_id"],
            provider=EmailProvider(row["provider"]),
            provider_message_id=row["provider_message_id"],
            timestamp=row["timestamp"],
            direction=EmailDirection(row["direction"]),
            sender=EmailSender(
                email=row["sender_email"],
                name=row["sender_name"],
                domain=row["sender_domain"],
            ),
            recipients=[],  # Not stored for privacy
            subject=row["subject"],
            has_attachments=row["has_attachments"],
            attachment_count=row["attachment_count"],
            headers=EmailHeaders(
                list_unsubscribe=row.get("header_list_unsubscribe"),
                auto_submitted=row.get("header_auto_submitted"),
                precedence=row.get("header_precedence"),
            ),
            labels=_json.loads(row.get("labels")) if isinstance(row.get("labels"), str) else (row.get("labels") or []),
            is_read=row["is_read"],
            is_starred=row["is_starred"],
            is_important=row["is_important"],
            is_newsletter=row["is_newsletter"],
            is_automated=row["is_automated"],
        ))

    return events


# =============================================================================
# Sync Operations
# =============================================================================

async def start_email_sync(
    person_id: str,
    provider: EmailProvider = EmailProvider.GMAIL,
) -> SyncProgress:
    """
    Start or resume email sync for a user.

    This runs the initial sync or incremental sync based on state.
    """
    state = await get_sync_state(person_id)

    if not state:
        return SyncProgress(
            status=SyncStatus.NOT_CONNECTED,
            error="Email not connected. Please connect your email first.",
        )

    if state.status == SyncStatus.REVOKED:
        return SyncProgress(
            status=SyncStatus.REVOKED,
            error="Email access was revoked. Please reconnect.",
        )

    if state.paused_by_user:
        return SyncProgress(
            status=SyncStatus.PAUSED,
            messages_synced=state.messages_synced,
            current_phase="paused",
        )

    adapter = _get_adapter(state.provider, person_id)

    try:
        access_token = await _get_valid_token(person_id, state, adapter)

        # Determine sync type
        if state.last_history_id:
            # Incremental sync
            return await _run_incremental_sync(person_id, state, adapter, access_token)
        else:
            # Initial sync
            return await _run_initial_sync(person_id, state, adapter, access_token)

    except TokenExpiredError:
        await update_sync_status(person_id, SyncStatus.ERROR, "Token expired")
        return SyncProgress(
            status=SyncStatus.ERROR,
            error="Authentication expired. Please reconnect.",
        )

    except PermissionRevokedError:
        return SyncProgress(
            status=SyncStatus.REVOKED,
            error="Email access was revoked.",
        )

    except QuotaExceededError as e:
        await update_sync_status(person_id, SyncStatus.ERROR, "Rate limited")
        return SyncProgress(
            status=SyncStatus.ERROR,
            error=f"Rate limited. Retrying in {e.retry_after_seconds}s.",
        )

    except Exception as e:
        LOGGER.exception("[EmailSync] Sync failed for %s: %s", person_id, e)
        await update_sync_status(person_id, SyncStatus.ERROR, str(e))
        return SyncProgress(
            status=SyncStatus.ERROR,
            error=f"Sync failed: {e}",
        )


async def _run_initial_sync(
    person_id: str,
    state: SyncState,
    adapter: BaseEmailAdapter,
    access_token: str,
) -> SyncProgress:
    """Run initial full sync (metadata only)."""
    LOGGER.info("[EmailSync] Starting initial sync for %s", person_id)

    state.status = SyncStatus.INITIAL_SYNC
    await save_sync_state(state)

    # Get user email for direction detection
    user_email = await adapter.get_user_email(access_token)

    # Fetch messages from last N days
    cutoff = datetime.now(timezone.utc) - timedelta(days=INITIAL_SYNC_DAYS)
    total_synced = 0

    async for event in adapter.iter_all_messages(
        access_token,
        after=cutoff,
        batch_size=BATCH_SIZE,
    ):
        # Update direction
        if user_email.lower() in event.sender.email.lower():
            from sakhi.apps.api.services.email.models import EmailDirection
            event.direction = EmailDirection.OUTGOING

        # Store event
        await store_email_events(person_id, [event])
        total_synced += 1

        # Update progress periodically
        if total_synced % 100 == 0:
            state.messages_synced = total_synced
            await save_sync_state(state)
            LOGGER.debug("[EmailSync] Synced %d messages for %s", total_synced, person_id)

    # Get history ID for incremental sync
    # Fetch profile to get latest history ID
    data = await adapter._make_request(access_token, "GET", "/users/me/profile")
    history_id = data.get("historyId")

    # Mark complete
    state.status = SyncStatus.INCREMENTAL_SYNC
    state.last_sync_at = datetime.now(timezone.utc)
    state.last_history_id = history_id
    state.messages_synced = total_synced
    state.consecutive_errors = 0
    state.error_message = None
    await save_sync_state(state)

    LOGGER.info("[EmailSync] Initial sync complete for %s: %d messages", person_id, total_synced)

    return SyncProgress(
        status=SyncStatus.INCREMENTAL_SYNC,
        messages_synced=total_synced,
        current_phase="complete",
        last_sync_at=state.last_sync_at,
    )


async def _run_incremental_sync(
    person_id: str,
    state: SyncState,
    adapter: BaseEmailAdapter,
    access_token: str,
) -> SyncProgress:
    """Run incremental sync using history API."""
    LOGGER.info("[EmailSync] Starting incremental sync for %s", person_id)

    if not state.last_history_id:
        # Fall back to initial sync
        return await _run_initial_sync(person_id, state, adapter, access_token)

    user_email = await adapter.get_user_email(access_token)

    try:
        history, new_history_id = await adapter.get_history(
            access_token,
            state.last_history_id,
        )
    except EmailAdapterError as e:
        if "historyId" in str(e).lower():
            # History ID expired, need full sync
            LOGGER.warning("[EmailSync] History ID expired for %s, running full sync", person_id)
            state.last_history_id = None
            await save_sync_state(state)
            return await _run_initial_sync(person_id, state, adapter, access_token)
        raise

    # Process history
    new_message_ids = set()
    for record in history:
        for msg in record.get("messagesAdded", []):
            new_message_ids.add(msg.get("message", {}).get("id"))

    # Fetch new messages
    synced = 0
    if new_message_ids:
        events = await adapter.fetch_messages_batch(
            access_token,
            list(new_message_ids),
        )

        # Update directions
        for event in events:
            if user_email.lower() in event.sender.email.lower():
                from sakhi.apps.api.services.email.models import EmailDirection
                event.direction = EmailDirection.OUTGOING

        synced = await store_email_events(person_id, events)

    # Update state
    state.last_sync_at = datetime.now(timezone.utc)
    state.last_history_id = new_history_id
    state.messages_synced += synced
    state.consecutive_errors = 0
    await save_sync_state(state)

    LOGGER.info("[EmailSync] Incremental sync complete for %s: %d new messages", person_id, synced)

    return SyncProgress(
        status=SyncStatus.INCREMENTAL_SYNC,
        messages_synced=state.messages_synced,
        current_phase="incremental",
        last_sync_at=state.last_sync_at,
    )


# =============================================================================
# User Controls
# =============================================================================

async def get_sync_status(person_id: str) -> SyncProgress:
    """Get current sync status for a user."""
    state = await get_sync_state(person_id)

    if not state:
        return SyncProgress(
            status=SyncStatus.NOT_CONNECTED,
            current_phase="not_connected",
        )

    return SyncProgress(
        status=state.status,
        messages_synced=state.messages_synced,
        current_phase=state.status if isinstance(state.status, str) else state.status.value,
        last_sync_at=state.last_sync_at,
        error=state.error_message,
    )


async def pause_sync(person_id: str) -> bool:
    """Pause sync for a user."""
    state = await get_sync_state(person_id)
    if not state:
        return False

    state.status = SyncStatus.PAUSED
    state.paused_at = datetime.now(timezone.utc)
    state.paused_by_user = True
    await save_sync_state(state)

    LOGGER.info("[EmailSync] Sync paused for %s", person_id)
    return True


async def resume_sync(person_id: str) -> SyncProgress:
    """Resume paused sync for a user."""
    state = await get_sync_state(person_id)
    if not state:
        return SyncProgress(
            status=SyncStatus.NOT_CONNECTED,
            error="Email not connected",
        )

    state.paused_by_user = False
    state.paused_at = None
    await save_sync_state(state)

    LOGGER.info("[EmailSync] Sync resumed for %s", person_id)
    return await start_email_sync(person_id)


async def disconnect_email(person_id: str) -> bool:
    """Disconnect email and clean up."""
    state = await get_sync_state(person_id)
    if not state:
        return True

    # Revoke token if possible
    try:
        adapter = _get_adapter(state.provider, person_id)
        if state.access_token_encrypted:
            from sakhi.libs.encryption import decrypt_value
            token = decrypt_value(state.access_token_encrypted)
            await adapter.revoke_access(token)
    except Exception as e:
        LOGGER.warning("[EmailSync] Failed to revoke token: %s", e)

    # Delete sync state
    await dbexec(
        "DELETE FROM email_sync_state WHERE person_id = $1",
        person_id,
    )

    # Delete stored events
    await dbexec(
        "DELETE FROM email_events WHERE person_id = $1",
        person_id,
    )

    # Delete extracted signals
    await dbexec(
        "DELETE FROM email_signals WHERE person_id = $1",
        person_id,
    )

    LOGGER.info("[EmailSync] Email disconnected for %s", person_id)
    return True


__all__ = [
    "start_email_sync",
    "get_sync_status",
    "pause_sync",
    "resume_sync",
    "disconnect_email",
    "get_sync_state",
    "get_stored_events",
]
