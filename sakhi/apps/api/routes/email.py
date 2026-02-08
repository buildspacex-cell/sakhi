"""
Email Intelligence API Routes
-----------------------------
REST API for email integration with Sakhi.

Endpoints:
- POST /email/connect/gmail - Start Gmail OAuth flow
- GET /email/connect/gmail/callback - OAuth callback
- GET /email/status - Get sync status
- POST /email/sync - Trigger sync
- GET /email/signals - Get extracted signals
- GET /email/signals/avoidance - Get avoidance patterns
- GET /email/signals/subscriptions - Get subscription list
- POST /email/disconnect - Disconnect email
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from sakhi.apps.api.services.email.adapters.gmail import GmailAdapter
from sakhi.apps.api.services.email.contact_preferences import (
    delete_preference,
    get_preferences,
    get_suggestions,
    upsert_preference,
)
from sakhi.apps.api.services.email.digest import (
    dismiss_action_item,
    fetch_email_detail,
    generate_digest,
    get_active_commitments,
    get_latest_digest,
    send_reply,
    update_commitment_status,
)
from sakhi.apps.api.services.email.integration import (
    extract_all_signals,
    get_email_context_for_conversation,
    get_stored_signals,
    get_surfaceable_insight,
)
from sakhi.apps.api.services.email.models import EmailProvider, SyncStatus
from sakhi.apps.api.services.email.sync import (
    disconnect_email,
    get_sync_state,
    get_sync_status,
    pause_sync,
    resume_sync,
    save_sync_state,
    start_email_sync,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ConnectRequest(BaseModel):
    """Request to start OAuth connection."""
    # Where to redirect user AFTER OAuth completes (web URL or deep link)
    # Examples:
    #   Web: "https://app.sakhi.com/settings/email?connected=true"
    #   Mobile: "sakhi://email/connected"
    app_redirect_uri: str


class ConnectResponse(BaseModel):
    """Response with OAuth URL."""
    auth_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    """OAuth callback parameters."""
    code: str
    state: str


class StatusResponse(BaseModel):
    """Sync status response."""
    connected: bool
    provider: Optional[str] = None
    status: str
    messages_synced: int = 0
    last_sync_at: Optional[str] = None
    error: Optional[str] = None


class SignalsResponse(BaseModel):
    """Extracted signals response."""
    status: str
    extracted_at: Optional[str] = None
    subscriptions: list = []
    avoidance: list = []
    boundary: Optional[dict] = None
    cognitive_load: Optional[dict] = None


class InsightResponse(BaseModel):
    """Surfaceable insight response."""
    has_insight: bool
    type: Optional[str] = None
    suggested_phrasing: Optional[str] = None
    data: Optional[dict] = None


# =============================================================================
# OAuth Endpoints
# =============================================================================

def _get_api_callback_url(request: Request) -> str:
    """Get the API callback URL for OAuth.

    This URL must be registered in Google Cloud Console.
    """
    # Use environment variable if set (for production)
    callback_url = os.environ.get("GMAIL_OAUTH_CALLBACK_URL")
    if callback_url:
        return callback_url

    # Build from request (for development)
    # request.base_url gives us the host
    return f"{request.base_url}email/connect/gmail/callback"


@router.post("/connect/gmail", response_model=ConnectResponse)
async def connect_gmail(
    request_obj: Request,
    body: ConnectRequest,
    person_id: str = Query(..., description="Person ID"),
):
    """
    Start Gmail OAuth flow.

    Returns an authorization URL to redirect the user to.
    The user should be redirected to auth_url.
    After OAuth completes, user will be redirected to app_redirect_uri.
    """
    # Generate state token for CSRF protection
    csrf_token = secrets.token_urlsafe(32)

    # Encode state with person_id and app redirect URI
    # This allows the callback to know where to redirect after processing
    state_data = {
        "csrf": csrf_token,
        "person_id": person_id,
        "app_redirect": body.app_redirect_uri,
    }
    state_encoded = base64.urlsafe_b64encode(
        json.dumps(state_data).encode()
    ).decode()

    # API callback URL (registered in Google Console)
    api_callback_url = _get_api_callback_url(request_obj)

    adapter = GmailAdapter(person_id)
    auth_url = adapter.get_auth_url(api_callback_url, state_encoded)

    LOGGER.info("[Email API] OAuth flow started for %s", person_id)

    return ConnectResponse(
        auth_url=auth_url,
        state=csrf_token,  # Return just the CSRF token for client-side validation if needed
    )


@router.get("/connect/gmail/callback")
async def gmail_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """
    Handle Gmail OAuth callback.

    Exchanges code for tokens, saves connection, and redirects to app.
    """
    from sakhi.apps.api.services.email.models import SyncState
    from sakhi.libs.encryption import encrypt_value

    # Decode state to get person_id and app redirect URI
    try:
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()))
        person_id = state_data["person_id"]
        app_redirect = state_data["app_redirect"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # The redirect_uri we used when generating the auth URL
    api_callback_url = _get_api_callback_url(request)

    adapter = GmailAdapter(person_id)

    try:
        # Exchange code for tokens
        access_token, refresh_token, expires_at = await adapter.exchange_code(
            code, api_callback_url
        )

        # Save sync state FIRST (before any API calls that might fail)
        state_obj = SyncState(
            person_id=person_id,
            provider=EmailProvider.GMAIL,
            status=SyncStatus.CONNECTING,
            connected_at=datetime.now(timezone.utc),
            access_token_encrypted=encrypt_value(access_token),
            refresh_token_encrypted=encrypt_value(refresh_token),
            token_expires_at=expires_at,
        )

        await save_sync_state(state_obj)
        LOGGER.info("[Email API] Sync state saved for %s", person_id)

        # Try to get user email (may fail if Gmail API not enabled)
        user_email = None
        try:
            user_email = await adapter.get_user_email(access_token)
            LOGGER.info("[Email API] Gmail connected for %s (%s)", person_id, user_email)
        except Exception as email_err:
            LOGGER.warning(
                "[Email API] Could not fetch user email for %s: %s. "
                "Tokens saved; sync will retry later.",
                person_id, email_err,
            )

        # Enqueue background sync
        try:
            from sakhi.apps.api.main import _enqueue_job
            _enqueue_job(
                request.app,
                "email_sync",
                "sakhi.apps.worker.tasks.email_sync_worker.run_email_sync",
                args=(person_id,),
                job_id=f"email_sync:{person_id}",
            )
            LOGGER.info("[Email API] Enqueued background sync for %s", person_id)
        except Exception as enqueue_err:
            LOGGER.warning("[Email API] Could not enqueue sync: %s", enqueue_err)

        # Redirect back to app with success
        redirect_params = urlencode({
            "status": "connected",
            **({"email": user_email} if user_email else {}),
        })
        redirect_url = f"{app_redirect}?{redirect_params}" if "?" not in app_redirect else f"{app_redirect}&{redirect_params}"

        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        LOGGER.exception("[Email API] OAuth callback failed: %s", e)

        # Redirect back to app with error
        redirect_params = urlencode({
            "status": "error",
            "error": str(e),
        })
        redirect_url = f"{app_redirect}?{redirect_params}" if "?" not in app_redirect else f"{app_redirect}&{redirect_params}"

        return RedirectResponse(url=redirect_url, status_code=302)


# =============================================================================
# Sync Endpoints
# =============================================================================

@router.get("/status", response_model=StatusResponse)
async def get_status(
    person_id: str = Query(..., description="Person ID"),
):
    """Get current email sync status."""
    state = await get_sync_state(person_id)

    if not state:
        return StatusResponse(
            connected=False,
            status="not_connected",
        )

    progress = await get_sync_status(person_id)

    return StatusResponse(
        connected=True,
        provider=state.provider if isinstance(state.provider, str) else state.provider.value,
        status=progress.status if isinstance(progress.status, str) else progress.status.value,
        messages_synced=progress.messages_synced,
        last_sync_at=progress.last_sync_at.isoformat() if progress.last_sync_at else None,
        error=progress.error,
    )


@router.post("/sync")
async def trigger_sync(
    request: Request,
    person_id: str = Query(..., description="Person ID"),
    background: bool = Query(False, description="Run in background"),
):
    """
    Trigger email sync.

    If background=true, starts sync in background and returns immediately.
    """
    state = await get_sync_state(person_id)

    if not state:
        raise HTTPException(status_code=400, detail="Email not connected")

    if background:
        # Enqueue via RQ worker for proper background processing
        from sakhi.apps.api.main import _enqueue_job
        _enqueue_job(
            request.app,
            "email_sync",
            "sakhi.apps.worker.tasks.email_sync_worker.run_email_sync",
            args=(person_id,),
            job_id=f"email_sync:{person_id}",
        )

        return {
            "status": "started",
            "message": "Sync started in background",
        }
    else:
        progress = await start_email_sync(person_id)

        return {
            "status": progress.status if isinstance(progress.status, str) else progress.status.value,
            "messages_synced": progress.messages_synced,
            "phase": progress.current_phase,
            "error": progress.error,
        }


@router.post("/sync/pause")
async def pause_email_sync(
    person_id: str = Query(..., description="Person ID"),
):
    """Pause email sync."""
    success = await pause_sync(person_id)

    if not success:
        raise HTTPException(status_code=400, detail="Email not connected")

    return {"status": "paused"}


@router.post("/sync/resume")
async def resume_email_sync(
    person_id: str = Query(..., description="Person ID"),
):
    """Resume paused email sync."""
    progress = await resume_sync(person_id)

    return {
        "status": progress.status if isinstance(progress.status, str) else progress.status.value,
        "message": "Sync resumed",
    }


# =============================================================================
# Signal Endpoints
# =============================================================================

@router.get("/signals", response_model=SignalsResponse)
async def get_signals(
    person_id: str = Query(..., description="Person ID"),
    refresh: bool = Query(False, description="Force refresh signals"),
):
    """
    Get extracted email signals.

    If refresh=true, re-extracts signals from stored events.
    """
    if refresh:
        result = await extract_all_signals(person_id, force_refresh=True)
    else:
        result = await get_stored_signals(person_id)

    return SignalsResponse(
        status=result.get("status", "unknown"),
        extracted_at=result.get("extracted_at"),
        subscriptions=result.get("subscriptions", []),
        avoidance=result.get("avoidance", []),
        boundary=result.get("boundary"),
        cognitive_load=result.get("cognitive_load"),
    )


@router.get("/signals/avoidance")
async def get_avoidance_signals(
    person_id: str = Query(..., description="Person ID"),
    min_days: int = Query(7, description="Minimum days without reply"),
):
    """Get email avoidance patterns."""
    signals = await get_stored_signals(person_id)

    avoidance = signals.get("avoidance", [])

    # Filter by minimum days
    filtered = [
        a for a in avoidance
        if a.get("duration_days", 0) >= min_days
    ]

    return {
        "count": len(filtered),
        "patterns": filtered,
    }


@router.get("/signals/subscriptions")
async def get_subscription_signals(
    person_id: str = Query(..., description="Person ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    marketing_only: bool = Query(False, description="Only marketing emails"),
):
    """Get detected subscriptions."""
    signals = await get_stored_signals(person_id)

    subscriptions = signals.get("subscriptions", [])

    # Apply filters
    if category:
        subscriptions = [s for s in subscriptions if s.get("category") == category]

    if marketing_only:
        subscriptions = [s for s in subscriptions if s.get("is_marketing")]

    return {
        "count": len(subscriptions),
        "subscriptions": subscriptions,
    }


@router.get("/signals/boundary")
async def get_boundary_signal(
    person_id: str = Query(..., description="Person ID"),
):
    """Get boundary erosion signal."""
    signals = await get_stored_signals(person_id)

    boundary = signals.get("boundary")

    if not boundary:
        return {"status": "no_data"}

    return {
        "erosion_score": boundary.get("erosion_score"),
        "after_hours_pct": boundary.get("after_hours_pct"),
        "weekend_pct": boundary.get("weekend_pct"),
        "trend": boundary.get("trend"),
        "friction_impact": boundary.get("friction_impact"),
    }


@router.get("/insight", response_model=InsightResponse)
async def get_insight(
    person_id: str = Query(..., description="Person ID"),
):
    """
    Get a surfaceable insight for conversation.

    Returns the most relevant insight to mention to the user.
    """
    insight = await get_surfaceable_insight(person_id)

    if not insight:
        return InsightResponse(has_insight=False)

    return InsightResponse(
        has_insight=True,
        type=insight.get("type"),
        suggested_phrasing=insight.get("suggested_phrasing"),
        data=insight.get("data"),
    )


@router.get("/context")
async def get_conversation_context(
    person_id: str = Query(..., description="Person ID"),
    include_details: bool = Query(False, description="Include specific details"),
):
    """
    Get email context for conversation engine.

    Returns a summary of email patterns for conversation context.
    """
    context = await get_email_context_for_conversation(
        person_id,
        include_details=include_details,
    )

    return {
        "has_context": context is not None,
        "context": context,
    }


# =============================================================================
# Digest Endpoints
# =============================================================================

@router.get("/digest")
async def get_digest(
    person_id: str = Query(..., description="Person ID"),
):
    """
    Get the latest email digest.

    Auto-generates a new digest if none exists or the latest is stale.
    """
    # Try to get existing digest
    digest = await get_latest_digest(person_id)

    if digest and digest.get("status") == "complete":
        return digest

    # No digest exists or not complete - generate one
    result = await generate_digest(person_id)
    return result


@router.post("/digest/generate")
async def trigger_digest_generation(
    request: Request,
    person_id: str = Query(..., description="Person ID"),
    background: bool = Query(False, description="Run in background"),
):
    """
    Force generate a new email digest.

    If background=true, enqueues via worker and returns immediately.
    """
    if background:
        from sakhi.apps.api.main import _enqueue_job
        _enqueue_job(
            request.app,
            "email_digest",
            "sakhi.apps.worker.tasks.email_digest_worker.run_digest_generation",
            args=(person_id,),
            kwargs={"force": True},
            job_id=f"email_digest:{person_id}",
        )
        return {"status": "started", "message": "Digest generation started in background"}
    else:
        result = await generate_digest(person_id, force=True)
        return result


# =============================================================================
# Commitment Endpoints
# =============================================================================

class CommitmentStatusUpdate(BaseModel):
    """Request to update commitment status."""
    status: str  # "done" or "dismissed"


@router.get("/commitments")
async def get_commitments(
    person_id: str = Query(..., description="Person ID"),
):
    """Get active email commitments (persisted across digest regenerations)."""
    commitments = await get_active_commitments(person_id)
    return {"commitments": commitments, "count": len(commitments)}


@router.patch("/commitments/{commitment_id}")
async def patch_commitment(
    commitment_id: str,
    body: CommitmentStatusUpdate,
    person_id: str = Query(..., description="Person ID"),
):
    """Mark a commitment as done or dismissed."""
    if body.status not in ("done", "dismissed"):
        raise HTTPException(status_code=400, detail="Status must be 'done' or 'dismissed'")

    success = await update_commitment_status(commitment_id, person_id, body.status)
    return {"updated": success, "status": body.status}


# =============================================================================
# Subscription Endpoints (memberships, renewals, billing)
# =============================================================================

@router.get("/subscriptions")
async def get_subscriptions(
    person_id: str = Query(..., description="Person ID"),
):
    """Get active subscription/renewal trackers (persisted across digest regenerations)."""
    subs = await get_active_commitments(person_id, commitment_type="subscription")
    return {"subscriptions": subs, "count": len(subs)}


@router.patch("/subscriptions/{subscription_id}")
async def patch_subscription(
    subscription_id: str,
    body: CommitmentStatusUpdate,
    person_id: str = Query(..., description="Person ID"),
):
    """Mark a subscription tracker as done (renewed) or dismissed."""
    if body.status not in ("done", "dismissed"):
        raise HTTPException(status_code=400, detail="Status must be 'done' or 'dismissed'")

    success = await update_commitment_status(subscription_id, person_id, body.status)
    return {"updated": success, "status": body.status}


# =============================================================================
# Action Item Dismiss Endpoints
# =============================================================================

class DismissActionRequest(BaseModel):
    """Request to dismiss an action item."""
    message_id: str


@router.post("/actions/dismiss")
async def dismiss_action(
    body: DismissActionRequest,
    person_id: str = Query(..., description="Person ID"),
):
    """Dismiss an action item so it won't appear in future digests."""
    success = await dismiss_action_item(person_id, body.message_id)
    return {"dismissed": success, "message_id": body.message_id}


