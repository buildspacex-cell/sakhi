"""
Base Email Adapter
------------------
Abstract interface that all email providers must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from sakhi.apps.api.services.email.models import (
    EmailEvent,
    EmailProvider,
    EmailThread,
    SyncState,
)


class EmailAdapterError(Exception):
    """Base exception for adapter errors."""
    pass


class TokenExpiredError(EmailAdapterError):
    """OAuth token has expired, needs refresh."""
    pass


class TokenRefreshError(EmailAdapterError):
    """Failed to refresh OAuth token."""
    pass


class QuotaExceededError(EmailAdapterError):
    """API quota exceeded, need to back off."""
    retry_after_seconds: int = 60


class PermissionRevokedError(EmailAdapterError):
    """User revoked OAuth permissions."""
    pass


class BaseEmailAdapter(ABC):
    """
    Abstract base class for email provider adapters.

    All providers must implement this interface to ensure
    the intelligence layer remains provider-agnostic.
    """

    provider: EmailProvider

    def __init__(self, person_id: str, sync_state: Optional[SyncState] = None):
        self.person_id = person_id
        self.sync_state = sync_state

    # =========================================================================
    # OAuth Methods
    # =========================================================================

    @abstractmethod
    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            redirect_uri: Where to redirect after auth
            state: CSRF token to verify callback

        Returns:
            Authorization URL to redirect user to
        """
        pass

    @abstractmethod
    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Tuple[str, str, datetime]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Must match original redirect URI

        Returns:
            Tuple of (access_token, refresh_token, expires_at)

        Raises:
            EmailAdapterError: If exchange fails
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Tuple[str, datetime]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token

        Returns:
            Tuple of (new_access_token, new_expires_at)

        Raises:
            TokenRefreshError: If refresh fails
            PermissionRevokedError: If user revoked access
        """
        pass

    @abstractmethod
    async def revoke_access(self, access_token: str) -> bool:
        """
        Revoke OAuth access (user disconnecting).

        Args:
            access_token: Token to revoke

        Returns:
            True if revoked successfully
        """
        pass

    # =========================================================================
    # Sync Methods
    # =========================================================================

    @abstractmethod
    async def get_message_ids(
        self,
        access_token: str,
        *,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        max_results: int = 100,
        page_token: Optional[str] = None,
    ) -> Tuple[List[str], Optional[str]]:
        """
        Get message IDs (for initial/full sync).

        Args:
            access_token: Valid OAuth token
            after: Only messages after this date
            before: Only messages before this date
            max_results: Max messages per page
            page_token: Pagination token

        Returns:
            Tuple of (message_ids, next_page_token)
        """
        pass

    @abstractmethod
    async def get_history(
        self,
        access_token: str,
        start_history_id: str,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Get changes since last sync (incremental).

        Args:
            access_token: Valid OAuth token
            start_history_id: History ID from last sync

        Returns:
            Tuple of (changes, new_history_id)
        """
        pass

    @abstractmethod
    async def fetch_message_metadata(
        self,
        access_token: str,
        message_id: str,
    ) -> EmailEvent:
        """
        Fetch metadata for a single message.

        Args:
            access_token: Valid OAuth token
            message_id: Provider-specific message ID

        Returns:
            Normalized EmailEvent
        """
        pass

    @abstractmethod
    async def fetch_messages_batch(
        self,
        access_token: str,
        message_ids: List[str],
    ) -> List[EmailEvent]:
        """
        Fetch metadata for multiple messages (batch).

        Args:
            access_token: Valid OAuth token
            message_ids: List of provider-specific message IDs

        Returns:
            List of normalized EmailEvents
        """
        pass

    @abstractmethod
    async def fetch_message_body(
        self,
        access_token: str,
        message_id: str,
    ) -> str:
        """
        Fetch full message body (ONLY when explicitly requested).

        Args:
            access_token: Valid OAuth token
            message_id: Provider-specific message ID

        Returns:
            Message body as plain text
        """
        pass

    # =========================================================================
    # Thread Methods
    # =========================================================================

    @abstractmethod
    async def fetch_thread(
        self,
        access_token: str,
        thread_id: str,
    ) -> EmailThread:
        """
        Fetch and reconstruct a thread.

        Args:
            access_token: Valid OAuth token
            thread_id: Provider-specific thread ID

        Returns:
            Reconstructed EmailThread with analytics
        """
        pass

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @abstractmethod
    async def get_user_email(self, access_token: str) -> str:
        """
        Get the authenticated user's email address.

        Args:
            access_token: Valid OAuth token

        Returns:
            User's email address
        """
        pass

    async def iter_all_messages(
        self,
        access_token: str,
        *,
        after: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> AsyncIterator[EmailEvent]:
        """
        Iterate through all messages (handles pagination).

        Args:
            access_token: Valid OAuth token
            after: Only messages after this date
            batch_size: Messages per batch

        Yields:
            EmailEvent for each message
        """
        page_token = None

        while True:
            message_ids, page_token = await self.get_message_ids(
                access_token,
                after=after,
                max_results=batch_size,
                page_token=page_token,
            )

            if message_ids:
                events = await self.fetch_messages_batch(access_token, message_ids)
                for event in events:
                    yield event

            if not page_token:
                break


__all__ = [
    "BaseEmailAdapter",
    "EmailAdapterError",
    "TokenExpiredError",
    "TokenRefreshError",
    "QuotaExceededError",
    "PermissionRevokedError",
]
