from __future__ import annotations

import json
import uuid
from contextvars import ContextVar
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.utils import EnhancedJSONEncoder

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


class DebugFlow:
    def __init__(self, trace_id: str | None = None, person_id: str | None = None) -> None:
        self.trace_id = trace_id
        self.person_id = person_id
        self.events: List[Dict[str, Any]] = []

    def add(self, stage: str, label: str, payload: Dict[str, Any] | None = None) -> None:
        self.events.append({"stage": stage, "label": label, "payload": payload or {}})

    async def finish(self, success: bool, extra: Dict[str, Any] | None = None) -> None:
        trace_identifier = self.trace_id or trace_id_var.get()
        if not trace_identifier:
            return

        try:
            trace_uuid = uuid.UUID(str(trace_identifier))
            trace_id_str = str(trace_uuid)
        except (ValueError, TypeError):
            trace_id_str = str(trace_identifier)

        person_id_str: str | None = None
        if self.person_id:
            try:
                person_id_str = str(uuid.UUID(str(self.person_id)))
            except (ValueError, TypeError):
                person_id_str = str(self.person_id)

        payload: Dict[str, Any] = {
            "trace_id": trace_id_str,
            "success": success,
            "events": self.events,
            "extra": extra,
        }
        if person_id_str is not None:
            payload["person_id"] = person_id_str

        self.trace_id = trace_id_str
        if person_id_str is not None:
            self.person_id = person_id_str

        await q(
            """
              UPDATE debug_traces
                 SET finished_at = now(),
                     success = $1,
                     payload = $2::jsonb
               WHERE trace_id = $3
            """,
            success,
            json.dumps(payload, cls=EnhancedJSONEncoder, ensure_ascii=False),
            trace_id_str,
        )