# =============================================================================
# Contact Preferences
# =============================================================================


class PreferenceRequest(BaseModel):
    """Request to create or update a contact preference."""
    contact_identifier: str
    channel: str = "email"
    display_name: Optional[str] = None
    relationship: Optional[str] = None
    organization: Optional[str] = None
    priority: str = "normal"
    notes: Optional[str] = None
    learned_from: Optional[str] = "user_set"
    confidence: Optional[float] = 1.0


@router.get("/preferences")
async def list_preferences(
    person_id: str = Query(..., description="Person ID"),
):
    """List all contact preferences for the user, sorted by priority."""
    prefs = await get_preferences(person_id)
    return {"preferences": prefs}


@router.put("/preferences")
async def set_preference(
    body: PreferenceRequest,
    person_id: str = Query(..., description="Person ID"),
):
    """
    Create or update a contact preference.

    Upserts on (person_id, contact_identifier, channel).
    """
    if not body.contact_identifier.strip():
        raise HTTPException(status_code=400, detail="contact_identifier is required")

    valid_priorities = {"critical", "high", "normal", "low", "muted"}
    if body.priority not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"priority must be one of: {', '.join(sorted(valid_priorities))}",
        )

    result = await upsert_preference(person_id, body.model_dump())
    return result


@router.delete("/preferences/{preference_id}")
async def remove_preference(
    preference_id: str,
    person_id: str = Query(..., description="Person ID"),
):
    """Delete a contact preference."""
    deleted = await delete_preference(preference_id, person_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preference not found")
    return {"deleted": True}


@router.get("/preferences/suggestions")
async def get_preference_suggestions(
    person_id: str = Query(..., description="Person ID"),
):
    """
    Get Sakhi's suggestions for contact priorities based on dismiss patterns.

    Suggests muting senders whose emails the user has dismissed 3+ times.
    """
    suggestions = await get_suggestions(person_id)
    return {"suggestions": suggestions}


# =============================================================================
# Single Email Peek Endpoint
# =============================================================================

@router.get("/message/{message_id}")
async def get_email_message(
    message_id: str,
    person_id: str = Query(..., description="Person ID"),
):
    """
    Fetch a single email's metadata + body for the peek/context view.

    Body is fetched transiently from Gmail and never stored.
    Returns sender, subject, cleaned body, and Gmail URL for "open in Gmail".
    """
    detail = await fetch_email_detail(person_id, message_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Email not found")
    return detail


class ReplyRequest(BaseModel):
    """Request to send a reply via Sakhi."""
    body: str


@router.post("/message/{message_id}/reply")
async def send_email_reply(
    message_id: str,
    req: ReplyRequest,
    person_id: str = Query(..., description="Person ID"),
):
    """
    Send a reply to an email via Gmail API.

    The reply is threaded properly in Gmail. This is an explicit user action —
    Sakhi never sends emails without user confirmation.
    """
    if not req.body.strip():
        raise HTTPException(status_code=400, detail="Reply body cannot be empty")

    result = await send_reply(person_id, message_id, req.body)

    if not result.get("sent"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error", "Failed to send reply"),
        )

    return result


# =============================================================================
# Management Endpoints
# =============================================================================

@router.post("/disconnect")
async def disconnect(
    person_id: str = Query(..., description="Person ID"),
):
    """
    Disconnect email and delete all data.

    This revokes OAuth access and deletes all stored email data.
    """
    success = await disconnect_email(person_id)

    if success:
        LOGGER.info("[Email API] Email disconnected for %s", person_id)
        return {"status": "disconnected"}
    else:
        return {"status": "not_connected"}


# =============================================================================
# Debug Endpoints (Lab Only)
# =============================================================================

@router.get("/debug/events")
async def debug_events(
    person_id: str = Query(..., description="Person ID"),
    limit: int = Query(50, description="Max events to return"),
):
    """
    [DEBUG] Get raw stored email events.

    Only for development/debugging.
    """
    from sakhi.apps.api.services.email.sync import get_stored_events

    events = await get_stored_events(person_id, limit=limit)

    return {
        "count": len(events),
        "events": [
            {
                "message_id": e.message_id,
                "timestamp": e.timestamp.isoformat(),
                "direction": e.direction if isinstance(e.direction, str) else e.direction.value,
                "sender": e.sender.email,
                "subject": e.subject[:100] if e.subject else "",
                "is_newsletter": e.is_newsletter,
                "is_automated": e.is_automated,
            }
            for e in events
        ],
    }


__all__ = ["router"]
