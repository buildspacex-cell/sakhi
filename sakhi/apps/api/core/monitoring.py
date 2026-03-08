"""External monitoring and on-call alert sink wiring."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

import httpx

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
    last_emitted_at: dict[str, float] = field(default_factory=dict)


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
    try:
        webhook_timeout_sec = max(1.0, float(timeout_raw))
    except Exception:
        webhook_timeout_sec = 4.0
    try:
        dedupe_window_sec = max(30, int(dedupe_raw))
    except Exception:
        dedupe_window_sec = 180

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


def _build_payload(
    *,
    kind: str,
    severity: str,
    where: str,
    message: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = get_monitoring_runtime()
    return {
        "source": "sakhi",
        "kind": kind,
        "service": runtime.service,
        "environment": runtime.environment,
        "release": runtime.release,
        "severity": severity,
        "where": where,
        "message": message[:2000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra": dict(extra or {}),
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
    dedupe = dedupe_key or f"{where}:{exc.__class__.__name__}:{message[:120]}"
    if not _should_emit(dedupe):
        return False

    event_extra = dict(extra or {})
    event_extra.setdefault("exception_type", exc.__class__.__name__)
    event_extra.setdefault("exception_message", message[:500])
    payload = _build_payload(
        kind="exception",
        severity=severity,
        where=where,
        message=message,
        extra=event_extra,
    )

    sent = False
    if runtime.sentry_enabled and _sentry_sdk is not None:
        try:  # pragma: no cover - tiny sentry wrapper
            with _sentry_sdk.push_scope() as scope:
                scope.set_tag("service", runtime.service)
                scope.set_tag("environment", runtime.environment)
                scope.set_tag("where", where)
                scope.level = _severity_to_sentry_level(severity)
                for key, value in event_extra.items():
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

    dedupe = dedupe_key or f"{where}:{severity}:{message[:160]}"
    if not _should_emit(dedupe):
        return False

    payload = _build_payload(
        kind="event",
        severity=severity,
        where=where,
        message=message,
        extra=extra,
    )

    sent = False
    if runtime.sentry_enabled and _sentry_sdk is not None:
        try:  # pragma: no cover - tiny sentry wrapper
            with _sentry_sdk.push_scope() as scope:
                scope.set_tag("service", runtime.service)
                scope.set_tag("environment", runtime.environment)
                scope.set_tag("where", where)
                scope.level = _severity_to_sentry_level(severity)
                for key, value in dict(extra or {}).items():
                    scope.set_extra(str(key), value)
                _sentry_sdk.capture_message(message[:300], level=_severity_to_sentry_level(severity))
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
