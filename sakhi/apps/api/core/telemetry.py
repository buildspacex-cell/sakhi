from __future__ import annotations

import logging
from typing import Any, Mapping

from sakhi.libs.security.observability_redaction import redact_observability_value

logger = logging.getLogger(__name__)


async def log_trace_event(event_name: str, payload: Mapping[str, Any] | None = None) -> None:
    """Best-effort async telemetry hook."""
    # Logging inside async helpers stays non-blocking and keeps observability.
    safe_payload = redact_observability_value(dict(payload or {}), key_hint="payload")
    logger.info("trace_event.%s %s", event_name, safe_payload)
