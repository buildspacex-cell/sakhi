"""Request telemetry middleware for logging sanitized request metadata."""

from __future__ import annotations

import json
from typing import Any, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from sakhi.libs.schemas.db import get_async_pool

from .auth_pilot import _mask_pii


def _to_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, (list, tuple)):
        return {"items": list(value)[:20]}
    if value is None:
        return {}
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            value = value[:2000]
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"data": parsed}
    except Exception:
        return {"raw": str(value)[:2000]}


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Persist lightweight request telemetry to Postgres."""

    async def dispatch(self, request: Request, call_next):
        scrubbed_body: Dict[str, Any] = {}
        try:
            raw_body = await request.body()
            if raw_body:
                initial_json = _to_json(raw_body)
                scrubbed = json.dumps(initial_json)
                scrubbed_body = _to_json(_mask_pii(scrubbed))
        except Exception:  # pragma: no cover - optional defensive guard
            scrubbed_body = {}

        response = await call_next(request)

        try:
            pool = await get_async_pool()
            user_id = getattr(request.state, "user_id", None)
            headers = {k: _mask_pii(v) for k, v in request.headers.items()}
            duration_ms = int(response.headers.get("X-Response-Time-ms", "0") or 0)
            client_host = getattr(request.client, "host", None)
            async with pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO request_logs(user_id, method, path, status, duration_ms, ip, headers, body)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    user_id,
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                    client_host,
                    headers,
                    scrubbed_body,
                )
        except Exception:  # pragma: no cover - telemetry best-effort
            pass

        return response


__all__ = ["TelemetryMiddleware"]
