"""
Gmail Adapter
-------------
Gmail-specific implementation of the email adapter interface.

Uses Gmail API with read + send scopes:
  https://www.googleapis.com/auth/gmail.readonly
  https://www.googleapis.com/auth/gmail.send

Key endpoints:
- /gmail/v1/users/me/messages - List message IDs
- /gmail/v1/users/me/messages/{id}?format=metadata - Get headers
- /gmail/v1/users/me/messages/send - Send a message
- /gmail/v1/users/me/history - Incremental sync
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, parseaddr, parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx

from sakhi.apps.api.services.email.adapters.base import (
    BaseEmailAdapter,
    EmailAdapterError,
    PermissionRevokedError,
    QuotaExceededError,
    TokenExpiredError,
    TokenRefreshError,
)
from sakhi.apps.api.services.email.models import (
    EmailDirection,
    EmailEvent,
    EmailHeaders,
    EmailProvider,
    EmailSender,
    EmailThread,
    SyncState,
)

LOGGER = logging.getLogger(__name__)

# Gmail API configuration
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
GOOGLE_OAUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Read + send scopes (no modify/delete)
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Rate limiting
MAX_BATCH_SIZE = 100
REQUESTS_PER_SECOND = 10
BATCH_DELAY_MS = 100


def _get_gmail_credentials() -> Tuple[str, str]:
    """Get Gmail OAuth credentials from environment."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise EmailAdapterError(
            "Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET environment variables"
        )

    return client_id, client_secret


