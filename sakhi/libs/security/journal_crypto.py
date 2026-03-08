"""Per-user journal encryption helpers and write-mode policy."""

from __future__ import annotations

import hmac
import logging
import os
import secrets
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_JOURNAL_MASTER_KEY_ENV = "SAKHI_JOURNAL_MASTER_KEY"
_NONCE_SIZE = 12
_PAYLOAD_PREFIX = b"SJK1"
_AAD_PREFIX = "sakhi-journal-v1"
_WRITE_MODE_ENV = "SAKHI_JOURNAL_WRITE_MODE"
_WRITE_MODE_DUAL = "dual_write"
_WRITE_MODE_ENCRYPTED_ONLY = "encrypted_only"
_MIN_MASTER_KEY_LEN = 32

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class JournalStoragePayload:
    """Computed storage fields for journal row inserts."""

    content: str | None
    raw: str | None
    cleaned: str | None
    raw_encrypted: bytes


def _resolve_master_key() -> bytes:
    raw_master = str(os.getenv(_JOURNAL_MASTER_KEY_ENV) or "").strip()
    if not raw_master:
        raise RuntimeError(
            "Missing required env var: SAKHI_JOURNAL_MASTER_KEY. "
            "Journal encryption is fail-closed in this build."
        )
    if len(raw_master) < _MIN_MASTER_KEY_LEN:
        raise RuntimeError(
            "SAKHI_JOURNAL_MASTER_KEY must be at least 32 characters "
            "for production-grade journal encryption."
        )
    return sha256(raw_master.encode("utf-8")).digest()


def _derive_user_key(user_id: str) -> bytes:
    normalized_user = str(user_id or "").strip()
    if not normalized_user:
        raise ValueError("user_id is required for journal encryption")
    master_key = _resolve_master_key()
    return hmac.new(master_key, normalized_user.encode("utf-8"), sha256).digest()


def journal_write_mode() -> str:
    mode = str(os.getenv(_WRITE_MODE_ENV, _WRITE_MODE_ENCRYPTED_ONLY)).strip().lower()
    if mode == _WRITE_MODE_DUAL:
        return _WRITE_MODE_DUAL
    return _WRITE_MODE_ENCRYPTED_ONLY


def journal_plaintext_enabled() -> bool:
    return journal_write_mode() == _WRITE_MODE_DUAL


def encrypt_journal_text(user_id: str, text: str) -> bytes:
    plaintext = str(text or "")
    nonce = secrets.token_bytes(_NONCE_SIZE)
    aad = f"{_AAD_PREFIX}:{user_id}".encode("utf-8")
    aes = AESGCM(_derive_user_key(user_id))
    ciphertext = aes.encrypt(nonce, plaintext.encode("utf-8"), associated_data=aad)
    return _PAYLOAD_PREFIX + nonce + ciphertext


def decrypt_journal_text(user_id: str, payload: bytes | memoryview | bytearray | None) -> str:
    if payload is None:
        raise ValueError("Missing encrypted journal payload")
    raw = bytes(payload)
    if not raw.startswith(_PAYLOAD_PREFIX):
        raise ValueError("Unknown journal encryption payload version")
    body = raw[len(_PAYLOAD_PREFIX) :]
    if len(body) <= _NONCE_SIZE:
        raise ValueError("Encrypted journal payload is malformed")
    nonce, ciphertext = body[:_NONCE_SIZE], body[_NONCE_SIZE:]
    aad = f"{_AAD_PREFIX}:{user_id}".encode("utf-8")
    aes = AESGCM(_derive_user_key(user_id))
    plaintext = aes.decrypt(nonce, ciphertext, associated_data=aad)
    return plaintext.decode("utf-8")


def build_journal_storage_payload(user_id: str, text: str | None) -> JournalStoragePayload:
    normalized = str(text or "")
    encrypted = encrypt_journal_text(user_id, normalized)
    if journal_plaintext_enabled():
        plain: str | None = normalized
    else:
        plain = None
    return JournalStoragePayload(
        content=plain,
        raw=plain,
        cleaned=plain,
        raw_encrypted=encrypted,
    )


def resolve_journal_text(row: dict[str, Any], *, user_id: str) -> str:
    content = row.get("content")
    if isinstance(content, str) and content:
        return content
    encrypted = row.get("raw_encrypted")
    if encrypted is None:
        if journal_write_mode() == _WRITE_MODE_ENCRYPTED_ONLY:
            raise ValueError("Missing raw_encrypted payload in encrypted_only mode")
        return ""
    try:
        return decrypt_journal_text(user_id, encrypted)
    except Exception as exc:
        if journal_write_mode() == _WRITE_MODE_ENCRYPTED_ONLY:
            raise ValueError("Failed to decrypt journal payload in encrypted_only mode") from exc
        LOGGER.warning("Journal decrypt failed in dual_write mode; falling back to empty text")
        return ""


def hydrate_journal_row(row: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(row)
    if "raw_encrypted" not in data:
        return data
    user_id = data.get("user_id") or data.get("person_id")
    if user_id in (None, ""):
        return data
    current = data.get("content")
    has_plain = isinstance(current, str) and bool(current.strip())
    if has_plain:
        return data
    text = resolve_journal_text(data, user_id=str(user_id))
    if not text:
        return data
    for field in ("content", "raw", "cleaned"):
        value = data.get(field)
        if value in (None, ""):
            data[field] = text
    return data


__all__ = [
    "JournalStoragePayload",
    "build_journal_storage_payload",
    "decrypt_journal_text",
    "encrypt_journal_text",
    "hydrate_journal_row",
    "journal_plaintext_enabled",
    "journal_write_mode",
    "resolve_journal_text",
]
