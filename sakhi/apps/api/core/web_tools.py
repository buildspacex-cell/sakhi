from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Tuple

from fastapi import HTTPException

from sakhi.libs.llm_router.web_provider import WebProvider

_ALLOW = (
    "review",
    "reviews",
    "rating",
    "ratings",
    "trustpilot",
    "reddit",
    "compare",
    "pricing",
    "subscription",
    "app store",
    "how to start",
    "beginner",
    "best",
)

_CACHE: dict[str, Tuple[float, str]] = {}
_TTL = int(os.getenv("WEB_SEARCH_CACHE_TTL_SECONDS", "900"))
_PROVIDER = WebProvider()

ALLOW_WEB = os.getenv("SAKHI_ALLOW_WEB_SEARCH", "false").lower() == "true"
WEB_RPM = int(os.getenv("WEB_SEARCH_RATE_LIMIT_PER_MIN", "15"))
_web_hits: int = 0
_web_window_start: float = 0.0

_REDACT_EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\\.[A-Za-z]{2,})")
_REDACT_PHONE = re.compile(r"\\b(\\+?\\d[\\d\\s\\-]{7,})\\b")


def _cache_key(query: str) -> str:
    return hashlib.sha1(query.encode("utf-8")).hexdigest()


def _redact(text: str) -> str:
    redacted = _REDACT_EMAIL.sub("***@***", text)
    redacted = _REDACT_PHONE.sub("***", redacted)
    return redacted


def _allow(query: str) -> bool:
    lowered = query.lower()
    return any(term in lowered for term in _ALLOW)


def _rewrite(query: str) -> str:
    trimmed = query.strip()
    lowered = trimmed.lower()
    if any(word in lowered for word in ("review", "reviews", "rating", "ratings")):
        trimmed += " site:trustpilot.com OR site:reddit.com OR site:appbrain.com"
    return trimmed


async def smart_search(query: str) -> str:
    rewritten = _rewrite(query)
    if not _allow(rewritten):
        return "For privacy/safety, I only search the web for reviews, comparisons, pricing, or beginner how-to."

    key = _cache_key(rewritten)
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < _TTL:
        return cached[1]

    text = await _PROVIDER.search(rewritten)
    text = _redact(text)
    _CACHE[key] = (now, text)
    return text


async def check_web_rate_limit() -> None:
    if not ALLOW_WEB:
        raise HTTPException(status_code=403, detail="Web search disabled")
    global _web_hits, _web_window_start
    now = time.time()
    if now - _web_window_start > 60.0:
        _web_window_start = now
        _web_hits = 0
    _web_hits += 1
    if _web_hits > WEB_RPM:
        raise HTTPException(status_code=429, detail="Web search rate limit exceeded")


__all__ = ["smart_search", "check_web_rate_limit", "ALLOW_WEB"]
