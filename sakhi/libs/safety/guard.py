"""Minimal conversation guardrails for safety handling."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from sakhi.libs.schemas.db import get_async_pool

BLOCKLIST: List[str] = [
    r"\b(api[_-]?key|password|access[_-]?token)\b",
    r"\b(base64|decrypt|exfiltrate)\b",
    r"self[- ]?harm|suicid|harm yourself|kill myself",
    r"terrorism|explosive|bomb[- ]?making",
]

SAFE_SYSTEM = (
    "You are Sakhi. Be kind, pragmatic, and refuse unsafe requests. "
    "NEVER output or ask for secrets or API keys. If the user requests unsafe actions, refuse and offer a safe alternative."
)


def is_unsafe(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in BLOCKLIST)


async def guard_messages(user_id: str | None, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    last_user = next((msg for msg in reversed(messages) if msg.get("role") == "user"), {"content": ""})
    if is_unsafe(last_user.get("content", "")):
        pool = await get_async_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO incidents(user_id, kind, severity, path, detail)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                "safety_violation",
                "medium",
                "/chat",
                "unsafe_prompt_detected",
            )
        return [
            {"role": "system", "content": SAFE_SYSTEM},
            {
                "role": "assistant",
                "content": (
                    "I can’t help with that request. I can help you with a safer alternative—"
                    "what outcome are you aiming for?"
                ),
            },
        ]

    has_system = any(msg.get("role") == "system" for msg in messages)
    if has_system:
        return messages
    return [{"role": "system", "content": SAFE_SYSTEM}, *messages]


__all__ = ["guard_messages", "is_unsafe", "SAFE_SYSTEM", "BLOCKLIST"]
