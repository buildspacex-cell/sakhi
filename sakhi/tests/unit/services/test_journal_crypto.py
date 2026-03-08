from __future__ import annotations

import pytest

from sakhi.libs.security.journal_crypto import (
    build_journal_storage_payload,
    decrypt_journal_text,
    encrypt_journal_text,
    resolve_journal_text,
)


def test_encrypt_decrypt_roundtrip_same_user(monkeypatch):
    monkeypatch.setenv("SAKHI_JOURNAL_MASTER_KEY", "unit-test-master-key-1234567890-abcdef")
    user_id = "user-123"
    text = "private journal text"

    payload = encrypt_journal_text(user_id, text)

    assert isinstance(payload, bytes)
    assert decrypt_journal_text(user_id, payload) == text


def test_decrypt_fails_for_different_user(monkeypatch):
    monkeypatch.setenv("SAKHI_JOURNAL_MASTER_KEY", "unit-test-master-key-1234567890-abcdef")
    payload = encrypt_journal_text("user-a", "sensitive note")

    with pytest.raises(Exception):
        decrypt_journal_text("user-b", payload)


def test_storage_payload_encrypted_only_default(monkeypatch):
    monkeypatch.setenv("SAKHI_JOURNAL_MASTER_KEY", "unit-test-master-key-1234567890-abcdef")
    monkeypatch.delenv("SAKHI_JOURNAL_WRITE_MODE", raising=False)

    payload = build_journal_storage_payload("user-1", "hello")

    assert payload.content is None
    assert payload.raw is None
    assert payload.cleaned is None
    assert isinstance(payload.raw_encrypted, bytes)


def test_storage_payload_dual_write(monkeypatch):
    monkeypatch.setenv("SAKHI_JOURNAL_MASTER_KEY", "unit-test-master-key-1234567890-abcdef")
    monkeypatch.setenv("SAKHI_JOURNAL_WRITE_MODE", "dual_write")

    payload = build_journal_storage_payload("user-1", "hello")

    assert payload.content == "hello"
    assert payload.raw == "hello"
    assert payload.cleaned == "hello"
    assert isinstance(payload.raw_encrypted, bytes)


def test_missing_master_key_fails_closed(monkeypatch):
    monkeypatch.delenv("SAKHI_JOURNAL_MASTER_KEY", raising=False)

    with pytest.raises(RuntimeError):
        build_journal_storage_payload("user-1", "hello")


def test_encrypted_only_missing_payload_raises(monkeypatch):
    monkeypatch.setenv("SAKHI_JOURNAL_MASTER_KEY", "unit-test-master-key-1234567890-abcdef")
    monkeypatch.setenv("SAKHI_JOURNAL_WRITE_MODE", "encrypted_only")

    with pytest.raises(ValueError):
        resolve_journal_text({"content": None, "raw_encrypted": None}, user_id="user-1")


def test_dual_write_decrypt_failure_falls_back_empty(monkeypatch):
    monkeypatch.setenv("SAKHI_JOURNAL_MASTER_KEY", "unit-test-master-key-1234567890-abcdef")
    monkeypatch.setenv("SAKHI_JOURNAL_WRITE_MODE", "dual_write")

    text = resolve_journal_text({"content": None, "raw_encrypted": b"invalid"}, user_id="user-1")
    assert text == ""
