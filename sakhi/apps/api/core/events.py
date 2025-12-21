from __future__ import annotations

import json
import os
from typing import Any, Dict

from redis import asyncio as aioredis

MEMORY_EVENT = "memory.entry.observed"
_redis = None


async def _r():
    global _redis
    if _redis is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("Missing required env var: REDIS_URL")
        _redis = aioredis.from_url(redis_url, decode_responses=True)
    return _redis


async def publish(topic: str, payload: Dict[str, Any]) -> None:
    await (await _r()).lpush(f"queue:{topic}", json.dumps(payload))
