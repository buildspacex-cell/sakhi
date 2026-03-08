from __future__ import annotations

from typing import Any

import pytest

from sakhi.apps.api.core import monitoring


@pytest.mark.asyncio
async def test_report_exception_posts_webhook_payload(monkeypatch):
    monkeypatch.setenv("SAKHI_MONITORING_ENABLED", "1")
    monkeypatch.setenv("SAKHI_ALERT_WEBHOOK_URL", "https://alerts.example.com/hooks/sakhi")

    captured: list[dict[str, Any]] = []

    async def _fake_post(payload):
        captured.append(dict(payload))

    monkeypatch.setattr(monitoring, "_post_webhook", _fake_post)
    monitoring.setup_monitoring(service="sakhi-api", environment="test")

    result = await monitoring.report_exception(
        RuntimeError("upstream timeout"),
        where="api:POST /v2/turn",
        severity="critical",
        extra={"request_id": "req-123"},
    )

    assert result is True
    assert len(captured) == 1
    payload = captured[0]
    assert payload["service"] == "sakhi-api"
    assert payload["environment"] == "test"
    assert payload["kind"] == "exception"
    assert payload["severity"] == "critical"
    assert payload["where"] == "api:POST /v2/turn"
    assert payload["extra"]["request_id"] == "req-123"
    assert payload["extra"]["exception_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_report_exception_dedupes(monkeypatch):
    monkeypatch.setenv("SAKHI_MONITORING_ENABLED", "1")
    monkeypatch.setenv("SAKHI_ALERT_WEBHOOK_URL", "https://alerts.example.com/hooks/sakhi")
    monkeypatch.setenv("SAKHI_ALERT_DEDUPE_WINDOW_SEC", "180")

    call_count = 0

    async def _fake_post(_payload):
        nonlocal call_count
        call_count += 1

    monkeypatch.setattr(monitoring, "_post_webhook", _fake_post)
    monitoring.setup_monitoring(service="sakhi-api", environment="test")

    first = await monitoring.report_exception(
        ValueError("db down"),
        where="api:GET /health",
        dedupe_key="health-db-down",
    )
    second = await monitoring.report_exception(
        ValueError("db down"),
        where="api:GET /health",
        dedupe_key="health-db-down",
    )

    assert first is True
    assert second is False
    assert call_count == 1


@pytest.mark.asyncio
async def test_report_message_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("SAKHI_MONITORING_ENABLED", raising=False)
    monkeypatch.delenv("SAKHI_ALERT_WEBHOOK_URL", raising=False)
    monitoring.setup_monitoring(service="sakhi-api", environment="test")

    called = False

    async def _fake_post(_payload):
        nonlocal called
        called = True

    monkeypatch.setattr(monitoring, "_post_webhook", _fake_post)
    result = await monitoring.report_message(message="hello", where="unit:test")

    assert result is False
    assert called is False


def test_report_exception_sync_runs_without_loop(monkeypatch):
    monkeypatch.setenv("SAKHI_MONITORING_ENABLED", "1")
    monkeypatch.setenv("SAKHI_ALERT_WEBHOOK_URL", "https://alerts.example.com/hooks/sakhi")
    monitoring.setup_monitoring(service="sakhi-worker", environment="test")

    captured: list[dict[str, Any]] = []

    async def _fake_report_exception(exc, *, where, severity="critical", extra=None, dedupe_key=None):
        captured.append(
            {
                "exc": str(exc),
                "where": where,
                "severity": severity,
                "extra": extra,
                "dedupe_key": dedupe_key,
            }
        )
        return True

    monkeypatch.setattr(monitoring, "report_exception", _fake_report_exception)
    monitoring.report_exception_sync(RuntimeError("worker failed"), where="worker:main", severity="critical")

    assert captured
    assert captured[0]["where"] == "worker:main"
    assert captured[0]["severity"] == "critical"
