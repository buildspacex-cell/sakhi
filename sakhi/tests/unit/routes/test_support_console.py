from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from sakhi.apps.api.routes import support


def test_normalize_support_code_uppercases_and_applies_prefix():
    assert support._normalize_support_code("skh-ab12-cd34-ef56") == "SKH-AB12-CD34-EF56"
    assert support._normalize_support_code("ab12cd34") == "SKH-AB12CD34"
    assert support._normalize_support_code("  ") == ""


def test_sanitize_client_context_limits_nesting_and_lengths():
    payload = {
        "appVersion": "2026.03.10",
        "platform": "ios",
        "nested": {
            "key": "x" * 400,
            "another": {"tooDeep": {"value": "ignored"}},
        },
        "list": list(range(0, 40)),
    }
    sanitized = support._sanitize_client_context(payload)

    assert sanitized["appVersion"] == "2026.03.10"
    assert sanitized["platform"] == "ios"
    assert isinstance(sanitized["nested"]["key"], str)
    assert len(sanitized["nested"]["key"]) <= support.MAX_STRING_LEN
    assert len(sanitized["list"]) == support.MAX_LIST_ITEMS


def test_is_report_active_respects_status_and_expiry():
    now = datetime.now(timezone.utc)
    active_row = {"status": "active", "expires_at": now + timedelta(hours=2)}
    expired_row = {"status": "active", "expires_at": now - timedelta(minutes=1)}
    revoked_row = {"status": "revoked", "expires_at": now + timedelta(hours=2)}

    assert support._is_report_active(active_row, now=now) is True
    assert support._is_report_active(expired_row, now=now) is False
    assert support._is_report_active(revoked_row, now=now) is False


def test_normalize_event_label_strips_unsafe_characters():
    assert support._normalize_event_label("Send Message!!!", max_len=24) == "sendmessage"
    assert support._normalize_event_label("/v2/turn?user=123", max_len=64, allow_slash=True) == "/v2/turnuser123"


def test_sanitize_timeline_metadata_redacts_sensitive_payload():
    payload = support._sanitize_timeline_metadata(
        {
            "screen": "chat",
            "message_preview": "I am exhausted after work",
            "token": "abc123",
        }
    )
    assert payload["screen"] == "chat"
    assert str(payload["message_preview"]).startswith("[REDACTED")
    assert str(payload["token"]).startswith("[REDACTED")


def test_build_public_report_payload_keeps_metadata_shape():
    now = datetime.now(timezone.utc)
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "support_code": "SKH-ABCD-EF12-3456",
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "expires_at": now + timedelta(hours=12),
        "revoked_at": None,
        "resolved_at": None,
        "issue_summary": "Chat froze after sending message.",
        "repro_steps": "Open chat -> send message -> spinner stays.",
        "diagnostics_enabled": True,
        "include_conversation_metadata": True,
        "client_context": {"platform": "ios"},
        "diagnostics_snapshot": {"activity": {"turns_24h": 4}},
    }

    payload = support._build_public_report_payload(row)

    assert payload["support_code"] == "SKH-ABCD-EF12-3456"
    assert payload["status"] == "active"
    assert payload["diagnostics"]["enabled"] is True
    assert payload["diagnostics"]["include_conversation_metadata"] is True
    assert payload["bundle_preview"]["activity"]["turns_24h"] == 4
    assert payload["client_context"]["platform"] == "ios"


