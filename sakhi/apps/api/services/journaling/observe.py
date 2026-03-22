from __future__ import annotations

import uuid
from typing import Any, Dict
import logging

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.person_utils import resolve_journal_owner_ids
from sakhi.libs.security.journal_crypto import build_journal_storage_payload

LOGGER = logging.getLogger(__name__)


async def observe_entry(
    person_id: str,
    text: str,
    source: str = "conversation",
    clarity_hint: str | None = None,
    created_at: Any = None,
) -> Dict[str, Any]:
    """
    Minimal journaling observe helper.
    Persists the entry and returns the inserted row (best effort).
    """

    entry_id = str(uuid.uuid4())
    db = await get_db()
    LOGGER.error("[observe_entry] start person_id=%s layer=journal", person_id)
    experience_ts = created_at or None
    lifecycle_ts = None
    try:
        owner_person_id, owner_user_id = await resolve_journal_owner_ids(person_id)
        owner_person_id = owner_person_id or person_id
        owner_user_id = owner_user_id or person_id
        storage = build_journal_storage_payload(person_id, text)
        await db.execute(
            """
            -- IMPORTANT:
            -- ts = when the experience happened (lived time)
            -- created_at / updated_at = database lifecycle only
            -- Episodic memory and all downstream reasoning depend on ts.
            INSERT INTO journal_entries (
                id, person_id, user_id, content, raw, raw_encrypted, source_ref, layer, ts, created_at, updated_at
            )
            VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                $6,
                jsonb_build_object(
                    'source', $7::text,
                    'clarity', $8::text
                ),
                'journal',
                COALESCE($9, NOW()),
                NOW(),
                NOW()
            )
            """,
            entry_id,
            owner_person_id,
            owner_user_id,
            storage.content,
            storage.raw,
            storage.raw_encrypted,
            source,
            clarity_hint,
            experience_ts,
        )
        row = await db.fetchrow(
            "SELECT * FROM journal_entries WHERE id = $1",
            entry_id,
        )
        if row:
            LOGGER.error("[observe_entry] inserted entry id=%s person_id=%s layer=%s", entry_id, person_id, row.get("layer"))
            return dict(row)
        LOGGER.error("[observe_entry] insert returned no row id=%s person_id=%s", entry_id, person_id)
        return {"id": entry_id}
    except Exception as exc:
        LOGGER.exception("[observe_entry] failed insert person_id=%s error=%s", person_id, exc)
        return {"id": entry_id, "error": str(exc)}
    finally:
        await db.close()


__all__ = ["observe_entry"]
