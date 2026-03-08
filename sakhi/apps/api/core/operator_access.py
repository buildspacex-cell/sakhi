"""Break-glass operator access guardrails for privileged API paths."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Mapping

OPERATOR_PROTECTED_PREFIXES: tuple[str, ...] = (
    "/admin",
    "/debug",
    "/lab",
    "/dev",
    "/demo",
    "/memory/dev",
)
OPERATOR_PROTECTED_EXACT_PATHS: tuple[str, ...] = (
    "/system/audit",
)

HEADER_OPERATOR_TOKEN = "x-sakhi-operator-token"
HEADER_OPERATOR_ID = "x-sakhi-operator-id"
HEADER_APPROVAL_REF = "x-sakhi-approval-ref"
HEADER_ACCESS_REASON = "x-sakhi-breakglass-reason"


@dataclass(frozen=True)
class OperatorAccessDecision:
    ok: bool
    code: str
    operator_id: str | None = None
    approval_ref: str | None = None
    reason: str | None = None


def _normalized_header(headers: Mapping[str, str], key: str) -> str:
    value = headers.get(key)
    if value is None:
        value = headers.get(key.lower())
    if value is None:
        value = headers.get(key.upper())
    return (value or "").strip()


def _normalize_path(path: str) -> str:
    cleaned = (path or "/").strip()
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned or "/"


def is_operator_protected_path(path: str) -> bool:
    target = _normalize_path(path)
    if target in OPERATOR_PROTECTED_EXACT_PATHS:
        return True
    for prefix in OPERATOR_PROTECTED_PREFIXES:
        if target == prefix or target.startswith(f"{prefix}/"):
            return True
    return False


def validate_operator_access(
    headers: Mapping[str, str],
    *,
    expected_token: str,
) -> OperatorAccessDecision:
    token_expected = (expected_token or "").strip()
    if not token_expected:
        return OperatorAccessDecision(ok=False, code="operator_token_not_configured")

    token_provided = _normalized_header(headers, HEADER_OPERATOR_TOKEN)
    if not token_provided:
        return OperatorAccessDecision(ok=False, code="operator_token_missing")
    if not secrets.compare_digest(token_provided, token_expected):
        return OperatorAccessDecision(ok=False, code="operator_token_invalid")

    operator_id = _normalized_header(headers, HEADER_OPERATOR_ID)
    if len(operator_id) < 3:
        return OperatorAccessDecision(ok=False, code="operator_id_missing")

    approval_ref = _normalized_header(headers, HEADER_APPROVAL_REF)
    if len(approval_ref) < 6:
        return OperatorAccessDecision(ok=False, code="approval_ref_missing")

    reason = _normalized_header(headers, HEADER_ACCESS_REASON)
    if len(reason) < 12:
        return OperatorAccessDecision(ok=False, code="breakglass_reason_missing")

    return OperatorAccessDecision(
        ok=True,
        code="ok",
        operator_id=operator_id[:80],
        approval_ref=approval_ref[:120],
        reason=reason[:240],
    )


__all__ = [
    "HEADER_ACCESS_REASON",
    "HEADER_APPROVAL_REF",
    "HEADER_OPERATOR_ID",
    "HEADER_OPERATOR_TOKEN",
    "OperatorAccessDecision",
    "OPERATOR_PROTECTED_EXACT_PATHS",
    "OPERATOR_PROTECTED_PREFIXES",
    "is_operator_protected_path",
    "validate_operator_access",
]

