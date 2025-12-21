from __future__ import annotations

import json
import os
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from redis import asyncio as aioredis

RedisCallable = Callable[..., Awaitable[Any]]
F = TypeVar("F", bound=RedisCallable)

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis = aioredis.from_url(url, decode_responses=True)
    return _redis


async def cache_get(key: str) -> str | None:
    redis = await _get_redis()
    return await redis.get(key)


async def cache_set(key: str, value: str, ttl: int | None = 600) -> None:
    redis = await _get_redis()
    if ttl:
        await redis.set(key, value, ex=max(ttl, 1))
    else:
        await redis.set(key, value)


def _build_key(prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    payload = {"args": args, "kwargs": kwargs}
    serialized = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
    return f"{prefix}:{serialized}"


def cached(ttl: int = 600) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @wraps(fn)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            key = _build_key(fn.__name__, args, kwargs)
            cached_value = await cache_get(key)
            if cached_value is not None:
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    pass

            result = await fn(*args, **kwargs)
            try:
                payload = json.dumps(result, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                return result

            await cache_set(key, payload, ttl=ttl)
            return result

        return wrapped  # type: ignore[return-value]

    return decorator


__all__ = ["cache_get", "cache_set", "cached"]
