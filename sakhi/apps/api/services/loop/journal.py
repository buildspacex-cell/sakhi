from __future__ import annotations

import datetime as dt
import uuid

from sakhi.apps.api.core.person_utils import resolve_journal_owner_ids
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


async def write_journal_entry(user_id: str, text: str, reply: str | None) -> str | None:
    pool = await get_async_pool()
    owner_person_id, owner_user_id = await resolve_journal_owner_ids(str(user_id))
    person_uuid = _coerce_uuid(owner_person_id or user_id)
    user_uuid = _coerce_uuid(owner_user_id or user_id)
    storage = build_journal_storage_payload(str(user_id), text or "")
    title = (text or "Turn")[:80] if journal_plaintext_enabled() else "Journal entry"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            -- IMPORTANT:
            -- ts = when the experience happened (lived time)
            -- created_at / updated_at = database lifecycle only
            INSERT INTO journal_entries (
                id, person_id, user_id, title, content, raw, raw_encrypted, layer, ts, created_at, updated_at
            )
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, 'journal', NOW(), NOW(), NOW())
            RETURNING id
            """,
            person_uuid,
            user_uuid,
            title,
            storage.content,
            storage.raw,
            storage.raw_encrypted,
        )

    entry_id = str(row["id"]) if row else None
    if entry_id:
        await ingest_journal_entry(
            {
                "id": entry_id,
                "user_id": user_id,
                "content": text or "",
                "cleaned": text,
                "layer": "loop",
                "ts": dt.datetime.utcnow().isoformat(),
            }
        )
    return entry_id
