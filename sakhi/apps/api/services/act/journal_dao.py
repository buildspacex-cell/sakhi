from __future__ import annotations

import datetime as dt
import uuid

from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.libs.security.journal_crypto import build_journal_storage_payload, journal_plaintext_enabled
from sakhi.libs.schemas.db import get_async_pool


def _coerce_uuid(value: uuid.UUID | str | None) -> uuid.UUID | str | None:
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except Exception:
        return value


async def add_entry(user_id: str, title: str | None, content: str, tags: list[str] | None = None) -> None:
    pool = await get_async_pool()
    user_uuid = _coerce_uuid(user_id)
    storage = build_journal_storage_payload(str(user_id), content)
    stored_title = title if journal_plaintext_enabled() else "Journal entry"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            -- IMPORTANT:
            -- ts = when the experience happened (lived time)
            -- created_at / updated_at = database lifecycle only
            INSERT INTO journal_entries (
                id, user_id, title, content, raw, raw_encrypted, tags, layer, ts, created_at, updated_at
            )
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, 'journal', NOW(), NOW(), NOW())
            RETURNING id
            """,
            user_uuid,
            stored_title,
            storage.content,
            storage.raw,
            storage.raw_encrypted,
            tags or [],
        )

    entry_id = str(row["id"]) if row else None
    if entry_id:
        await ingest_journal_entry(
            {
                "id": entry_id,
                "user_id": user_id,
                "content": content,
                "tags": tags or [],
                "layer": "act",
                "ts": dt.datetime.utcnow().isoformat(),
            }
        )
