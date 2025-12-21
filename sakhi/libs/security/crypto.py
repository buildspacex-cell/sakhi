"""Field-level encryption helpers built on AES-GCM."""

from __future__ import annotations

import base64
import os
import secrets
from hashlib import sha256

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SECRET_ENV = "ENCRYPTION_KEY"
_NONCE_SIZE = 12


def _derive_key() -> bytes:
    raw_secret = os.getenv(_SECRET_ENV)
    if not raw_secret:
        raise RuntimeError("ENCRYPTION_KEY must be configured before import")

    return sha256(raw_secret.encode("utf-8")).digest()


_KEY = _derive_key()


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(token + padding)


def encrypt_field(value: str) -> str:
    """Encrypt a string using AES-GCM with a random nonce per value."""

    aes = AESGCM(_KEY)
    nonce = secrets.token_bytes(_NONCE_SIZE)
    ciphertext = aes.encrypt(nonce, value.encode("utf-8"), associated_data=None)
    return _encode(nonce + ciphertext)


def decrypt_field(token: str) -> str:
    """Decrypt a previously encrypted value."""

    raw = _decode(token)
    if len(raw) <= _NONCE_SIZE:
        raise ValueError("Encrypted payload is malformed")

    nonce, ciphertext = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    aes = AESGCM(_KEY)
    plaintext = aes.decrypt(nonce, ciphertext, associated_data=None)
    return plaintext.decode("utf-8")


__all__ = ["decrypt_field", "encrypt_field"]
