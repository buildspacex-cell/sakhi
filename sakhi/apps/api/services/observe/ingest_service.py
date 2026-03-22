from __future__ import annotations

import datetime as dt
import os
from typing import Iterable, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_journal_owner_ids
from sakhi.apps.api.services.observe.models import IngestedEntry
from sakhi.libs.security.journal_crypto import build_journal_storage_payload

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

    experience_ts = ts or dt.datetime.utcnow()
    lifecycle_ts = dt.datetime.utcnow()
    # IMPORTANT:
    # ts = when the experience happened (lived time)
    # created_at / updated_at = database lifecycle only
    # Episodic memory and all downstream reasoning depend on ts.
    safe_tags = list(tags or [])
    safe_user_tags = list(user_tags or safe_tags)
    safe_context = client_context or {}
    owner_person_id, owner_user_id = await resolve_journal_owner_ids(person_id)
    owner_person_id = owner_person_id or person_id
    owner_user_id = owner_user_id or person_id
    storage = build_journal_storage_payload(person_id, text)

    if BUILD32_DB_EXTENSIONS:
        row = await q(
            """
            INSERT INTO journal_entries (
                person_id, user_id, content, raw, raw_encrypted, layer, tags, mood,
                input_type, client_context, language, timezone, user_tags,
                ts, created_at, updated_at,
                processing_state, processing_attempts, ack_text
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, $12, $13, $14, $15, $15, 'queued', 0, $16)
            RETURNING id
            """,
            owner_person_id,
            owner_user_id,
            storage.content,
            storage.raw,
            storage.raw_encrypted,
            layer or "journal",
            safe_tags,
            mood,
            input_type,
            safe_context,
            language,
            timezone,
            safe_user_tags,
            experience_ts,
            lifecycle_ts,
            ack_text,
            one=True,
        )
    else:
        row = await q(
            """
            INSERT INTO journal_entries (
                person_id, user_id, content, raw, raw_encrypted, layer, tags, mood,
                input_type, client_context, language, timezone, user_tags,
                ts, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, $12, $13, $14, $14)
            RETURNING id
            """,
            owner_person_id,
            owner_user_id,
            storage.content,
            storage.raw,
            storage.raw_encrypted,
            layer or "journal",
            safe_tags,
            mood,
            input_type,
            safe_context,
            language,
            timezone,
            safe_user_tags,
            experience_ts,
            lifecycle_ts,
            one=True,
        )

    entry_id = str(row["id"])
    return IngestedEntry(
        entry_id=entry_id,
        person_id=person_id,
        status="queued",
        created_at=lifecycle_ts,
        tags=safe_tags,
    )


__all__ = ["ingest_entry"]
