"""External monitoring and on-call alert sink wiring."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

import httpx

from sakhi.libs.security.observability_redaction import (
    redact_log_line,
    redact_observability_value,
)

try:  # pragma: no cover - optional dependency
    import sentry_sdk as _sentry_sdk  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _sentry_sdk = None


LOGGER = logging.getLogger(__name__)
_SENTRY_INITIALIZED = False


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "y", "on"}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _sanitize_extra(extra: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = redact_observability_value(dict(extra or {}), key_hint="extra")
    if isinstance(payload, dict):
        return payload
    return {"value": payload}


@dataclass(slots=True)
class MonitoringRuntime:
    enabled: bool = False
    service: str = "sakhi"
    environment: str = "development"
    release: str | None = None
    sentry_enabled: bool = False
    webhook_url: str | None = None
    webhook_bearer_token: str | None = None
    webhook_timeout_sec: float = 4.0
    dedupe_window_sec: int = 180
    auth_failure_threshold: int = 5
    auth_failure_window_sec: int = 300
    crash_loop_threshold: int = 5
    crash_loop_window_sec: int = 300
    data_access_spike_threshold: int = 8
    data_access_window_sec: int = 600
    last_emitted_at: dict[str, float] = field(default_factory=dict)
    burst_counters: dict[str, list[float]] = field(default_factory=dict)
    burst_alerted_at: dict[str, float] = field(default_factory=dict)


_RUNTIME = MonitoringRuntime()


def setup_monitoring(*, service: str, environment: str | None = None) -> MonitoringRuntime:
    """Initialize monitoring sinks from environment variables."""

    global _RUNTIME, _SENTRY_INITIALIZED

    env = (environment or os.getenv("SAKHI_ENVIRONMENT") or os.getenv("ENV") or "development").strip().lower()
    release = (os.getenv("SAKHI_RELEASE") or os.getenv("RELEASE") or "").strip() or None
    webhook_url = (os.getenv("SAKHI_ALERT_WEBHOOK_URL") or "").strip() or None
    webhook_bearer_token = (os.getenv("SAKHI_ALERT_WEBHOOK_BEARER_TOKEN") or "").strip() or None
    sentry_dsn = (os.getenv("SAKHI_SENTRY_DSN") or os.getenv("SENTRY_DSN") or "").strip() or None
    monitoring_enabled = _as_bool(os.getenv("SAKHI_MONITORING_ENABLED"), default=False)
    monitoring_enabled = monitoring_enabled or bool(webhook_url) or bool(sentry_dsn)

    timeout_raw = os.getenv("SAKHI_ALERT_WEBHOOK_TIMEOUT_SEC", "4")
    dedupe_raw = os.getenv("SAKHI_ALERT_DEDUPE_WINDOW_SEC", "180")
    auth_threshold_raw = os.getenv("SAKHI_ALERT_AUTH_FAILURE_THRESHOLD", "5")
    auth_window_raw = os.getenv("SAKHI_ALERT_AUTH_FAILURE_WINDOW_SEC", "300")
    crash_threshold_raw = os.getenv("SAKHI_ALERT_CRASH_LOOP_THRESHOLD", "5")
    crash_window_raw = os.getenv("SAKHI_ALERT_CRASH_LOOP_WINDOW_SEC", "300")
    data_threshold_raw = os.getenv("SAKHI_ALERT_DATA_ACCESS_SPIKE_THRESHOLD", "8")
    data_window_raw = os.getenv("SAKHI_ALERT_DATA_ACCESS_WINDOW_SEC", "600")
    try:
        webhook_timeout_sec = max(1.0, float(timeout_raw))
    except Exception:
        webhook_timeout_sec = 4.0
    try:
        dedupe_window_sec = max(30, int(dedupe_raw))
    except Exception:
        dedupe_window_sec = 180
    try:
        auth_failure_threshold = max(2, int(auth_threshold_raw))
    except Exception:
        auth_failure_threshold = 5
    try:
        auth_failure_window_sec = max(60, int(auth_window_raw))
    except Exception:
        auth_failure_window_sec = 300
    try:
        crash_loop_threshold = max(2, int(crash_threshold_raw))
    except Exception:
        crash_loop_threshold = 5
    try:
        crash_loop_window_sec = max(60, int(crash_window_raw))
    except Exception:
        crash_loop_window_sec = 300
    try:
        data_access_spike_threshold = max(2, int(data_threshold_raw))
    except Exception:
        data_access_spike_threshold = 8
    try:
        data_access_window_sec = max(60, int(data_window_raw))
    except Exception:
        data_access_window_sec = 600

    runtime = MonitoringRuntime(
        enabled=monitoring_enabled,
        service=service,
        environment=env,
        release=release,
        sentry_enabled=False,
        webhook_url=webhook_url,
        webhook_bearer_token=webhook_bearer_token,
        webhook_timeout_sec=webhook_timeout_sec,
        dedupe_window_sec=dedupe_window_sec,
        auth_failure_threshold=auth_failure_threshold,
        auth_failure_window_sec=auth_failure_window_sec,
        crash_loop_threshold=crash_loop_threshold,
        crash_loop_window_sec=crash_loop_window_sec,
        data_access_spike_threshold=data_access_spike_threshold,
        data_access_window_sec=data_access_window_sec,
    )

    if sentry_dsn:
        if _sentry_sdk is None:
            LOGGER.warning(
                "Monitoring configured with Sentry DSN, but sentry-sdk is not installed. "
                "Using webhook sink only."
            )
        else:
            if not _SENTRY_INITIALIZED:
                try:
                    traces_sample_rate = float(os.getenv("SAKHI_SENTRY_TRACES_SAMPLE_RATE", "0.0"))
                except Exception:
                    traces_sample_rate = 0.0
                _sentry_sdk.init(
                    dsn=sentry_dsn,
                    environment=env,
                    release=release,
                    traces_sample_rate=max(0.0, traces_sample_rate),
                    send_default_pii=False,
                )
                _SENTRY_INITIALIZED = True
            runtime.sentry_enabled = True

    _RUNTIME = runtime
    LOGGER.info(
        "Monitoring setup",
        extra={
            "event": "monitoring_setup",
            "enabled": runtime.enabled,
            "service": runtime.service,
            "environment": runtime.environment,
            "webhook_enabled": bool(runtime.webhook_url),
            "sentry_enabled": runtime.sentry_enabled,
            "auth_failure_threshold": runtime.auth_failure_threshold,
            "auth_failure_window_sec": runtime.auth_failure_window_sec,
            "crash_loop_threshold": runtime.crash_loop_threshold,
            "crash_loop_window_sec": runtime.crash_loop_window_sec,
            "data_access_spike_threshold": runtime.data_access_spike_threshold,
            "data_access_window_sec": runtime.data_access_window_sec,
        },
    )
    return runtime


def get_monitoring_runtime() -> MonitoringRuntime:
    return _RUNTIME


def _severity_to_sentry_level(severity: str) -> str:
    normalized = (severity or "error").strip().lower()
    if normalized in {"critical", "fatal"}:
        return "fatal"
    if normalized in {"warning", "warn"}:
        return "warning"
    if normalized in {"info", "notice"}:
        return "info"
    return "error"


def _should_emit(dedupe_key: str | None) -> bool:
    if not dedupe_key:
        return True

    runtime = get_monitoring_runtime()
    now = time.monotonic()
    previous = runtime.last_emitted_at.get(dedupe_key)
    if previous is not None and (now - previous) < runtime.dedupe_window_sec:
        return False

    runtime.last_emitted_at[dedupe_key] = now
    if len(runtime.last_emitted_at) > 2048:
        cutoff = now - (runtime.dedupe_window_sec * 2)
        for key, seen_at in list(runtime.last_emitted_at.items()):
            if seen_at < cutoff:
                runtime.last_emitted_at.pop(key, None)
    return True


def _track_burst(
    *,
    bucket: str,
    threshold: int,
    window_sec: int,
) -> tuple[int, bool]:
    runtime = get_monitoring_runtime()
    now = time.monotonic()

    points = runtime.burst_counters.get(bucket, [])
    if points:
        floor = now - window_sec
        points = [point for point in points if point >= floor]
    points.append(now)
    runtime.burst_counters[bucket] = points

    if len(runtime.burst_counters) > 2048:
        cutoff = now - max(window_sec, runtime.dedupe_window_sec) * 2
        for key, values in list(runtime.burst_counters.items()):
            if not values or max(values) < cutoff:
                runtime.burst_counters.pop(key, None)
                runtime.burst_alerted_at.pop(key, None)

    count = len(points)
    last_alerted_at = runtime.burst_alerted_at.get(bucket)
    threshold_hit = count >= threshold
    already_alerted = last_alerted_at is not None and (now - last_alerted_at) < window_sec
    triggered = threshold_hit and not already_alerted
    if triggered:
        runtime.burst_alerted_at[bucket] = now
    return count, triggered


def _build_payload(
    *,
    kind: str,
    severity: str,
    where: str,
    message: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = get_monitoring_runtime()
    safe_extra = _sanitize_extra(extra)
    return {
        "source": "sakhi",
        "kind": kind,
        "service": runtime.service,
        "environment": runtime.environment,
        "release": runtime.release,
        "severity": severity,
        "where": where,
        "message": redact_log_line(message)[:2000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra": safe_extra,
    }


async def _post_webhook(payload: Mapping[str, Any]) -> None:
    runtime = get_monitoring_runtime()
    if not runtime.webhook_url:
        return
    headers = {"Content-Type": "application/json"}
    if runtime.webhook_bearer_token:
        headers["Authorization"] = f"Bearer {runtime.webhook_bearer_token}"
    timeout = httpx.Timeout(runtime.webhook_timeout_sec)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(runtime.webhook_url, json=dict(payload), headers=headers)
        response.raise_for_status()


async def report_exception(
    exc: BaseException,
    *,
    where: str,
    severity: str = "critical",
    extra: Mapping[str, Any] | None = None,
    dedupe_key: str | None = None,
) -> bool:
    """Send unhandled exceptions to configured monitoring sinks."""

    runtime = get_monitoring_runtime()
    if not runtime.enabled:
        return False

    message = str(exc) or exc.__class__.__name__
    crash_count, crash_triggered = _track_burst(
        bucket=f"crash_loop:{where}:{exc.__class__.__name__}",
        threshold=runtime.crash_loop_threshold,
        window_sec=runtime.crash_loop_window_sec,
    )
    if crash_triggered:
        await report_message(
            message=f"crash_loop_detected where={where} exception_type={exc.__class__.__name__}",
            where=where,
            severity="critical",
            dedupe_key=f"crash_loop_detected:{where}:{exc.__class__.__name__}",
            extra={
                "where": where,
                "exception_type": exc.__class__.__name__,
                "event_count": crash_count,
                "window_sec": runtime.crash_loop_window_sec,
            },
        )

    dedupe = dedupe_key or f"{where}:{exc.__class__.__name__}:{_digest(message)}"
    if not _should_emit(dedupe):
        return False

    event_extra = dict(extra or {})
    event_extra.setdefault("exception_type", exc.__class__.__name__)
    event_extra.setdefault("exception_message", message[:500])
    safe_extra = _sanitize_extra(event_extra)
    safe_message = redact_log_line(message)
    payload = _build_payload(
        kind="exception",
        severity=severity,
        where=where,
        message=safe_message,
        extra=safe_extra,
    )

    sent = False
    if runtime.sentry_enabled and _sentry_sdk is not None:
        try:  # pragma: no cover - tiny sentry wrapper
            with _sentry_sdk.push_scope() as scope:
                scope.set_tag("service", runtime.service)
                scope.set_tag("environment", runtime.environment)
                scope.set_tag("where", where)
                scope.level = _severity_to_sentry_level(severity)
                for key, value in safe_extra.items():
                    scope.set_extra(str(key), value)
                _sentry_sdk.capture_exception(exc)
            sent = True
        except Exception as sentry_exc:
            LOGGER.warning("Sentry exception capture failed: %s", sentry_exc)

    if runtime.webhook_url:
        try:
            await _post_webhook(payload)
            sent = True
        except Exception as webhook_exc:
            LOGGER.warning("Alert webhook delivery failed: %s", webhook_exc)

    return sent


async def report_auth_failure(
    *,
    where: str,
    reason: str,
    subject_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> bool:
    """Emit alert only when auth failures cross burst threshold."""

    runtime = get_monitoring_runtime()
    if not runtime.enabled:
        return False

    count, triggered = _track_burst(
        bucket=f"auth_failure:{where}:{reason}",
        threshold=runtime.auth_failure_threshold,
        window_sec=runtime.auth_failure_window_sec,
    )
    if not triggered:
        return False

    details = dict(extra or {})
    details.update(
        {
            "reason": reason,
            "event_count": count,
            "window_sec": runtime.auth_failure_window_sec,
            "subject_id": subject_id,
        }
    )
    return await report_message(
        message=f"repeated_auth_failures_detected reason={reason}",
        where=where,
        severity="critical",
        dedupe_key=f"repeated_auth_failures:{where}:{reason}",
        extra=details,
    )


async def report_breakglass_event(
    *,
    granted: bool,
    where: str,
    operator_id: str | None,
    approval_ref: str | None,
    reason: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> bool:
    """Emit standardized break-glass allow/deny alert events."""

    status_label = "granted" if granted else "denied"
    details = dict(extra or {})
    details.update(
        {
            "status": status_label,
            "operator_id": operator_id,
            "approval_ref": approval_ref,
            "reason": reason,
        }
    )
    return await report_message(
        message=f"operator_access_{status_label}",
        where=where,
        severity="warning" if granted else "critical",
        dedupe_key=f"operator_access:{status_label}:{where}:{operator_id}:{approval_ref}:{reason}",
        extra=details,
    )


async def report_data_access_event(
    *,
    action: str,
    where: str,
    subject_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> bool:
    """Emit alert when export/delete operations spike unexpectedly."""

    runtime = get_monitoring_runtime()
    if not runtime.enabled:
        return False

    normalized = (action or "").strip().lower()
    if normalized not in {"export", "delete"}:
        return False

    count, triggered = _track_burst(
        bucket=f"data_access:{normalized}:{where}",
        threshold=runtime.data_access_spike_threshold,
        window_sec=runtime.data_access_window_sec,
    )
    if not triggered:
        return False

    details = dict(extra or {})
    details.update(
        {
            "action": normalized,
            "event_count": count,
            "window_sec": runtime.data_access_window_sec,
            "subject_id": subject_id,
        }
    )
    return await report_message(
        message=f"data_access_spike_detected action={normalized}",
        where=where,
        severity="critical",
        dedupe_key=f"data_access_spike:{normalized}:{where}",
        extra=details,
    )


async def report_message(
    *,
    message: str,
    where: str,
    severity: str = "warning",
    extra: Mapping[str, Any] | None = None,
    dedupe_key: str | None = None,
) -> bool:
    """Send a non-exception alert to configured monitoring sinks."""

    runtime = get_monitoring_runtime()
    if not runtime.enabled:
        return False

    safe_message = redact_log_line(message)
    dedupe = dedupe_key or f"{where}:{severity}:{_digest(safe_message)}"
    if not _should_emit(dedupe):
        return False

    safe_extra = _sanitize_extra(extra)
    payload = _build_payload(
        kind="event",
        severity=severity,
        where=where,
        message=safe_message,
        extra=safe_extra,
    )

    sent = False
    if runtime.sentry_enabled and _sentry_sdk is not None:
        try:  # pragma: no cover - tiny sentry wrapper
            with _sentry_sdk.push_scope() as scope:
                scope.set_tag("service", runtime.service)
                scope.set_tag("environment", runtime.environment)
                scope.set_tag("where", where)
                scope.level = _severity_to_sentry_level(severity)
                for key, value in safe_extra.items():
                    scope.set_extra(str(key), value)
                _sentry_sdk.capture_message(safe_message[:300], level=_severity_to_sentry_level(severity))
            sent = True
        except Exception as sentry_exc:
            LOGGER.warning("Sentry message capture failed: %s", sentry_exc)

    if runtime.webhook_url:
        try:
            await _post_webhook(payload)
            sent = True
        except Exception as webhook_exc:
            LOGGER.warning("Alert webhook delivery failed: %s", webhook_exc)

    return sent


def report_exception_sync(
    exc: BaseException,
    *,
    where: str,
    severity: str = "critical",
    extra: Mapping[str, Any] | None = None,
    dedupe_key: str | None = None,
) -> None:
    """Sync wrapper for worker/runtime code that cannot await."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(
            report_exception(
                exc,
                where=where,
                severity=severity,
                extra=extra,
                dedupe_key=dedupe_key,
            )
        )
        return
    loop.create_task(
        report_exception(
            exc,
            where=where,
            severity=severity,
            extra=extra,
            dedupe_key=dedupe_key,
        )
    )


__all__ = [
    "MonitoringRuntime",
    "get_monitoring_runtime",
    "report_exception",
    "report_exception_sync",
    "report_message",
    "setup_monitoring",
]
