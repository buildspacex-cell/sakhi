"""User-consented support diagnostics routes (metadata-only, no journal/message text)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import asyncpg
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.monitoring import report_data_access_event
from sakhi.apps.api.services.continuity import CONTINUITY_SCOPE
from sakhi.apps.api.utils.person_resolver import resolve_person
from sakhi.libs.security.observability_redaction import redact_observability_value

SUPPORT_CODE_PREFIX = "SKH"

# Notification config — set ONE of these in Railway env:
#
# Option A — Telegram (recommended, free, 5 min setup):
#   1. Message @BotFather → /newbot → get SAKHI_SUPPORT_TELEGRAM_BOT_TOKEN
#   2. Message your bot once, then open:
#      https://api.telegram.org/bot{TOKEN}/getUpdates  → find chat.id
#   3. Set SAKHI_SUPPORT_TELEGRAM_CHAT_ID to that number
#
# Option B — Generic webhook (Discord, Slack, n8n, Zapier, Make):
#   Discord: channel → Integrations → Webhooks → New Webhook → copy URL
#   Slack: Apps → Incoming Webhooks → Add → copy URL
#   Set SAKHI_SUPPORT_WEBHOOK_URL to the URL
#
# If neither is set, reports are logged to Railway logs as SUPPORT_REPORT warnings.
SUPPORT_TELEGRAM_BOT_TOKEN = os.environ.get("SAKHI_SUPPORT_TELEGRAM_BOT_TOKEN", "").strip()
SUPPORT_TELEGRAM_CHAT_ID = os.environ.get("SAKHI_SUPPORT_TELEGRAM_CHAT_ID", "").strip()
SUPPORT_WEBHOOK_URL = os.environ.get("SAKHI_SUPPORT_WEBHOOK_URL", "").strip()


async def _notify_support(support_code: str, issue_summary: str, client_context: dict[str, Any]) -> None:
    """Fire-and-forget notification when a support report is created.

    Tries Telegram first, then generic webhook, then logs to Railway.
    All failures are soft — never affects the user-facing response.
    """
    platform = str(client_context.get("platform") or "unknown")
    app_version = str(client_context.get("appVersion") or "unknown")
    message = (
        f"\U0001f198 New support report \u2014 {support_code}\n"
        f"Issue: {issue_summary[:400]}\n"
        f"App {app_version} \u00b7 {platform}"
    )

    if SUPPORT_TELEGRAM_BOT_TOKEN and SUPPORT_TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{SUPPORT_TELEGRAM_BOT_TOKEN}/sendMessage"
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(url, json={"chat_id": SUPPORT_TELEGRAM_CHAT_ID, "text": message})
            return
        except Exception as exc:
            LOGGER.warning("Support Telegram notification failed (code=%s): %s", support_code, exc)

    if SUPPORT_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # text = Slack/generic, content = Discord — both fields for compatibility
                await client.post(SUPPORT_WEBHOOK_URL, json={"text": message, "content": message})
            return
        except Exception as exc:
            LOGGER.warning("Support webhook failed (code=%s): %s", support_code, exc)

    LOGGER.warning("SUPPORT_REPORT code=%s summary=%s platform=%s app=%s",
                   support_code, issue_summary[:200], platform, app_version)


DEFAULT_SUPPORT_TTL_HOURS = 72
DEFAULT_SUPPORT_SESSION_TTL_MINUTES = 30
MAX_SUPPORT_SESSION_TTL_MINUTES = 240
MAX_CONTEXT_KEYS = 24
MAX_LIST_ITEMS = 20
MAX_STRING_LEN = 220
MAX_TIMELINE_BATCH_EVENTS = 40
MAX_TIMELINE_EVENTS_PER_SESSION = 400
MAX_TIMELINE_PREVIEW_EVENTS = 120
ALLOWED_TIMELINE_EVENT_TYPES = {"screen_view", "action", "api_start", "api_end", "ui_error"}

router = APIRouter(prefix="/support", tags=["support"])
admin_router = APIRouter(prefix="/admin/support", tags=["support-admin"])


class SupportDiagnosticsOptions(BaseModel):
    enabled: bool = False
    include_conversation_metadata: bool = False


class SupportReportCreateRequest(BaseModel):
    person_id: str
    issue_summary: str = Field(min_length=8, max_length=1200)
    repro_steps: str | None = Field(default=None, max_length=3000)
    diagnostics: SupportDiagnosticsOptions = Field(default_factory=SupportDiagnosticsOptions)
    client_context: dict[str, Any] = Field(default_factory=dict)


class SupportReportRevokeRequest(BaseModel):
    person_id: str
    support_code: str


class SupportSessionStartRequest(BaseModel):
    person_id: str
    support_code: str
    duration_minutes: int | None = Field(default=None, ge=5, le=MAX_SUPPORT_SESSION_TTL_MINUTES)
    client_context: dict[str, Any] = Field(default_factory=dict)


class SupportTimelineEvent(BaseModel):
    type: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    ts: str | None = None
    seq: int | None = Field(default=None, ge=0, le=1_000_000)
    screen: str | None = Field(default=None, max_length=80)
    route: str | None = Field(default=None, max_length=160)
    method: str | None = Field(default=None, max_length=12)
    status: int | None = Field(default=None, ge=100, le=599)
    request_id: str | None = Field(default=None, max_length=120)
    latency_ms: int | None = Field(default=None, ge=0, le=120_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SupportSessionEventRequest(BaseModel):
    person_id: str
    support_code: str
    session_id: str
    events: list[SupportTimelineEvent] = Field(min_length=1, max_length=MAX_TIMELINE_BATCH_EVENTS)


class SupportSessionStopRequest(BaseModel):
    person_id: str
    support_code: str
    session_id: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_ts(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return None


def _support_ttl_hours() -> int:
    raw = str(os.getenv("SAKHI_SUPPORT_REPORT_TTL_HOURS", DEFAULT_SUPPORT_TTL_HOURS)).strip()
    try:
        hours = int(raw)
    except ValueError:
        hours = DEFAULT_SUPPORT_TTL_HOURS
    return min(max(hours, 1), 24 * 30)


def _support_session_ttl_minutes() -> int:
    raw = str(os.getenv("SAKHI_SUPPORT_SESSION_TTL_MINUTES", DEFAULT_SUPPORT_SESSION_TTL_MINUTES)).strip()
    try:
        minutes = int(raw)
    except ValueError:
        minutes = DEFAULT_SUPPORT_SESSION_TTL_MINUTES
    return min(max(minutes, 5), MAX_SUPPORT_SESSION_TTL_MINUTES)


def _sanitize_text(value: str | None, *, max_len: int) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) > max_len:
        return raw[:max_len]
    return raw


def _sanitize_json(value: Any, *, depth: int = 0) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value.strip()[:MAX_STRING_LEN]
    if depth >= 2:
        return str(value)[:MAX_STRING_LEN]
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= MAX_CONTEXT_KEYS:
                break
            normalized_key = str(key).strip()[:48]
            if not normalized_key:
                continue
            sanitized_item = _sanitize_json(item, depth=depth + 1)
            if sanitized_item is None:
                continue
            clean[normalized_key] = sanitized_item
        return clean
    if isinstance(value, (list, tuple)):
        clean_items: list[Any] = []
        for idx, item in enumerate(value):
            if idx >= MAX_LIST_ITEMS:
                break
            sanitized_item = _sanitize_json(item, depth=depth + 1)
            if sanitized_item is None:
                continue
            clean_items.append(sanitized_item)
        return clean_items
    return str(value)[:MAX_STRING_LEN]


def _sanitize_client_context(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    sanitized = _sanitize_json(payload)
    return sanitized if isinstance(sanitized, dict) else {}


def _normalize_support_code(value: str) -> str:
    token = "".join(char for char in str(value or "").upper() if char.isalnum() or char == "-").strip("-")
    if token.startswith(f"{SUPPORT_CODE_PREFIX}-"):
        return token
    if token.startswith(SUPPORT_CODE_PREFIX):
        suffix = token[len(SUPPORT_CODE_PREFIX):].lstrip("-")
        return f"{SUPPORT_CODE_PREFIX}-{suffix}" if suffix else SUPPORT_CODE_PREFIX
    return f"{SUPPORT_CODE_PREFIX}-{token}" if token else ""


def _generate_support_code() -> str:
    raw = secrets.token_hex(6).upper()
    return f"{SUPPORT_CODE_PREFIX}-{raw[:4]}-{raw[4:8]}-{raw[8:12]}"


def _normalize_event_label(value: str | None, *, max_len: int, allow_slash: bool = False) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-.:")
    if allow_slash:
        allowed.add("/")
    normalized = "".join(ch for ch in raw if ch in allowed)
    return normalized[:max_len]


def _parse_event_ts(value: str | None) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        return _utcnow()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return _utcnow()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_report_active(row: Mapping[str, Any], *, now: datetime | None = None) -> bool:
    current = now or _utcnow()
    status = str(row.get("status") or "").strip().lower()
    expires_at = row.get("expires_at")
    if not isinstance(expires_at, datetime):
        return status == "active"
    return status == "active" and expires_at > current


def _is_session_active(row: Mapping[str, Any], *, now: datetime | None = None) -> bool:
    current = now or _utcnow()
    status = str(row.get("status") or "").strip().lower()
    expires_at = row.get("expires_at")
    if not isinstance(expires_at, datetime):
        return status == "active"
    return status == "active" and expires_at > current


def _sanitize_timeline_metadata(payload: dict[str, Any] | None) -> dict[str, Any]:
    sanitized = _sanitize_client_context(payload)
    redacted = redact_observability_value(sanitized, key_hint="support_timeline_metadata")
    return redacted if isinstance(redacted, dict) else {}


def _build_public_session_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": str(row.get("id") or ""),
        "support_code": str(row.get("support_code") or ""),
        "status": str(row.get("status") or "unknown"),
        "started_at": _serialize_ts(row.get("started_at")),
        "last_event_at": _serialize_ts(row.get("last_event_at")),
        "stopped_at": _serialize_ts(row.get("stopped_at")),
        "expires_at": _serialize_ts(row.get("expires_at")),
        "event_count": int(row.get("event_count") or 0),
        "client_context": _coerce_json_object(row.get("client_context")),
    }


def _build_public_report_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics_enabled = bool(row.get("diagnostics_enabled"))
    include_conversation_metadata = bool(row.get("include_conversation_metadata"))
    client_context = _coerce_json_object(row.get("client_context"))
    snapshot = _coerce_json_object(row.get("diagnostics_snapshot"))
    payload: dict[str, Any] = {
        "report_id": str(row.get("id") or ""),
        "support_code": str(row.get("support_code") or ""),
        "status": str(row.get("status") or "unknown"),
        "created_at": _serialize_ts(row.get("created_at")),
        "updated_at": _serialize_ts(row.get("updated_at")),
        "expires_at": _serialize_ts(row.get("expires_at")),
        "revoked_at": _serialize_ts(row.get("revoked_at")),
        "resolved_at": _serialize_ts(row.get("resolved_at")),
        "issue_summary": str(row.get("issue_summary") or ""),
        "repro_steps": str(row.get("repro_steps") or ""),
        "diagnostics": {
            "enabled": diagnostics_enabled,
            "include_conversation_metadata": diagnostics_enabled and include_conversation_metadata,
        },
        "client_context": client_context,
    }
    payload["bundle_preview"] = snapshot
    return payload


async def _safe_fetch_one(sql: str, *args: Any) -> dict[str, Any] | None:
    try:
        return await q(sql, *args, one=True)
    except Exception:
        return None


def _coerce_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


async def _safe_fetch_all(sql: str, *args: Any) -> list[dict[str, Any]]:
    try:
        rows = await q(sql, *args)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


async def _fetch_report_by_code(person_id: str, support_code: str) -> dict[str, Any] | None:
    return await _safe_fetch_one(
        """
        SELECT *
        FROM support_debug_reports
        WHERE person_id = $1::uuid
          AND support_code = $2
        LIMIT 1
        """,
        person_id,
        support_code,
    )


async def _refresh_expired_session_status(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return row
    if _is_session_active(row):
        return row
    status = str(row.get("status") or "").strip().lower()
    expires_at = row.get("expires_at")
    if status != "active" or not isinstance(expires_at, datetime) or expires_at > _utcnow():
        return row
    updated = await _safe_fetch_one(
        """
        UPDATE support_debug_sessions
        SET status = 'expired', stopped_at = COALESCE(stopped_at, now()), updated_at = now()
        WHERE id = $1::uuid
          AND status = 'active'
        RETURNING *
        """,
        str(row.get("id")),
    )
    return updated or row


async def _fetch_latest_session(report_id: str) -> dict[str, Any] | None:
    row = await _safe_fetch_one(
        """
        SELECT *
        FROM support_debug_sessions
        WHERE report_id = $1::uuid
        ORDER BY started_at DESC
        LIMIT 1
        """,
        report_id,
    )
    if not row:
        return None
    return await _refresh_expired_session_status(row)


async def _build_timeline_preview(report_id: str) -> dict[str, Any]:
    if not await _table_exists("support_debug_sessions") or not await _table_exists("support_debug_events"):
        return {
            "available": False,
            "reason": "support_session_schema_missing",
        }

    session_rows = await _safe_fetch_all(
        """
        SELECT id, status, support_code, started_at, last_event_at, stopped_at, expires_at, event_count
        FROM support_debug_sessions
        WHERE report_id = $1::uuid
        ORDER BY started_at DESC
        LIMIT 6
        """,
        report_id,
    )
    event_rows = await _safe_fetch_all(
        """
        SELECT
            id,
            session_id,
            event_type,
            event_name,
            event_seq,
            event_at,
            screen,
            route,
            http_method,
            http_status,
            request_id,
            latency_ms,
            payload
        FROM support_debug_events
        WHERE report_id = $1::uuid
        ORDER BY event_at DESC, id DESC
        LIMIT $2
        """,
        report_id,
        MAX_TIMELINE_PREVIEW_EVENTS,
    )
    events = [
        {
            "session_id": str(row.get("session_id") or ""),
            "type": str(row.get("event_type") or ""),
            "name": str(row.get("event_name") or ""),
            "seq": row.get("event_seq"),
            "at": _serialize_ts(row.get("event_at")),
            "screen": str(row.get("screen") or ""),
            "route": str(row.get("route") or ""),
            "method": str(row.get("http_method") or ""),
            "status": row.get("http_status"),
            "request_id": str(row.get("request_id") or ""),
            "latency_ms": row.get("latency_ms"),
            "metadata": _coerce_json_object(row.get("payload")),
        }
        for row in reversed(event_rows)
    ]
    return {
        "available": True,
        "session_count": len(session_rows),
        "sessions": [_build_public_session_payload(row) for row in session_rows],
        "events": events,
    }


async def _table_exists(table_name: str) -> bool:
    row = await _safe_fetch_one(
        "SELECT to_regclass($1) AS regclass",
        f"public.{table_name}",
    )
    return bool(row and row.get("regclass"))


async def _table_has_column(table_name: str, column_name: str) -> bool:
    row = await _safe_fetch_one(
        """
        SELECT 1 AS ok
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = $1
          AND column_name = $2
        LIMIT 1
        """,
        table_name,
        column_name,
    )
    return bool(row and row.get("ok"))


async def _build_diagnostics_snapshot(
    person_id: str,
    *,
    include_conversation_metadata: bool,
) -> dict[str, Any]:
    now = _utcnow()
    snapshot: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "privacy_contract": {
            "journal_content_included": False,
            "conversation_text_included": False,
            "notes": "Metadata-only diagnostics snapshot.",
        },
        "runtime": {
            "environment": str(os.getenv("ENV") or os.getenv("NODE_ENV") or "unknown"),
        },
    }

    policy_row = await _safe_fetch_one(
        """
        SELECT enabled, updated_at, COALESCE(jsonb_array_length(exclusions), 0) AS exclusion_count
        FROM continuity_surface_policy
        WHERE person_id = $1::uuid AND scope = $2
        LIMIT 1
        """,
        person_id,
        CONTINUITY_SCOPE,
    )
    labels_total_row = await _safe_fetch_one(
        """
        SELECT COUNT(*)::int AS label_count,
               COUNT(DISTINCT anchor)::int AS topic_count
        FROM continuity_labels
        WHERE person_id = $1::uuid
        """,
        person_id,
    )
    reflection_rows = await _safe_fetch_all(
        """
        SELECT status, COUNT(*)::int AS count
        FROM deep_reflections
        WHERE person_id = $1::uuid
          AND created_at >= now() - interval '30 days'
        GROUP BY status
        ORDER BY status
        """,
        person_id,
    )
    snapshot["continuity"] = {
        "policy_enabled": bool((policy_row or {}).get("enabled")),
        "policy_updated_at": _serialize_ts((policy_row or {}).get("updated_at")),
        "policy_exclusion_count": int((policy_row or {}).get("exclusion_count") or 0),
        "label_count": int((labels_total_row or {}).get("label_count") or 0),
        "topic_count": int((labels_total_row or {}).get("topic_count") or 0),
        "deep_reflections_30d": [
            {"status": str(row.get("status") or ""), "count": int(row.get("count") or 0)}
            for row in reflection_rows
        ],
    }

    if include_conversation_metadata:
        turn_totals = await _safe_fetch_one(
            """
            SELECT
                COUNT(*) FILTER (WHERE created_at >= now() - interval '24 hours')::int AS turns_24h,
                COUNT(*) FILTER (WHERE created_at >= now() - interval '7 days')::int AS turns_7d,
                MAX(created_at) AS latest_turn_at
            FROM conversation_turns
            WHERE person_id = $1::uuid
            """,
            person_id,
        )
        role_breakdown = await _safe_fetch_all(
            """
            SELECT role, COUNT(*)::int AS count
            FROM conversation_turns
            WHERE person_id = $1::uuid
              AND created_at >= now() - interval '7 days'
            GROUP BY role
            ORDER BY count DESC, role ASC
            LIMIT 6
            """,
            person_id,
        )
        topic_rows = await _safe_fetch_all(
            """
            SELECT anchor, COUNT(*)::int AS moments, MAX(updated_at) AS last_seen
            FROM continuity_labels
            WHERE person_id = $1::uuid
            GROUP BY anchor
            ORDER BY moments DESC, anchor ASC
            LIMIT 6
            """,
            person_id,
        )
        snapshot["activity"] = {
            "turns_24h": int((turn_totals or {}).get("turns_24h") or 0),
            "turns_7d": int((turn_totals or {}).get("turns_7d") or 0),
            "latest_turn_at": _serialize_ts((turn_totals or {}).get("latest_turn_at")),
            "role_breakdown_7d": [
                {"role": str(row.get("role") or ""), "count": int(row.get("count") or 0)}
                for row in role_breakdown
            ],
            "top_topics": [
                {
                    "topic_key": str(row.get("anchor") or "")[:64],
                    "moments": int(row.get("moments") or 0),
                    "last_seen": _serialize_ts(row.get("last_seen")),
                }
                for row in topic_rows
            ],
        }
    else:
        snapshot["activity"] = {
            "conversation_metadata_shared": False,
        }

    failures_section: dict[str, Any] = {"available": False}
    if include_conversation_metadata and await _table_exists("request_logs"):
        user_col = "user_id" if await _table_has_column("request_logs", "user_id") else None
        if user_col is None and await _table_has_column("request_logs", "person_id"):
            user_col = "person_id"
        if user_col:
            failure_rows = await _safe_fetch_all(
                f"""
                SELECT path, status, COUNT(*)::int AS count, MAX(created_at) AS last_seen
                FROM request_logs
                WHERE {user_col}::text = $1
                  AND created_at >= now() - interval '7 days'
                  AND status >= 400
                GROUP BY path, status
                ORDER BY count DESC, path ASC
                LIMIT 8
                """,
                person_id,
            )
            failures_section = {
                "available": True,
                "recent_failures_7d": [
                    {
                        "path": str(row.get("path") or ""),
                        "status": int(row.get("status") or 0),
                        "count": int(row.get("count") or 0),
                        "last_seen": _serialize_ts(row.get("last_seen")),
                    }
                    for row in failure_rows
                ],
            }
    snapshot["request_failures"] = failures_section
    return snapshot


async def _refresh_expired_status(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return row
    if _is_report_active(row):
        return row
    status = str(row.get("status") or "").strip().lower()
    expires_at = row.get("expires_at")
    if status != "active" or not isinstance(expires_at, datetime) or expires_at > _utcnow():
        return row

    updated = await _safe_fetch_one(
        """
        UPDATE support_debug_reports
        SET status = 'expired', updated_at = now()
        WHERE id = $1::uuid
          AND status = 'active'
        RETURNING *
        """,
        str(row.get("id")),
    )
    report = updated or row
    try:
        await dbexec(
            """
            UPDATE support_debug_sessions
            SET status = 'expired',
                stopped_at = COALESCE(stopped_at, now()),
                updated_at = now()
            WHERE report_id = $1::uuid
              AND status = 'active'
            """,
            str(report.get("id") or ""),
        )
    except asyncpg.UndefinedTableError:
        pass
    return report


@router.post("/report")
async def create_support_report(request: Request, body: SupportReportCreateRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)

    issue_summary = _sanitize_text(body.issue_summary, max_len=1200)
    if not issue_summary or len(issue_summary) < 8:
        raise HTTPException(status_code=400, detail="issue_summary_too_short")
    repro_steps = _sanitize_text(body.repro_steps, max_len=3000)

    diagnostics_enabled = bool(body.diagnostics.enabled)
    include_conversation_metadata = diagnostics_enabled and bool(body.diagnostics.include_conversation_metadata)
    client_context = _sanitize_client_context(body.client_context)
    now = _utcnow()
    expires_at = now + timedelta(hours=_support_ttl_hours())

    diagnostics_snapshot = (
        await _build_diagnostics_snapshot(
            resolved_person_id,
            include_conversation_metadata=include_conversation_metadata,
        )
        if diagnostics_enabled
        else {
            "generated_at": now.isoformat(),
            "privacy_contract": {
                "journal_content_included": False,
                "conversation_text_included": False,
                "notes": "Diagnostics disabled by user.",
            },
            "activity": {"conversation_metadata_shared": False},
        }
    )

    consent_snapshot = {
        "diagnostics_enabled": diagnostics_enabled,
        "include_conversation_metadata": include_conversation_metadata,
        "agreed_at": now.isoformat(),
    }

    row: dict[str, Any] | None = None
    for _ in range(5):
        support_code = _generate_support_code()
        try:
            row = await q(
                """
                INSERT INTO support_debug_reports (
                    person_id,
                    support_code,
                    issue_summary,
                    repro_steps,
                    diagnostics_enabled,
                    include_conversation_metadata,
                    consent_snapshot,
                    client_context,
                    diagnostics_snapshot,
                    status,
                    expires_at,
                    created_at,
                    updated_at
                )
                VALUES (
                    $1::uuid,
                    $2,
                    $3,
                    $4,
                    $5,
                    $6,
                    $7::jsonb,
                    $8::jsonb,
                    $9::jsonb,
                    'active',
                    $10,
                    now(),
                    now()
                )
                RETURNING *
                """,
                resolved_person_id,
                support_code,
                issue_summary,
                repro_steps,
                diagnostics_enabled,
                include_conversation_metadata,
                json.dumps(consent_snapshot),
                json.dumps(client_context),
                json.dumps(diagnostics_snapshot),
                expires_at,
                one=True,
            )
            break
        except asyncpg.UniqueViolationError:
            continue
        except asyncpg.UndefinedTableError as exc:
            raise HTTPException(status_code=503, detail="support_schema_missing") from exc
    if not row:
        raise HTTPException(status_code=500, detail="support_code_generation_failed")
    asyncio.create_task(_notify_support(support_code, issue_summary, client_context))
    payload = _build_public_report_payload(row)
    payload["active_session"] = None
    return payload


@router.get("/report")
async def get_support_report(
    request: Request,
    person_id: str,
    support_code: str,
):
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    normalized_code = _normalize_support_code(support_code)
    if not normalized_code:
        raise HTTPException(status_code=400, detail="invalid_support_code")

    try:
        row = await _fetch_report_by_code(resolved_person_id, normalized_code)
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_schema_missing") from exc
    if not row:
        raise HTTPException(status_code=404, detail="support_report_not_found")

    row = await _refresh_expired_status(row)
    payload = _build_public_report_payload(row)
    latest_session = await _fetch_latest_session(str(row.get("id") or ""))
    payload["active_session"] = (
        _build_public_session_payload(latest_session)
        if latest_session and _is_session_active(latest_session)
        else None
    )
    return payload


@router.post("/report/revoke")
async def revoke_support_report(request: Request, body: SupportReportRevokeRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    normalized_code = _normalize_support_code(body.support_code)
    if not normalized_code:
        raise HTTPException(status_code=400, detail="invalid_support_code")

    try:
        row = await _fetch_report_by_code(resolved_person_id, normalized_code)
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_schema_missing") from exc
    if not row:
        raise HTTPException(status_code=404, detail="support_report_not_found")

    row = await _refresh_expired_status(row)
    status = str(row.get("status") or "").strip().lower()
    if status == "active":
        await dbexec(
            """
            UPDATE support_debug_reports
            SET status = 'revoked',
                revoked_at = now(),
                updated_at = now()
            WHERE id = $1::uuid
            """,
            str(row.get("id")),
        )
        try:
            await dbexec(
                """
                UPDATE support_debug_sessions
                SET status = 'revoked',
                    stopped_at = COALESCE(stopped_at, now()),
                    updated_at = now()
                WHERE report_id = $1::uuid
                  AND status = 'active'
                """,
                str(row.get("id")),
            )
        except asyncpg.UndefinedTableError:
            pass
        row = await q(
            "SELECT * FROM support_debug_reports WHERE id = $1::uuid",
            str(row.get("id")),
            one=True,
        ) or row
    payload = _build_public_report_payload(row)
    payload["active_session"] = None
    return payload


@router.post("/session/start")
async def start_support_session(request: Request, body: SupportSessionStartRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    normalized_code = _normalize_support_code(body.support_code)
    if not normalized_code:
        raise HTTPException(status_code=400, detail="invalid_support_code")

    try:
        report_row = await _fetch_report_by_code(resolved_person_id, normalized_code)
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_schema_missing") from exc
    if not report_row:
        raise HTTPException(status_code=404, detail="support_report_not_found")

    report_row = await _refresh_expired_status(report_row)
    if not _is_report_active(report_row):
        raise HTTPException(status_code=409, detail="support_report_not_active")

    report_id = str(report_row.get("id") or "")
    now = _utcnow()
    report_expires_at = report_row.get("expires_at")
    remaining_minutes = (
        int(max(1, (report_expires_at - now).total_seconds() // 60))
        if isinstance(report_expires_at, datetime)
        else _support_session_ttl_minutes()
    )
    requested_minutes = body.duration_minutes or _support_session_ttl_minutes()
    ttl_minutes = min(max(requested_minutes, 5), remaining_minutes, MAX_SUPPORT_SESSION_TTL_MINUTES)
    expires_at = now + timedelta(minutes=ttl_minutes)

    existing_session = await _safe_fetch_one(
        """
        SELECT *
        FROM support_debug_sessions
        WHERE report_id = $1::uuid
          AND status = 'active'
        ORDER BY started_at DESC
        LIMIT 1
        """,
        report_id,
    )
    if existing_session:
        existing_session = await _refresh_expired_session_status(existing_session)
        if _is_session_active(existing_session):
            payload = _build_public_session_payload(existing_session)
            payload["reused"] = True
            return payload

    try:
        session_row = await q(
            """
            INSERT INTO support_debug_sessions (
                report_id,
                person_id,
                support_code,
                status,
                started_at,
                expires_at,
                event_count,
                client_context,
                created_at,
                updated_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3,
                'active',
                now(),
                $4,
                0,
                $5::jsonb,
                now(),
                now()
            )
            RETURNING *
            """,
            report_id,
            resolved_person_id,
            normalized_code,
            expires_at,
            json.dumps(_sanitize_client_context(body.client_context)),
            one=True,
        )
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_session_schema_missing") from exc

    if not session_row:
        raise HTTPException(status_code=500, detail="support_session_creation_failed")
    payload = _build_public_session_payload(session_row)
    payload["reused"] = False
    return payload


@router.post("/session/event")
async def append_support_session_events(request: Request, body: SupportSessionEventRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    normalized_code = _normalize_support_code(body.support_code)
    if not normalized_code:
        raise HTTPException(status_code=400, detail="invalid_support_code")

    try:
        report_row = await _fetch_report_by_code(resolved_person_id, normalized_code)
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_schema_missing") from exc
    if not report_row:
        raise HTTPException(status_code=404, detail="support_report_not_found")

    report_row = await _refresh_expired_status(report_row)
    if not _is_report_active(report_row):
        raise HTTPException(status_code=409, detail="support_report_not_active")
    report_id = str(report_row.get("id") or "")

    try:
        session_row = await q(
            """
            SELECT *
            FROM support_debug_sessions
            WHERE id = $1::uuid
              AND person_id = $2::uuid
              AND support_code = $3
            LIMIT 1
            """,
            body.session_id,
            resolved_person_id,
            normalized_code,
            one=True,
        )
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_session_schema_missing") from exc
    except (asyncpg.DataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid_support_session_id") from exc
    if not session_row:
        raise HTTPException(status_code=404, detail="support_session_not_found")

    session_row = await _refresh_expired_session_status(session_row)
    if str(session_row.get("report_id") or "") != report_id:
        raise HTTPException(status_code=404, detail="support_session_not_found")
    if not _is_session_active(session_row):
        raise HTTPException(status_code=409, detail="support_session_not_active")

    existing_count = int(session_row.get("event_count") or 0)
    if existing_count >= MAX_TIMELINE_EVENTS_PER_SESSION:
        raise HTTPException(status_code=409, detail="support_session_event_limit_reached")
    if existing_count + len(body.events) > MAX_TIMELINE_EVENTS_PER_SESSION:
        raise HTTPException(status_code=409, detail="support_session_event_batch_exceeds_limit")

    accepted = 0
    latest_event_at: datetime | None = None
    for event in body.events:
        event_type = _normalize_event_label(event.type, max_len=24)
        if event_type not in ALLOWED_TIMELINE_EVENT_TYPES:
            raise HTTPException(status_code=400, detail=f"invalid_event_type:{event_type or 'unknown'}")

        event_name = _normalize_event_label(event.name, max_len=64) or event_type
        screen = _normalize_event_label(event.screen, max_len=64)
        route = _normalize_event_label(event.route, max_len=140, allow_slash=True)
        method = _normalize_event_label(event.method, max_len=12).upper()
        event_at = _parse_event_ts(event.ts)
        request_id = _sanitize_text(event.request_id, max_len=120)
        metadata = _sanitize_timeline_metadata(event.metadata)

        await dbexec(
            """
            INSERT INTO support_debug_events (
                session_id,
                report_id,
                person_id,
                support_code,
                event_type,
                event_name,
                event_seq,
                event_at,
                screen,
                route,
                http_method,
                http_status,
                request_id,
                latency_ms,
                payload,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4,
                $5,
                $6,
                $7,
                $8,
                $9,
                $10,
                $11,
                $12,
                $13,
                $14,
                $15::jsonb,
                now()
            )
            """,
            str(session_row.get("id") or ""),
            report_id,
            resolved_person_id,
            normalized_code,
            event_type,
            event_name,
            event.seq,
            event_at,
            screen or None,
            route or None,
            method or None,
            event.status,
            request_id,
            event.latency_ms,
            json.dumps(metadata),
        )
        accepted += 1
        if latest_event_at is None or event_at > latest_event_at:
            latest_event_at = event_at

    if accepted > 0:
        await dbexec(
            """
            UPDATE support_debug_sessions
            SET event_count = event_count + $2,
                last_event_at = CASE
                    WHEN last_event_at IS NULL OR last_event_at < $3 THEN $3
                    ELSE last_event_at
                END,
                updated_at = now()
            WHERE id = $1::uuid
            """,
            str(session_row.get("id") or ""),
            accepted,
            latest_event_at or _utcnow(),
        )
        session_row = await q(
            "SELECT * FROM support_debug_sessions WHERE id = $1::uuid",
            str(session_row.get("id") or ""),
            one=True,
        ) or session_row

    return {
        "session": _build_public_session_payload(session_row),
        "accepted": accepted,
    }


@router.post("/session/stop")
async def stop_support_session(request: Request, body: SupportSessionStopRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    normalized_code = _normalize_support_code(body.support_code)
    if not normalized_code:
        raise HTTPException(status_code=400, detail="invalid_support_code")

    try:
        session_row = await q(
            """
            SELECT *
            FROM support_debug_sessions
            WHERE id = $1::uuid
              AND person_id = $2::uuid
              AND support_code = $3
            LIMIT 1
            """,
            body.session_id,
            resolved_person_id,
            normalized_code,
            one=True,
        )
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_session_schema_missing") from exc
    except (asyncpg.DataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid_support_session_id") from exc
    if not session_row:
        raise HTTPException(status_code=404, detail="support_session_not_found")

    session_row = await _refresh_expired_session_status(session_row)
    if _is_session_active(session_row):
        await dbexec(
            """
            UPDATE support_debug_sessions
            SET status = 'stopped',
                stopped_at = now(),
                updated_at = now()
            WHERE id = $1::uuid
            """,
            str(session_row.get("id") or ""),
        )
        session_row = await q(
            "SELECT * FROM support_debug_sessions WHERE id = $1::uuid",
            str(session_row.get("id") or ""),
            one=True,
        ) or session_row

    return _build_public_session_payload(session_row)


@admin_router.get("/report/{support_code}")
async def get_support_report_for_operator(
    support_code: str,
    include_inactive: bool = False,
    include_timeline: bool = True,
):
    normalized_code = _normalize_support_code(support_code)
    if not normalized_code:
        raise HTTPException(status_code=400, detail="invalid_support_code")

    try:
        row = await q(
            """
            SELECT *
            FROM support_debug_reports
            WHERE support_code = $1
            LIMIT 1
            """,
            normalized_code,
            one=True,
        )
    except asyncpg.UndefinedTableError as exc:
        raise HTTPException(status_code=503, detail="support_schema_missing") from exc
    if not row:
        raise HTTPException(status_code=404, detail="support_report_not_found")

    row = await _refresh_expired_status(row)
    if not include_inactive and not _is_report_active(row):
        raise HTTPException(status_code=404, detail="support_report_not_active")

    person_id = str(row.get("person_id") or "")
    await report_data_access_event(
        action="support_lookup",
        where="api:GET /admin/support/report/{support_code}",
        subject_id=person_id or None,
        extra={
            "support_code": normalized_code,
            "status": str(row.get("status") or ""),
        },
    )

    payload = _build_public_report_payload(row)
    payload["person_id"] = person_id
    payload["access_contract"] = {
        "journal_content_included": False,
        "conversation_text_included": False,
        "requires_user_support_code": True,
    }
    if include_timeline:
        payload["debug_timeline"] = await _build_timeline_preview(str(row.get("id") or ""))
    return payload
