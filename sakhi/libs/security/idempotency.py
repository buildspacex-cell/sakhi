"""Database backed idempotency helpers keyed on request headers."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Mapping

from sakhi.libs.schemas import execute, fetch_one

IdempotentHandler = Callable[[], Awaitable[Any]]
_HEADER = "idempotency-key"


def extract_idempotency_key(headers: Mapping[str, str]) -> str | None:
    """Return the Idempotency-Key header value if present."""

    for key, value in headers.items():
        if key.lower() == _HEADER:
            trimmed = value.strip()
            return trimmed or None
    return None


async def run_idempotent(
    headers: Mapping[str, str],
    handler: IdempotentHandler,
    *,
    event_type: str = "idempotent_request",
    payload: Any | None = None,
    user_id: str | None = None,
) -> Any:
    """Execute handler once per idempotency key, returning cached results when duplicated."""

    key = extract_idempotency_key(headers)
    if not key:
        return await handler()

    record = await fetch_one(
        "SELECT response FROM events WHERE idempotency_key = $1",
        key,
    )
    if record and record["response"] is not None:
        return record["response"]

    result = await handler()
    payload_json = json.dumps(payload or {}, ensure_ascii=False, default=str)
    response_json = json.dumps(result, ensure_ascii=False, default=str)

    await execute(
        """
        INSERT INTO events (user_id, event_type, payload, idempotency_key, response)
        VALUES ($1, $2, $3::jsonb, $4, $5::jsonb)
        ON CONFLICT (idempotency_key)
        DO UPDATE SET response = EXCLUDED.response
        """,
        user_id,
        event_type,
        payload_json,
        key,
        response_json,
    )
    return result


__all__ = ["extract_idempotency_key", "run_idempotent"]
