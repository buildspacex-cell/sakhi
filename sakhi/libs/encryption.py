"""
Encryption Utilities
--------------------
Secure encryption/decryption for sensitive data like OAuth tokens.

Uses Fernet symmetric encryption with a key derived from environment.
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

# Environment variable for encryption key
ENCRYPTION_KEY_ENV = "SAKHI_ENCRYPTION_KEY"


def _get_fernet() -> Fernet:
    """
    Get Fernet instance with key from environment.

    The key should be a 32-byte base64-encoded string.
    If not set, derives one from a secret (not recommended for production).
    """
    key = os.environ.get(ENCRYPTION_KEY_ENV)

    if not key:
        # Fallback: derive from a secret env var (less secure but functional)
        secret = os.environ.get("SAKHI_SECRET_KEY", "sakhi-dev-secret-change-me")
        # Use SHA256 to get 32 bytes, then base64 encode for Fernet
        derived = hashlib.sha256(secret.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()

    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a string value.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    if not plaintext:
        return ""

    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return encrypted.decode()


def decrypt_value(ciphertext: str) -> Optional[str]:
    """
    Decrypt an encrypted string value.

    Args:
        ciphertext: The encrypted string from encrypt_value()

    Returns:
        Decrypted plaintext, or None if decryption fails
    """
    if not ciphertext:
        return None

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        return None
    except Exception:
        return None


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.

    Use this to generate a key for SAKHI_ENCRYPTION_KEY env var.

    Returns:
        Base64-encoded 32-byte key suitable for Fernet
    """
    return Fernet.generate_key().decode()


__all__ = ["encrypt_value", "decrypt_value", "generate_key"]