@pytest.mark.asyncio
async def test_create_support_report_respects_opt_out_diagnostics(monkeypatch: pytest.MonkeyPatch):
    now = datetime.now(timezone.utc)
    expected_person = "a1b2c3d4-1111-4000-8000-000000000001"

    async def _fake_resolve_person(_request, _person_id):
        return expected_person, "User", "a1b2"

    async def _fake_q(_sql, *args, one=False):
        assert one is True
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "support_code": args[1],
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "expires_at": args[9],
            "revoked_at": None,
            "resolved_at": None,
            "issue_summary": args[2],
            "repro_steps": args[3],
            "diagnostics_enabled": args[4],
            "include_conversation_metadata": args[5],
            "client_context": args[7],
            "diagnostics_snapshot": args[8],
        }

    monkeypatch.setattr(support, "resolve_person", _fake_resolve_person)
    monkeypatch.setattr(support, "q", _fake_q)

    request_body = support.SupportReportCreateRequest(
        person_id=expected_person,
        issue_summary="App stuck on loading when opening reflection.",
        repro_steps="Open app -> reflection -> spinner remains",
        diagnostics={"enabled": False, "include_conversation_metadata": True},
        client_context={"platform": "ios"},
    )

    payload = await support.create_support_report(object(), request_body)

    assert payload["support_code"].startswith("SKH-")
    assert payload["diagnostics"]["enabled"] is False
    assert payload["diagnostics"]["include_conversation_metadata"] is False
    assert payload["bundle_preview"]["privacy_contract"]["journal_content_included"] is False


@pytest.mark.asyncio
async def test_operator_lookup_rejects_inactive_when_not_overridden(monkeypatch: pytest.MonkeyPatch):
    now = datetime.now(timezone.utc)
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "person_id": "a1b2c3d4-1111-4000-8000-000000000001",
        "support_code": "SKH-AAAA-BBBB-CCCC",
        "status": "revoked",
        "created_at": now,
        "updated_at": now,
        "expires_at": now + timedelta(hours=1),
        "revoked_at": now,
        "resolved_at": None,
        "issue_summary": "Issue",
        "repro_steps": "",
        "diagnostics_enabled": True,
        "include_conversation_metadata": False,
        "client_context": {},
        "diagnostics_snapshot": {},
    }

    async def _fake_q(_sql, *_args, one=False):
        assert one is True
        return row

    async def _noop_refresh(value):
        return value

    async def _noop_report_data_access_event(**_kwargs):
        return False

    monkeypatch.setattr(support, "q", _fake_q)
    monkeypatch.setattr(support, "_refresh_expired_status", _noop_refresh)
    monkeypatch.setattr(support, "report_data_access_event", _noop_report_data_access_event)

    with pytest.raises(HTTPException) as exc_info:
        await support.get_support_report_for_operator("SKH-AAAA-BBBB-CCCC")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_start_support_session_reuses_active_session(monkeypatch: pytest.MonkeyPatch):
    now = datetime.now(timezone.utc)
    person_id = "a1b2c3d4-1111-4000-8000-000000000001"
    report = {
        "id": "11111111-1111-1111-1111-111111111111",
        "status": "active",
        "expires_at": now + timedelta(hours=1),
    }
    session = {
        "id": "22222222-2222-2222-2222-222222222222",
        "support_code": "SKH-AAAA-BBBB-CCCC",
        "status": "active",
        "started_at": now,
        "last_event_at": now,
        "stopped_at": None,
        "expires_at": now + timedelta(minutes=30),
        "event_count": 4,
        "client_context": {},
    }

    async def _fake_resolve_person(_request, _person_id):
        return person_id, "User", "a1b2"

    async def _fake_fetch_report(_person_id, _support_code):
        return report

    async def _fake_refresh(value):
        return value

    async def _fake_safe_fetch_one(sql, *_args):
        if "FROM support_debug_sessions" in sql:
            return session
        return None

    monkeypatch.setattr(support, "resolve_person", _fake_resolve_person)
    monkeypatch.setattr(support, "_fetch_report_by_code", _fake_fetch_report)
    monkeypatch.setattr(support, "_refresh_expired_status", _fake_refresh)
    monkeypatch.setattr(support, "_refresh_expired_session_status", _fake_refresh)
    monkeypatch.setattr(support, "_safe_fetch_one", _fake_safe_fetch_one)

    body = support.SupportSessionStartRequest(
        person_id=person_id,
        support_code="SKH-AAAA-BBBB-CCCC",
        duration_minutes=30,
        client_context={"platform": "ios"},
    )
    payload = await support.start_support_session(object(), body)

    assert payload["session_id"] == session["id"]
    assert payload["reused"] is True
    assert payload["status"] == "active"


