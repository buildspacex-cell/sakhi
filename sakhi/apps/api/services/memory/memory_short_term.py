from __future__ import annotations

import datetime as dt
import json
import uuid
from typing import Any, Dict, List, Sequence

from dateutil import parser

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.apps.api.services.memory.memory_long_term import consolidate_long_term
from sakhi.apps.api.services.memory.stm_config import compute_expires_at


def _sanitize(obj: Any) -> Any:
    """
    Recursively convert UUIDs to strings and make the structure JSON safe.
    """
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(i) for i in obj]
    return obj


async def cleanup_expired_short_term() -> None:
    """Best-effort eviction of expired STM rows."""
    await dbexec(
        "DELETE FROM memory_short_term WHERE expires_at < NOW()"
    )


def _coerce_vector(candidate: Any) -> list[float]:
    if isinstance(candidate, (bytes, bytearray)):
        try:
            candidate = candidate.decode("utf-8")
        except Exception:
            return []

    if isinstance(candidate, str):
        text = candidate.strip()
        if not text:
            return []
        parsed: Any
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = []
        else:
            parts = [piece.strip() for piece in text.split(",") if piece.strip()]
            parsed = parts
        if isinstance(parsed, (list, tuple)):
            candidate = parsed
        else:
            return []

    if isinstance(candidate, (list, tuple)):
        items: Sequence[Any] = candidate  # type: ignore[assignment]
    else:
        return []

    if items and isinstance(items[0], (list, tuple)):
        items = items[0]  # type: ignore[assignment]

    try:
        return [float(value) for value in items]  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return []


def _coerce_record(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return {}
        try:
            decoded = json.loads(text)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            return {}
    return {}


def _to_utc(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = parser.parse(value)
        except Exception:
            return None
    if not isinstance(value, dt.datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


async def merge_into_short_term(person_id: str, record: Dict[str, Any], vec: Sequence[float]) -> Dict[str, Any]:
    """
    Append a new episodic memory into the short-term table and recompute the
    rolling short-term vector (last 7 days).
    STM is evidence-only; no derived signals are stored here.
    """

    # STM must remain an evidence pointer cache; do not store derived signals here.
    enriched_record = {
        "entry_id": record.get("entry_id") or record.get("id"),
        "source_type": record.get("layer") or "journal",
        "text": record.get("text") or record.get("content") or "",
        "mood": record.get("mood"),
        "user_tags": record.get("tags"),
    }

    await cleanup_expired_short_term()
    expires_at = compute_expires_at(dt.datetime.utcnow())

    await dbexec(
        """
        INSERT INTO memory_short_term (id, user_id, record, created_at, expires_at)
        VALUES ($1, $2, $3::jsonb, NOW(), $4)
        """,
        str(uuid.uuid4()),
        person_id,
        json.dumps(_sanitize(enriched_record), ensure_ascii=False),
        expires_at,
    )

    # STM no longer aggregates vectors; keep it optional/disposable.
    await consolidate_long_term(person_id)
    return {}
