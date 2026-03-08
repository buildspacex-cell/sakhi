from __future__ import annotations

from sakhi.libs.security.observability_redaction import (
    redact_log_line,
    redact_observability_value,
)


def test_redact_observability_value_masks_sensitive_keys():
    payload = {
        "person_id": "a1b2c3d4-1111-4000-8000-000000000001",
        "text": "I had a hard day and feel exhausted",
        "content": {"nested": "long private journal content"},
        "headers": {
            "authorization": "Bearer super-secret-token",
        },
        "meta": {"status": "ok"},
    }

    redacted = redact_observability_value(payload)

    assert redacted["person_id"] == payload["person_id"]
    assert str(redacted["text"]).startswith("[REDACTED")
    assert str(redacted["content"]).startswith("[REDACTED")
    assert str(redacted["headers"]["authorization"]).startswith("[REDACTED")
    assert redacted["meta"]["status"] == "ok"


def test_redact_log_line_masks_inline_sensitive_assignments():
    line = "morning_presence person_id=abc text=I am overwhelmed today"
    redacted = redact_log_line(line)

    assert "overwhelmed" not in redacted
    assert "text=[REDACTED" in redacted


def test_redact_observability_value_masks_tokens_in_non_sensitive_strings():
    line = "Authorization: Bearer super-secret-token"
    redacted = redact_observability_value(line, key_hint="notes")

    assert "super-secret-token" not in str(redacted)
