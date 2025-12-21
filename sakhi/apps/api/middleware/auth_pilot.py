"""Pilot authentication, rate limiting, and request correlation middleware."""

from __future__ import annotations

import os
import re
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from sakhi.libs.schemas.db import get_async_pool

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    redis = None

RE_EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
RE_PHONE = re.compile(r"\b(\+?\d[\d\s-]{7,}\d)\b")

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_REDIS = None
if redis is not None:  # pragma: no branch - trivial guard
    try:
        _REDIS = redis.from_url(_REDIS_URL)
    except Exception:  # pragma: no cover - optional infrastructure
        _REDIS = None


def _mask_pii(text: str) -> str:
    if not text:
        return text
    safe = RE_EMAIL.sub(r"***@***", text)
    safe = RE_PHONE.sub("***", safe)
    return safe


def _user_key(api_key: str) -> Optional[str]:
    token = api_key.strip() if api_key else ""
    return f"api:{token}" if token else None


class PilotAuthAndRateLimit(BaseHTTPMiddleware):
    """Authenticate pilot API keys, rate-limit requests, and attach request metadata."""

    def __init__(self, app, rpm: int = 60) -> None:
        super().__init__(app)
        self.rpm = max(int(rpm), 1)

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        start = time.time()
        request.state.request_id = req_id

        api_key = request.headers.get("X-API-Key", "").strip()
        user_id = None
        flags = {}

        pool = await get_async_pool()

        open_paths = ("/health", "/docs", "/openapi.json")
        if request.url.path not in open_paths:
            async with pool.acquire() as connection:
                row = await connection.fetchrow(
                    "SELECT user_id, flags FROM pilot_users WHERE api_key = $1",
                    api_key or None,
                )
            if not row:
                async with pool.acquire() as connection:
                    await connection.execute(
                        """
                        INSERT INTO incidents(user_id, kind, severity, path, detail)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        None,
                        "auth",
                        "low",
                        request.url.path,
                        "missing_or_invalid_api_key",
                    )
                return Response("Unauthorized (pilot)", status_code=401)

            user_id = row["user_id"]
            flags = row.get("flags") or {}
            request.state.user_id = user_id
            request.state.feature_flags = flags

        key = _user_key(api_key)
        if key and _REDIS is not None:
            bucket = f"ratelimit:{key}:{int(time.time() // 60)}"
            try:
                count = _REDIS.incr(bucket)
                _REDIS.expire(bucket, 120)
                if count > self.rpm:
                    async with pool.acquire() as connection:
                        await connection.execute(
                            """
                            INSERT INTO incidents(user_id, kind, severity, path, detail)
                            VALUES ($1, $2, $3, $4, $5)
                            """,
                            user_id,
                            "rate_limit",
                            "low",
                            request.url.path,
                            f"over {self.rpm}/min",
                        )
                    return Response("Rate limit exceeded", status_code=429)
            except Exception:  # pragma: no cover - optional infrastructure
                pass

        response = await call_next(request)

        duration_ms = int((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time-ms"] = str(duration_ms)

        return response


__all__ = ["PilotAuthAndRateLimit", "_mask_pii"]