class GmailAdapter(BaseEmailAdapter):
    """
    Gmail-specific adapter implementation.

    Handles:
    - OAuth 2.0 flow with Google
    - Message metadata fetching (headers only)
    - Incremental sync via History API
    - Batch requests for efficiency
    """

    provider = EmailProvider.GMAIL

    def __init__(
        self,
        person_id: str,
        sync_state: Optional[SyncState] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(person_id, sync_state)
        self._client = http_client
        self._user_email: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _make_request(
        self,
        access_token: str,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Gmail API."""
        client = await self._get_client()
        url = f"{GMAIL_API_BASE}{endpoint}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            if method == "GET":
                response = await client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await client.post(url, params=params, json=json_body, headers=headers)
            else:
                raise EmailAdapterError(f"Unsupported method: {method}")

            if response.status_code == 401:
                raise TokenExpiredError("Gmail access token expired")

            if response.status_code == 403:
                error_data = response.json()
                error_str = str(error_data)
                LOGGER.warning("[Gmail] 403 response: %s", error_str[:500])
                if "accessNotConfigured" in error_str:
                    raise PermissionRevokedError(
                        "Gmail API not enabled. Enable it at "
                        "https://console.cloud.google.com/apis/library/gmail.googleapis.com"
                    )
                if "insufficientPermissions" in error_str:
                    raise PermissionRevokedError("Gmail API insufficient permissions")
                raise QuotaExceededError("Gmail API quota exceeded")

            if response.status_code == 429:
                error = QuotaExceededError("Gmail rate limit exceeded")
                error.retry_after_seconds = int(response.headers.get("Retry-After", 60))
                raise error

            if response.status_code >= 400:
                LOGGER.error("[Gmail] API error: %s %s", response.status_code, response.text[:500])
                raise EmailAdapterError(f"Gmail API error: {response.status_code}")

            return response.json()

        except httpx.RequestError as e:
            LOGGER.error("[Gmail] Request failed: %s", e)
            raise EmailAdapterError(f"Gmail request failed: {e}")

    # =========================================================================
    # OAuth Methods
    # =========================================================================

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Generate Gmail OAuth authorization URL."""
        client_id, _ = _get_gmail_credentials()

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Always show consent screen
            "state": state,
        }

        return f"{GOOGLE_OAUTH_BASE}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Tuple[str, str, datetime]:
        """Exchange authorization code for tokens."""
        client_id, client_secret = _get_gmail_credentials()
        client = await self._get_client()

        try:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                LOGGER.error("[Gmail] Token exchange failed: %s", response.text)
                raise EmailAdapterError(f"Token exchange failed: {response.status_code}")

            data = response.json()
            access_token = data["access_token"]
            refresh_token = data.get("refresh_token", "")
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            return access_token, refresh_token, expires_at

        except httpx.RequestError as e:
            raise EmailAdapterError(f"Token exchange request failed: {e}")

    async def refresh_token(self, refresh_token: str) -> Tuple[str, datetime]:
        """Refresh an expired access token."""
        client_id, client_secret = _get_gmail_credentials()
        client = await self._get_client()

        try:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code == 400:
                error_data = response.json()
                if error_data.get("error") == "invalid_grant":
                    raise PermissionRevokedError("Gmail refresh token revoked")
                raise TokenRefreshError(f"Token refresh failed: {error_data}")

            if response.status_code != 200:
                raise TokenRefreshError(f"Token refresh failed: {response.status_code}")

            data = response.json()
            access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            return access_token, expires_at

        except httpx.RequestError as e:
            raise TokenRefreshError(f"Token refresh request failed: {e}")

    async def revoke_access(self, access_token: str) -> bool:
        """Revoke OAuth access."""
        client = await self._get_client()

        try:
            response = await client.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": access_token},
            )
            return response.status_code == 200

        except httpx.RequestError:
            return False

    # =========================================================================
    # Sync Methods
    # =========================================================================

    async def get_message_ids(
        self,
        access_token: str,
        *,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        max_results: int = 100,
        page_token: Optional[str] = None,
    ) -> Tuple[List[str], Optional[str]]:
        """Get message IDs with optional date filtering."""
        params: Dict[str, Any] = {
            "maxResults": min(max_results, 500),
        }

        if page_token:
            params["pageToken"] = page_token

        # Build query for date filtering
        query_parts = []
        if after:
            # Gmail uses epoch seconds
            query_parts.append(f"after:{int(after.timestamp())}")
        if before:
            query_parts.append(f"before:{int(before.timestamp())}")

        if query_parts:
            params["q"] = " ".join(query_parts)

        data = await self._make_request(
            access_token,
            "GET",
            "/users/me/messages",
            params=params,
        )

        message_ids = [msg["id"] for msg in data.get("messages", [])]
        next_page_token = data.get("nextPageToken")

        LOGGER.debug("[Gmail] Got %d message IDs, next_page=%s", len(message_ids), bool(next_page_token))

        return message_ids, next_page_token

    async def get_history(
        self,
        access_token: str,
        start_history_id: str,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Get changes since last sync (incremental)."""
        params = {
            "startHistoryId": start_history_id,
            "historyTypes": ["messageAdded", "messageDeleted", "labelAdded", "labelRemoved"],
        }

        try:
            data = await self._make_request(
                access_token,
                "GET",
                "/users/me/history",
                params=params,
            )

            history = data.get("history", [])
            new_history_id = data.get("historyId", start_history_id)

            LOGGER.debug("[Gmail] Got %d history records, new_id=%s", len(history), new_history_id)

            return history, new_history_id

        except EmailAdapterError as e:
            # History ID might be too old, need full sync
            if "historyId" in str(e).lower():
                LOGGER.warning("[Gmail] History ID expired, need full sync")
                return [], start_history_id
            raise

    async def fetch_message_metadata(
        self,
        access_token: str,
        message_id: str,
    ) -> EmailEvent:
        """Fetch metadata for a single message."""
        data = await self._make_request(
            access_token,
            "GET",
            f"/users/me/messages/{message_id}",
            params={"format": "metadata", "metadataHeaders": self._get_metadata_headers()},
        )

        return self._parse_message(data)

    async def fetch_messages_batch(
        self,
        access_token: str,
        message_ids: List[str],
    ) -> List[EmailEvent]:
        """Fetch metadata for multiple messages using batch requests."""
        if not message_ids:
            return []

        events = []

        # Process in batches
        for i in range(0, len(message_ids), MAX_BATCH_SIZE):
            batch_ids = message_ids[i:i + MAX_BATCH_SIZE]

            # Fetch concurrently within batch
            tasks = [
                self.fetch_message_metadata(access_token, msg_id)
                for msg_id in batch_ids
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, EmailEvent):
                    events.append(result)
                elif isinstance(result, Exception):
                    LOGGER.warning("[Gmail] Failed to fetch message: %s", result)

            # Rate limiting between batches
            if i + MAX_BATCH_SIZE < len(message_ids):
                await asyncio.sleep(BATCH_DELAY_MS / 1000)

        return events

    async def fetch_message_body(
        self,
        access_token: str,
        message_id: str,
    ) -> str:
        """
        Fetch full message body (ONLY when explicitly requested by user).

        This should NEVER be called during background sync.
        """
        data = await self._make_request(
            access_token,
            "GET",
            f"/users/me/messages/{message_id}",
            params={"format": "full"},
        )

        return self._extract_body(data)

    # =========================================================================
    # Send Methods
    # =========================================================================

    async def send_reply(
        self,
        access_token: str,
        original_message_id: str,
        reply_body: str,
    ) -> Dict[str, Any]:
        """
        Send a reply to an existing email.

        Fetches the original message headers (Message-ID, References, Subject,
        From) to construct a properly threaded reply, then sends via Gmail API.

        Returns the sent message metadata from Gmail.
        """
        # Fetch original message headers for threading
        original = await self._make_request(
            access_token,
            "GET",
            f"/users/me/messages/{original_message_id}",
            params={"format": "metadata", "metadataHeaders": self._get_metadata_headers()},
        )

        headers_list = original.get("payload", {}).get("headers", [])
        headers_dict = {h["name"].lower(): h["value"] for h in headers_list}
        thread_id = original.get("threadId", "")

        # Determine reply-to address
        original_from = headers_dict.get("from", "")
        _, reply_to_email = parseaddr(original_from)

        # Get user's own email
        user_email = await self.get_user_email(access_token)

        # Build threading headers
        original_msg_id_header = headers_dict.get("message-id", "")
        original_references = headers_dict.get("references", "")
        references = f"{original_references} {original_msg_id_header}".strip()

        # Build subject with Re: prefix
        original_subject = headers_dict.get("subject", "")
        reply_subject = original_subject
        if not original_subject.lower().startswith("re:"):
            reply_subject = f"Re: {original_subject}"

        # Construct MIME message
        msg = MIMEText(reply_body, "plain", "utf-8")
        msg["From"] = user_email
        msg["To"] = reply_to_email
        msg["Subject"] = reply_subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = f"<sakhi-{uuid.uuid4().hex[:12]}@sakhi.app>"

        if original_msg_id_header:
            msg["In-Reply-To"] = original_msg_id_header
        if references:
            msg["References"] = references

        # Encode as base64url for Gmail API
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

        # Send via Gmail API
        send_body: Dict[str, Any] = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        result = await self._make_request(
            access_token,
            "POST",
            "/users/me/messages/send",
            json_body=send_body,
        )

        LOGGER.info(
            "[Gmail] Reply sent to %s (thread=%s, msg=%s)",
            reply_to_email, thread_id, result.get("id", ""),
        )

        return result

    # =========================================================================
    # Thread Methods
    # =========================================================================

    async def fetch_thread(
        self,
        access_token: str,
        thread_id: str,
    ) -> EmailThread:
        """Fetch and reconstruct a thread."""
        data = await self._make_request(
            access_token,
            "GET",
            f"/users/me/threads/{thread_id}",
            params={"format": "metadata", "metadataHeaders": self._get_metadata_headers()},
        )

        messages = data.get("messages", [])
        if not messages:
            raise EmailAdapterError(f"Thread {thread_id} has no messages")

        # Parse all messages
        events = [self._parse_message(msg) for msg in messages]

        # Build thread analytics
        user_email = await self.get_user_email(access_token)

        return self._build_thread(thread_id, events, user_email)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def get_user_email(self, access_token: str) -> str:
        """Get the authenticated user's email address."""
        if self._user_email:
            return self._user_email

        data = await self._make_request(
            access_token,
            "GET",
            "/users/me/profile",
        )

        self._user_email = data.get("emailAddress", "")
        return self._user_email

    def _get_metadata_headers(self) -> List[str]:
        """Headers to request for metadata extraction."""
        return [
            "From",
            "To",
            "Cc",
            "Subject",
            "Date",
            "Message-ID",
            "In-Reply-To",
            "References",
            "List-Unsubscribe",
            "Auto-Submitted",
            "Precedence",
            "Content-Type",
        ]

    def _parse_message(self, data: Dict[str, Any]) -> EmailEvent:
        """Parse Gmail message data into normalized EmailEvent."""
        message_id = data.get("id", "")
        thread_id = data.get("threadId", "")

        # Extract headers
        headers_list = data.get("payload", {}).get("headers", [])
        headers_dict = {h["name"].lower(): h["value"] for h in headers_list}

        # Parse sender
        from_header = headers_dict.get("from", "")
        sender_name, sender_email = parseaddr(from_header)
        sender = EmailSender(email=sender_email or from_header, name=sender_name or None)

        # Parse recipients
        recipients = self._parse_recipients(headers_dict.get("to", ""))
        cc = self._parse_recipients(headers_dict.get("cc", ""))

        # Parse timestamp
        timestamp = self._parse_timestamp(data, headers_dict)

        # Determine direction (requires user email)
        # Will be updated later when we know user email
        direction = EmailDirection.INCOMING

        # Extract labels
        labels = data.get("labelIds", [])

        # Parse headers for signals
        email_headers = EmailHeaders(
            list_unsubscribe=headers_dict.get("list-unsubscribe"),
            auto_submitted=headers_dict.get("auto-submitted"),
            precedence=headers_dict.get("precedence"),
            in_reply_to=headers_dict.get("in-reply-to"),
            references=headers_dict.get("references"),
            content_type=headers_dict.get("content-type"),
        )

        # Detect automated/newsletter
        is_automated = bool(
            headers_dict.get("auto-submitted")
            or headers_dict.get("precedence") in ("bulk", "list", "junk")
        )
        is_newsletter = bool(headers_dict.get("list-unsubscribe"))

        # Check for attachments
        payload = data.get("payload", {})
        parts = payload.get("parts", [])
        attachment_count = sum(
            1 for p in parts
            if p.get("filename") and p.get("body", {}).get("attachmentId")
        )

        return EmailEvent(
            message_id=f"gmail:{message_id}",
            thread_id=f"gmail:{thread_id}",
            provider=EmailProvider.GMAIL,
            provider_message_id=message_id,
            timestamp=timestamp,
            direction=direction,
            sender=sender,
            recipients=recipients,
            cc=cc,
            subject=headers_dict.get("subject", ""),
            has_attachments=attachment_count > 0,
            attachment_count=attachment_count,
            headers=email_headers,
            labels=labels,
            is_read="UNREAD" not in labels,
            is_starred="STARRED" in labels,
            is_important="IMPORTANT" in labels,
            is_newsletter=is_newsletter,
            is_automated=is_automated,
        )

    def _parse_recipients(self, header: str) -> List[EmailSender]:
        """Parse To/Cc header into list of EmailSenders."""
        if not header:
            return []

        recipients = []
        # Simple split on comma (handles most cases)
        for part in header.split(","):
            name, email = parseaddr(part.strip())
            if email:
                recipients.append(EmailSender(email=email, name=name or None))

        return recipients

    def _parse_timestamp(
        self,
        data: Dict[str, Any],
        headers_dict: Dict[str, str],
    ) -> datetime:
        """Parse message timestamp."""
        # Try internalDate first (epoch ms)
        internal_date = data.get("internalDate")
        if internal_date:
            return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)

        # Fall back to Date header
        date_header = headers_dict.get("date")
        if date_header:
            try:
                return parsedate_to_datetime(date_header)
            except (ValueError, TypeError):
                pass

        # Default to now
        return datetime.now(timezone.utc)

    def _build_thread(
        self,
        thread_id: str,
        events: List[EmailEvent],
        user_email: str,
    ) -> EmailThread:
        """Build thread with analytics from events."""
        if not events:
            raise EmailAdapterError("Cannot build thread with no events")

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)

        # Determine direction for each event
        for event in events:
            if user_email.lower() in event.sender.email.lower():
                event.direction = EmailDirection.OUTGOING
            else:
                event.direction = EmailDirection.INCOMING

        # Collect participants
        participants = {}
        for event in events:
            participants[event.sender.email] = event.sender
            for r in event.recipients + event.cc:
                participants[r.email] = r

        # Compute analytics
        incoming_count = sum(1 for e in events if e.direction == EmailDirection.INCOMING)
        outgoing_count = sum(1 for e in events if e.direction == EmailDirection.OUTGOING)

        last_incoming = next(
            (e for e in reversed(events) if e.direction == EmailDirection.INCOMING),
            None,
        )
        last_outgoing = next(
            (e for e in reversed(events) if e.direction == EmailDirection.OUTGOING),
            None,
        )

        # Calculate reply gap
        reply_gap_hours = None
        awaiting_reply = False

        if last_incoming and (not last_outgoing or last_incoming.timestamp > last_outgoing.timestamp):
            awaiting_reply = True
            reply_gap_hours = (datetime.now(timezone.utc) - last_incoming.timestamp).total_seconds() / 3600

        # Count follow-ups (incoming without reply)
        follow_up_count = 0
        last_reply_time = None
        for event in events:
            if event.direction == EmailDirection.OUTGOING:
                last_reply_time = event.timestamp
            elif event.direction == EmailDirection.INCOMING:
                if last_reply_time is None or event.timestamp > last_reply_time:
                    # Check if this is a follow-up (same sender, no reply in between)
                    if last_reply_time:
                        follow_up_count += 1

        return EmailThread(
            thread_id=f"gmail:{thread_id}",
            provider=EmailProvider.GMAIL,
            subject=events[0].subject if events else "",
            participant_count=len(participants),
            participants=list(participants.values()),
            first_message_at=events[0].timestamp,
            last_message_at=events[-1].timestamp,
            message_count=len(events),
            incoming_count=incoming_count,
            outgoing_count=outgoing_count,
            last_direction=events[-1].direction,
            last_outgoing_at=last_outgoing.timestamp if last_outgoing else None,
            last_incoming_at=last_incoming.timestamp if last_incoming else None,
            awaiting_reply=awaiting_reply,
            reply_gap_hours=reply_gap_hours,
            follow_up_count=follow_up_count,
        )

    def _extract_body(self, data: Dict[str, Any]) -> str:
        """Extract plain text body from message data."""
        payload = data.get("payload", {})

        # Try to find plain text part
        def find_text_part(part: Dict[str, Any]) -> Optional[str]:
            mime_type = part.get("mimeType", "")

            if mime_type == "text/plain":
                body = part.get("body", {})
                data_str = body.get("data", "")
                if data_str:
                    return base64.urlsafe_b64decode(data_str).decode("utf-8", errors="replace")

            # Recurse into multipart
            for sub_part in part.get("parts", []):
                result = find_text_part(sub_part)
                if result:
                    return result

            return None

        text = find_text_part(payload)
        return text or ""


__all__ = ["GmailAdapter"]
