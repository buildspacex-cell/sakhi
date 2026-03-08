"""Central redaction helpers for logs, telemetry, and alert payloads."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_RE_EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_RE_PHONE = re.compile(r"\b(\+?\d[\d\s-]{7,}\d)\b")
_RE_SECRET_ASSIGN = re.compile(
    r"(?i)\b(authorization|api[_-]?key|token|password|secret)\b\s*[:=]\s*([^\n,;]+)"
)
_RE_SENSITIVE_ASSIGN = re.compile(
    r"(?i)\b(text|content|prompt|query|user_query|message|journal|body|payload|raw|reply)\b\s*=\s*(.+)$"
)

_SENSITIVE_KEY_FRAGMENTS = (
    "text",
    "content",
    "prompt",
    "query",
    "message",
    "journal",
    "body",
    "payload",
    "raw",
    "reply",
    "authorization",
    "cookie",
    "token",
    "password",
    "secret",
    "api_key",
    "x-api-key",
    "set-cookie",
)

_IDENTIFIER_KEYS = {
    "id",
    "person_id",
    "user_id",
    "request_id",
    "job_id",
    "session_id",
    "entry_id",
    "reflection_id",
}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _is_sensitive_key(key_hint: str | None) -> bool:
    if not key_hint:
        return False
    normalized = str(key_hint).strip().lower()
    return any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _is_identifier_key(key_hint: str | None) -> bool:
    if not key_hint:
        return False
    normalized = str(key_hint).strip().lower()
    return normalized in _IDENTIFIER_KEYS or normalized.endswith("_id")


def _summary(value: Any) -> str:
    text = str(value or "")
    if not text:
        return "[REDACTED]"
    return f"[REDACTED len={len(text)} sha={_digest(text)}]"


def _mask_inline_pii(text: str) -> str:
    masked = _RE_EMAIL.sub(r"***@***", text)
    masked = _RE_PHONE.sub(_mask_phone, masked)
    return _RE_SECRET_ASSIGN.sub(lambda match: f"{match.group(1)}=<redacted>", masked)


def _mask_phone(match: re.Match[str]) -> str:
    token = match.group(1)
    normalized = token.replace(" ", "").replace("-", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{32}", normalized):
        return token
    digits_only = re.sub(r"\D", "", token)
    if len(digits_only) < 10:
        return token
    return "***"


def redact_observability_value(value: Any, *, key_hint: str | None = None, _depth: int = 0) -> Any:
    """Redact sensitive/freeform values while preserving useful structure."""

    if _depth > 6:
        return "[TRUNCATED]"

    if _is_sensitive_key(key_hint):
        return _summary(value)

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        masked = _RE_SECRET_ASSIGN.sub(lambda match: f"{match.group(1)}=<redacted>", value)
        if not _is_identifier_key(key_hint):
            masked = _mask_inline_pii(masked)
        if len(masked) > 1200:
            return _summary(masked)
        return masked

    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"[REDACTED bytes len={len(value)}]"

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_name = str(key)
            redacted[key_name] = redact_observability_value(
                item,
                key_hint=key_name,
                _depth=_depth + 1,
            )
        return redacted

    if isinstance(value, (list, tuple, set)):
        items = list(value)
        if len(items) > 25:
            kept = items[:25]
            out = [
                redact_observability_value(item, key_hint=key_hint, _depth=_depth + 1)
                for item in kept
            ]
            out.append(f"... ({len(items) - len(kept)} more)")
            return out
        return [
            redact_observability_value(item, key_hint=key_hint, _depth=_depth + 1)
            for item in items
        ]

    return redact_observability_value(str(value), key_hint=key_hint, _depth=_depth + 1)


def redact_log_line(message: str) -> str:
    """Best-effort redaction for formatted log lines."""

    if not message:
        return message

    scrubbed = _mask_inline_pii(message)

    match = _RE_SENSITIVE_ASSIGN.search(scrubbed)
    if match:
        key = match.group(1)
        value = match.group(2)
        scrubbed = f"{scrubbed[:match.start()]}{key}={_summary(value)}"

    if len(scrubbed) > 2000:
        return f"{scrubbed[:900]} ... [TRUNCATED len={len(scrubbed)} sha={_digest(scrubbed)}]"
    return scrubbed


__all__ = ["redact_log_line", "redact_observability_value"]
