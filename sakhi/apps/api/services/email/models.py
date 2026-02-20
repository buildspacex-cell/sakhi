"""
Normalized Email Event Model
----------------------------
Provider-agnostic models that all adapters must map into.
All downstream intelligence relies ONLY on these models.

Signal-related models are defined in kala and re-exported here.
Sync-specific models (SyncStatus, SyncState, SyncProgress) remain sakhi-specific.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

# Re-export signal models from kala (single source of truth)
from kala.signals.email.models import (  # noqa: F401
    AvoidanceSignal,
    BoundarySignal,
    CognitiveLoadSignal,
    EmailDirection,
    EmailEvent,
    EmailHeaders,
    EmailProvider,
    EmailSender,
    EmailThread,
    SignalType,
    SubscriptionSignal,
)


class SyncStatus(str, Enum):
    """Status of email sync."""
    NOT_CONNECTED = "not_connected"
    CONNECTING = "connecting"
    INITIAL_SYNC = "initial_sync"
    INCREMENTAL_SYNC = "incremental_sync"
    PAUSED = "paused"
    ERROR = "error"
    REVOKED = "revoked"


class SyncState(BaseModel):
    """
    Tracks sync state for a user's email account.
    """
    person_id: str
    provider: EmailProvider

    # Connection
    status: SyncStatus = SyncStatus.NOT_CONNECTED
    connected_at: Optional[datetime] = None

    # OAuth
    access_token_encrypted: Optional[str] = None
    refresh_token_encrypted: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    # Sync progress
    last_sync_at: Optional[datetime] = None
    last_history_id: Optional[str] = None  # For incremental sync
    messages_synced: int = 0

    # Error tracking
    error_message: Optional[str] = None
    error_at: Optional[datetime] = None
    consecutive_errors: int = 0

    # User control
    paused_at: Optional[datetime] = None
    paused_by_user: bool = False

    class Config:
        use_enum_values = True


class SyncProgress(BaseModel):
    """Progress info for sync operations."""
    status: SyncStatus
    messages_synced: int = 0
    total_estimated: Optional[int] = None
    percent_complete: Optional[float] = None
    current_phase: str = "connecting"
    last_sync_at: Optional[datetime] = None
    error: Optional[str] = None


__all__ = [
    # Re-exported from kala
    "EmailDirection",
    "EmailProvider",
    "EmailSender",
    "EmailHeaders",
    "EmailEvent",
    "EmailThread",
    "SignalType",
    "SubscriptionSignal",
    "AvoidanceSignal",
    "BoundarySignal",
    "CognitiveLoadSignal",
    # Sakhi-specific
    "SyncStatus",
    "SyncState",
    "SyncProgress",
]
