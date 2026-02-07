"""
Email Provider Adapters
-----------------------
Provider-specific implementations that map to normalized models.

Each adapter must:
1. Handle OAuth flow
2. Fetch messages/metadata
3. Map to EmailEvent model
4. Support incremental sync
"""

from sakhi.apps.api.services.email.adapters.base import BaseEmailAdapter
from sakhi.apps.api.services.email.adapters.gmail import GmailAdapter

__all__ = [
    "BaseEmailAdapter",
    "GmailAdapter",
]
