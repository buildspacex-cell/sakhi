"""
Sakhi Email Intelligence Service
--------------------------------
Extracts patterns from email metadata to reduce cognitive friction.

Key Principle: Email is a signal generator, not a content store.

Components:
- adapters/: Provider-specific implementations (Gmail, Outlook)
- signals/: Pattern extractors (avoidance, subscriptions, boundaries)
- models.py: Normalized event model (provider-agnostic)
- sync.py: Sync orchestration
- integration.py: Connect to Sakhi intelligence layer
"""

from sakhi.apps.api.services.email.models import (
    EmailEvent,
    EmailSender,
    EmailThread,
    SyncState,
    SyncStatus,
)
from sakhi.apps.api.services.email.sync import (
    get_sync_status,
    pause_sync,
    resume_sync,
    start_email_sync,
)

__all__ = [
    "EmailEvent",
    "EmailThread",
    "EmailSender",
    "SyncState",
    "SyncStatus",
    "start_email_sync",
    "get_sync_status",
    "pause_sync",
    "resume_sync",
]
