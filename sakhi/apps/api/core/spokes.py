from __future__ import annotations

import datetime as dt
import json
import os

from redis import asyncio as aioredis

_redis: aioredis.Redis | None = None


async def r() -> aioredis.Redis:
    global _redis
    if _redis is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("Missing required env var: REDIS_URL")
        _redis = aioredis.from_url(redis_url, decode_responses=True)
    return _redis


async def get_json(key: str, default: dict | None = None) -> dict:
    redis = await r()
    value = await redis.get(key)
    if value is None:
        return {} if default is None else default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {} if default is None else default


async def set_json(key: str, value: dict, ttl: int | None = None) -> None:
    redis = await r()
    await redis.set(key, json.dumps(value))
    if ttl:
        await redis.expire(key, ttl)


def habit_key(pid: str, action: str) -> str:
    return f"habit_stats:{pid}:{action}"


def tone_key(pid: str) -> str:
    return f"tone_profile:{pid}"


def energy_curve_key(pid: str, date: dt.date) -> str:
    return f"energy_curve_daily:{pid}:{date}"


def chronotype_key(pid: str) -> str:
    return f"chronotype:{pid}"
