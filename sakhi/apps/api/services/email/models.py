"""
Normalized Email Event Model
----------------------------
Provider-agnostic models that all adapters must map into.
All downstream intelligence relies ONLY on these models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EmailDirection(str, Enum):
    """Direction of email relative to user."""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class SyncStatus(str, Enum):
    """Status of email sync."""
    NOT_CONNECTED = "not_connected"
    CONNECTING = "connecting"
    INITIAL_SYNC = "initial_sync"
    INCREMENTAL_SYNC = "incremental_sync"
    PAUSED = "paused"
    ERROR = "error"
    REVOKED = "revoked"


class EmailProvider(str, Enum):
    """Supported email providers."""
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    # Future: IMAP = "imap"


class EmailSender(BaseModel):
    """Normalized sender/recipient info."""
    email: str
    name: Optional[str] = None
    domain: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        if not self.domain and self.email:
            parts = self.email.split("@")
            if len(parts) == 2:
                self.domain = parts[1].lower()


class EmailHeaders(BaseModel):
    """Relevant email headers for signal extraction."""
    list_unsubscribe: Optional[str] = None
    auto_submitted: Optional[str] = None
    precedence: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    content_type: Optional[str] = None


class EmailEvent(BaseModel):
    """
    Normalized email event - the core abstraction.

    All providers must map into this schema.
    All signal extractors operate on this model.
    """
    # Identifiers
    message_id: str
    thread_id: str
    provider: EmailProvider
    provider_message_id: str  # Original provider ID

    # Timing
    timestamp: datetime
    received_at: Optional[datetime] = None

    # Direction and parties
    direction: EmailDirection
    sender: EmailSender
    recipients: List[EmailSender] = Field(default_factory=list)
    cc: List[EmailSender] = Field(default_factory=list)

    # Content metadata (NOT the body)
    subject: str = ""
    has_attachments: bool = False
    attachment_count: int = 0

    # Headers for signal extraction
    headers: EmailHeaders = Field(default_factory=EmailHeaders)

    # Provider labels/folders
    labels: List[str] = Field(default_factory=list)
    is_read: bool = True
    is_starred: bool = False
    is_important: bool = False

    # Computed flags
    is_newsletter: bool = False
    is_automated: bool = False
    is_transactional: bool = False

    class Config:
        use_enum_values = True


class EmailThread(BaseModel):
    """
    A conversation thread with computed analytics.
    """
    thread_id: str
    provider: EmailProvider

    # Thread metadata
    subject: str = ""
    participant_count: int = 0
    participants: List[EmailSender] = Field(default_factory=list)

    # Thread timeline
    first_message_at: datetime
    last_message_at: datetime
    message_count: int = 0

    # Direction analysis
    incoming_count: int = 0
    outgoing_count: int = 0
    last_direction: EmailDirection = EmailDirection.INCOMING

    # Reply analysis
    last_outgoing_at: Optional[datetime] = None
    last_incoming_at: Optional[datetime] = None
    awaiting_reply: bool = False
    reply_gap_hours: Optional[float] = None

    # Follow-up tracking
    follow_up_count: int = 0  # Times they followed up without our reply

    class Config:
        use_enum_values = True


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


# =============================================================================
# Signal Models (output of signal extractors)
# =============================================================================

class SignalType(str, Enum):
    """Types of signals extracted from email."""
    SUBSCRIPTION = "subscription"
    AVOIDANCE = "avoidance"
    BOUNDARY_EROSION = "boundary_erosion"
    COGNITIVE_LOAD = "cognitive_load"
    FOLLOW_UP_NEEDED = "follow_up_needed"


class SubscriptionSignal(BaseModel):
    """Detected subscription/recurring email."""
    signal_type: SignalType = SignalType.SUBSCRIPTION
    domain: str
    sender_email: str
    sender_name: Optional[str] = None

    # Pattern
    cadence: Optional[str] = None  # daily, weekly, monthly, yearly
    cadence_confidence: float = 0.5

    # Classification
    category: Optional[str] = None  # entertainment, finance, shopping, news, etc.
    is_transactional: bool = False  # receipts, shipping updates
    is_marketing: bool = False

    # Engagement
    open_rate: Optional[float] = None
    last_opened_at: Optional[datetime] = None
    total_received: int = 0

    # Unsubscribe
    has_unsubscribe: bool = False
    unsubscribe_link: Optional[str] = None

    confidence: float = 0.5


class AvoidanceSignal(BaseModel):
    """Detected avoidance/postponement pattern."""
    signal_type: SignalType = SignalType.AVOIDANCE
    thread_id: str

    # Thread context
    subject: str = ""
    sender_email: str = ""
    sender_name: Optional[str] = None

    # Avoidance metrics
    duration_days: int
    follow_up_count: int = 0
    last_incoming_at: datetime

    # Severity
    severity: str = "mild"  # mild, moderate, significant
    confidence: float = 0.5

    # Suggested action
    suggested_action: Optional[str] = None


class BoundarySignal(BaseModel):
    """Detected boundary/rhythm pattern."""
    signal_type: SignalType = SignalType.BOUNDARY_EROSION

    # Time analysis
    period_start: datetime
    period_end: datetime

    # Metrics
    total_emails: int = 0
    after_hours_count: int = 0
    after_hours_pct: float = 0.0
    weekend_count: int = 0
    weekend_pct: float = 0.0
    late_night_count: int = 0  # After 10pm

    # Trend
    trend: str = "stable"  # improving, stable, worsening
    previous_after_hours_pct: Optional[float] = None

    # Impact
    erosion_score: float = 0.0  # 0-1
    friction_impact: Optional[str] = None  # chaos_friction, etc.

    confidence: float = 0.5


class CognitiveLoadSignal(BaseModel):
    """Detected cognitive load pattern."""
    signal_type: SignalType = SignalType.COGNITIVE_LOAD

    # Period
    period_start: datetime
    period_end: datetime

    # Load metrics
    total_threads: int = 0
    active_threads: int = 0  # Threads with recent activity
    heavy_threads: int = 0  # >10 messages or >5 participants

    # Distribution
    top_senders: List[Dict[str, Any]] = Field(default_factory=list)
    thread_by_age: Dict[str, int] = Field(default_factory=dict)  # <1d, 1-7d, >7d

    # Score
    load_score: float = 0.0  # 0-1, higher = more load
    overwhelm_risk: str = "low"  # low, moderate, high

    confidence: float = 0.5


__all__ = [
    "EmailDirection",
    "SyncStatus",
    "EmailProvider",
    "EmailSender",
    "EmailHeaders",
    "EmailEvent",
    "EmailThread",
    "SyncState",
    "SyncProgress",
    "SignalType",
    "SubscriptionSignal",
    "AvoidanceSignal",
    "BoundarySignal",
    "CognitiveLoadSignal",
]
