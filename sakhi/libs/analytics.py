"""
Server-side analytics — PostHog Python SDK wrapper.

Only emit events that the mobile client might drop (network failures, app kill).
All server emissions include `server_side: True` so PostHog dashboards can
differentiate client vs server events and deduplicate for funnel accuracy.

Enabled only when POSTHOG_SERVER_KEY is set. Silent no-op otherwise.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

_POSTHOG_KEY = os.getenv("POSTHOG_SERVER_KEY", "").strip()
_POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com").strip()

_client: Any = None
_client_lock = threading.Lock()


def _get_client() -> Any | None:
    """Lazy-init PostHog client. Returns None if key not set."""
    global _client
    if not _POSTHOG_KEY:
        return None
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        try:
            import posthog as ph
            ph.project_api_key = _POSTHOG_KEY
            ph.host = _POSTHOG_HOST
            # Disable unnecessary print output
            ph.debug = False
            _client = ph
            logger.info("[analytics] PostHog server-side analytics enabled")
        except ImportError:
            logger.warning("[analytics] posthog package not installed; server analytics disabled")
            _client = None
    return _client


def capture(person_id: str, event: str, props: dict | None = None) -> None:
    """Fire-and-forget: capture a server-side event for a known person."""
    client = _get_client()
    if client is None:
        return
    try:
        payload = {"server_side": True, **(props or {})}
        client.capture(person_id, event, payload)
    except Exception as exc:
        logger.debug("[analytics] capture failed event=%s err=%s", event, exc)


def delete_person(person_id: str) -> None:
    """
    Delete a person from PostHog (GDPR / user data deletion).
    Call this when a user permanently deletes their account.
    """
    client = _get_client()
    if client is None:
        return
    try:
        # PostHog Python SDK: delete person by distinct_id
        client.delete(person_id)
        logger.info("[analytics] PostHog person deleted person_id=%s", person_id)
    except Exception as exc:
        logger.warning("[analytics] PostHog person deletion failed person_id=%s err=%s", person_id, exc)
