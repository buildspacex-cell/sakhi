"""
Normalized Email Event Model
----------------------------
Provider-agnostic models that all adapters must map into.
All downstream intelligence relies ONLY on these models.

Note: Sync-specific models (SyncStatus, SyncState, SyncProgress)
stay in sakhi as they are application-level concerns, not temporal primitives.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmailDirection(str, Enum):
    """Direction of email relative to user."""

    INCOMING = "incoming"
    OUTGOING = "outgoing"


class EmailProvider(str, Enum):
    """Supported email providers."""

    GMAIL = "gmail"
    OUTLOOK = "outlook"
    # Future: IMAP = "imap"


class EmailSender(BaseModel):
    """Normalized sender/recipient info."""

    email: str
    name: str | None = None
    domain: str = ""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.domain and self.email:
            parts = self.email.split("@")
            if len(parts) == 2:
                self.domain = parts[1].lower()


class EmailHeaders(BaseModel):
    """Relevant email headers for signal extraction."""

    list_unsubscribe: str | None = None
    auto_submitted: str | None = None
    precedence: str | None = None
    in_reply_to: str | None = None
    references: str | None = None
    content_type: str | None = None


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
    received_at: datetime | None = None

    # Direction and parties
    direction: EmailDirection
    sender: EmailSender
    recipients: list[EmailSender] = Field(default_factory=list)
    cc: list[EmailSender] = Field(default_factory=list)

    # Content metadata (NOT the body)
    subject: str = ""
    has_attachments: bool = False
    attachment_count: int = 0

    # Headers for signal extraction
    headers: EmailHeaders = Field(default_factory=EmailHeaders)

    # Provider labels/folders
    labels: list[str] = Field(default_factory=list)
    is_read: bool = True
    is_starred: bool = False
    is_important: bool = False

    # Computed flags
    is_newsletter: bool = False
    is_automated: bool = False
    is_transactional: bool = False

    model_config = ConfigDict(use_enum_values=True)


class EmailThread(BaseModel):
    """A conversation thread with computed analytics."""

    thread_id: str
    provider: EmailProvider

    # Thread metadata
    subject: str = ""
    participant_count: int = 0
    participants: list[EmailSender] = Field(default_factory=list)

    # Thread timeline
    first_message_at: datetime
    last_message_at: datetime
    message_count: int = 0

    # Direction analysis
    incoming_count: int = 0
    outgoing_count: int = 0
    last_direction: EmailDirection = EmailDirection.INCOMING

    # Reply analysis
    last_outgoing_at: datetime | None = None
    last_incoming_at: datetime | None = None
    awaiting_reply: bool = False
    reply_gap_hours: float | None = None

    # Follow-up tracking
    follow_up_count: int = 0  # Times they followed up without our reply

    model_config = ConfigDict(use_enum_values=True)


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
    sender_name: str | None = None

    # Pattern
    cadence: str | None = None  # daily, weekly, monthly, yearly
    cadence_confidence: float = 0.5

    # Classification
    category: str | None = None  # entertainment, finance, shopping, news, etc.
    is_transactional: bool = False  # receipts, shipping updates
    is_marketing: bool = False

    # Engagement
    open_rate: float | None = None
    last_opened_at: datetime | None = None
    total_received: int = 0

    # Unsubscribe
    has_unsubscribe: bool = False
    unsubscribe_link: str | None = None

    confidence: float = 0.5


class AvoidanceSignal(BaseModel):
    """Detected avoidance/postponement pattern."""

    signal_type: SignalType = SignalType.AVOIDANCE
    thread_id: str

    # Thread context
    subject: str = ""
    sender_email: str = ""
    sender_name: str | None = None

    # Avoidance metrics
    duration_days: int
    follow_up_count: int = 0
    last_incoming_at: datetime

    # Severity
    severity: str = "mild"  # mild, moderate, significant
    confidence: float = 0.5

    # Suggested action
    suggested_action: str | None = None


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
    previous_after_hours_pct: float | None = None

    # Impact
    erosion_score: float = 0.0  # 0-1
    friction_impact: str | None = None  # chaos_friction, etc.

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
    top_senders: list[dict[str, Any]] = Field(default_factory=list)
    thread_by_age: dict[str, int] = Field(default_factory=dict)  # <1d, 1-7d, >7d

    # Score
    load_score: float = 0.0  # 0-1, higher = more load
    overwhelm_risk: str = "low"  # low, moderate, high

    confidence: float = 0.5


__all__ = [
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
]
