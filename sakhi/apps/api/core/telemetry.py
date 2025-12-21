from __future__ import annotations

import logging
from typing import Any, Mapping

logger = logging.getLogger(__name__)


async def log_trace_event(event_name: str, payload: Mapping[str, Any] | None = None) -> None:
    """Best-effort async telemetry hook."""
    # Logging inside async helpers stays non-blocking and keeps observability.
    logger.info("trace_event.%s %s", event_name, dict(payload or {}))
