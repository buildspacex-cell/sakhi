from __future__ import annotations

import datetime as dt
import os
from typing import Iterable, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.observe.models import IngestedEntry

BUILD32_DB_EXTENSIONS = os.getenv("SAKHI_BUILD32_DB_EXTENSIONS", "0") == "1"


async def ingest_entry(
    *,
    person_id: str,
    text: str,
    layer: str,
    tags: Iterable[str] | None = None,
    input_type: str | None = None,
    client_context: dict | None = None,
    language: str | None = None,
    timezone: str | None = None,
    user_tags: Iterable[str] | None = None,
    mood: str | None = None,
    ack_text: str | None = None,
    ts: dt.datetime | None = None,
) -> IngestedEntry:
    """Insert minimal journal entry and return its metadata."""

    created_at = ts or dt.datetime.utcnow()
    safe_tags = list(tags or [])
    safe_user_tags = list(user_tags or safe_tags)
    safe_context = client_context or {}

    if BUILD32_DB_EXTENSIONS:
        row = await q(
            """
            INSERT INTO journal_entries (
                user_id, content, layer, tags, mood,
                input_type, client_context, language, timezone, user_tags,
                created_at, updated_at,
                processing_state, processing_attempts, ack_text
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11, $11, 'queued', 0, $12)
            RETURNING id
            """,
            person_id,
            text,
            layer or "journal",
            safe_tags,
            mood,
            input_type,
            safe_context,
            language,
            timezone,
            safe_user_tags,
            created_at,
            ack_text,
            one=True,
        )
    else:
        row = await q(
            """
            INSERT INTO journal_entries (
                user_id, content, layer, tags, mood,
                input_type, client_context, language, timezone, user_tags,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11, $11)
            RETURNING id
            """,
            person_id,
            text,
            layer or "journal",
            safe_tags,
            mood,
            input_type,
            safe_context,
            language,
            timezone,
            safe_user_tags,
            created_at,
            one=True,
        )

    entry_id = str(row["id"])
    return IngestedEntry(
        entry_id=entry_id,
        person_id=person_id,
        status="queued",
        created_at=created_at,
        tags=safe_tags,
    )


__all__ = ["ingest_entry"]