@pytest.mark.asyncio
async def test_append_support_session_events_rejects_invalid_type(monkeypatch: pytest.MonkeyPatch):
    now = datetime.now(timezone.utc)
    person_id = "a1b2c3d4-1111-4000-8000-000000000001"
    report = {
        "id": "11111111-1111-1111-1111-111111111111",
        "status": "active",
        "expires_at": now + timedelta(hours=1),
    }
    session_row = {
        "id": "22222222-2222-2222-2222-222222222222",
        "report_id": report["id"],
        "status": "active",
        "expires_at": now + timedelta(minutes=10),
        "event_count": 0,
    }

    async def _fake_resolve_person(_request, _person_id):
        return person_id, "User", "a1b2"

    async def _fake_fetch_report(_person_id, _support_code):
        return report

    async def _fake_refresh(value):
        return value

    async def _fake_q(_sql, *_args, one=False):
        assert one is True
        return session_row

    monkeypatch.setattr(support, "resolve_person", _fake_resolve_person)
    monkeypatch.setattr(support, "_fetch_report_by_code", _fake_fetch_report)
    monkeypatch.setattr(support, "_refresh_expired_status", _fake_refresh)
    monkeypatch.setattr(support, "_refresh_expired_session_status", _fake_refresh)
    monkeypatch.setattr(support, "q", _fake_q)

    body = support.SupportSessionEventRequest(
        person_id=person_id,
        support_code="SKH-AAAA-BBBB-CCCC",
        session_id=session_row["id"],
        events=[
            support.SupportTimelineEvent(
                type="custom_event",
                name="unexpected_event",
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        await support.append_support_session_events(object(), body)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_append_support_session_events_accepts_safe_batch(monkeypatch: pytest.MonkeyPatch):
    now = datetime.now(timezone.utc)
    person_id = "a1b2c3d4-1111-4000-8000-000000000001"
    report = {
        "id": "11111111-1111-1111-1111-111111111111",
        "status": "active",
        "expires_at": now + timedelta(hours=1),
    }
    initial_session = {
        "id": "22222222-2222-2222-2222-222222222222",
        "report_id": report["id"],
        "support_code": "SKH-AAAA-BBBB-CCCC",
        "status": "active",
        "started_at": now,
        "last_event_at": None,
        "stopped_at": None,
        "expires_at": now + timedelta(minutes=30),
        "event_count": 0,
        "client_context": {},
    }
    updated_session = {
        **initial_session,
        "event_count": 1,
        "last_event_at": now,
    }
    inserted: list[tuple] = []

    async def _fake_resolve_person(_request, _person_id):
        return person_id, "User", "a1b2"

    async def _fake_fetch_report(_person_id, _support_code):
        return report

    async def _fake_refresh(value):
        return value

    async def _fake_q(sql, *_args, one=False):
        if "FROM support_debug_sessions" in sql and "LIMIT 1" in sql:
            assert one is True
            return initial_session
        if "SELECT * FROM support_debug_sessions WHERE id" in sql:
            assert one is True
            return updated_session
        raise AssertionError(f"Unexpected SQL: {sql}")

    async def _fake_dbexec(sql, *args):
        if "INSERT INTO support_debug_events" in sql:
            inserted.append(args)
        return "OK"

    monkeypatch.setattr(support, "resolve_person", _fake_resolve_person)
    monkeypatch.setattr(support, "_fetch_report_by_code", _fake_fetch_report)
    monkeypatch.setattr(support, "_refresh_expired_status", _fake_refresh)
    monkeypatch.setattr(support, "_refresh_expired_session_status", _fake_refresh)
    monkeypatch.setattr(support, "q", _fake_q)
    monkeypatch.setattr(support, "dbexec", _fake_dbexec)

    body = support.SupportSessionEventRequest(
        person_id=person_id,
        support_code="SKH-AAAA-BBBB-CCCC",
        session_id=initial_session["id"],
        events=[
            support.SupportTimelineEvent(
                type="action",
                name="send_message_pressed",
                screen="chat",
                metadata={"message_preview": "this should be redacted"},
            )
        ],
    )
    payload = await support.append_support_session_events(object(), body)

    assert payload["accepted"] == 1
    assert payload["session"]["event_count"] == 1
    assert len(inserted) == 1
