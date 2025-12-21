"""Speech-to-text adapter that forwards audio to DeepSeek Voice.

Falls back to the legacy placeholder if DeepSeek is not configured or errors.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)
PLACEHOLDER_TRANSCRIPT = "[voice note captured] (transcription pending)"


def _env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key, default)
    if value:
        value = value.strip()
    return value or None


DEEPSEEK_VOICE_API_KEY = _env("DEEPSEEK_VOICE_API_KEY")
DEEPSEEK_VOICE_MODEL = _env("DEEPSEEK_VOICE_MODEL", "deepseek-voice")
DEEPSEEK_VOICE_BASE_URL = _env(
    "DEEPSEEK_VOICE_BASE_URL", "https://api.deepseek.com/v1/audio/transcriptions"
)


async def _transcribe_with_deepseek(
    data: bytes, filename: str | None, content_type: str | None
) -> str | None:
    """Send audio bytes to DeepSeek and return the transcript or ``None``."""

    if not DEEPSEEK_VOICE_API_KEY:
        LOGGER.debug("DeepSeek transcription skipped: API key not configured")
        return None

    headers = {"Authorization": f"Bearer {DEEPSEEK_VOICE_API_KEY}"}
    files = {
        "file": (
            filename or "audio.m4a",
            data,
            content_type or "application/octet-stream",
        )
    }
    form = {"model": DEEPSEEK_VOICE_MODEL}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DEEPSEEK_VOICE_BASE_URL, headers=headers, files=files, data=form
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        LOGGER.warning(
            "DeepSeek transcription error: %s %s",
            exc.response.status_code,
            exc.response.text,
        )
        return None
    except httpx.HTTPError as exc:
        LOGGER.warning("DeepSeek transcription request failed: %s", exc, exc_info=True)
        return None

    try:
        payload = response.json()
    except json.JSONDecodeError:
        LOGGER.warning("DeepSeek transcription returned non-JSON payload")
        return None

    transcript = (
        payload.get("text")
        or payload.get("transcript")
        or payload.get("data", {}).get("text")
    )
    if not transcript:
        LOGGER.warning("DeepSeek transcription missing text field: %s", payload)
        return None

    return str(transcript).strip()


def _decode_fallback(data: bytes) -> str:
    try:
        text = data.decode("utf-8").strip()
    except Exception:
        return PLACEHOLDER_TRANSCRIPT
    return text[:5000] if text else PLACEHOLDER_TRANSCRIPT


async def transcribe_file(upload_file: Any) -> str:
    """Transcribe an uploaded voice note using DeepSeek Voice when available."""

    data = await upload_file.read()
    if not data:
        return PLACEHOLDER_TRANSCRIPT

    transcript = await _transcribe_with_deepseek(
        data=data,
        filename=getattr(upload_file, "filename", None),
        content_type=getattr(upload_file, "content_type", None),
    )
    if transcript:
        return transcript[:5000]

    return _decode_fallback(data)
