"""Authentication helpers for API and worker contexts."""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, status

_API_KEY_ENV = "SAKHI_API_KEY"


def verify_api_key(candidate: str | None) -> None:
    """Raise if the provided API key does not match the configured secret."""

    expected = os.getenv(_API_KEY_ENV)
    if not expected:
        return  # Treat absence as disabled during local development.

    if not candidate or not secrets.compare_digest(candidate, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


__all__ = ["verify_api_key"]
