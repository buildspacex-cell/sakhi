from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec

logger = logging.getLogger(__name__)


async def persist_trace(trace: Dict[str, Any]) -> None:
    try:
        trace.setdefault("trace_id", str(uuid.uuid4()))

        def _default(obj: Any) -> str:
            if isinstance(obj, uuid.UUID):
                return str(obj)
            return str(obj)

        payload_json = json.dumps(trace, ensure_ascii=False, default=_default)

        await dbexec(
            """
            INSERT INTO debug_traces (trace_id, person_id, flow, payload, created_at)
            VALUES ($1, $2, $3, $4, now())
            """,
            trace["trace_id"],
            trace.get("person_id"),
            trace.get("flow"),
            payload_json,
        )
    except Exception as exc:  # pragma: no cover - debug persistence best effort
        logger.warning("debug_trace_persist_failed", exc_info=exc)
