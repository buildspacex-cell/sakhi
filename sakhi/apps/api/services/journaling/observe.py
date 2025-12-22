from __future__ import annotations

import uuid
from typing import Any, Dict
import logging

from sakhi.apps.api.core.db import get_db

LOGGER = logging.getLogger(__name__)


async def observe_entry(
    person_id: str,
    text: str,
    source: str = "conversation",
    clarity_hint: str | None = None,
) -> Dict[str, Any]:
    """
    Minimal journaling observe helper.
    Persists the entry and returns the inserted row (best effort).
    """

    entry_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO journal_entries (id, user_id, content, raw, source_ref, layer)
            VALUES (
                $1,
                $2,
                $3,
                $3,
                jsonb_build_object(
                    'source', $4::text,
                    'clarity', $5::text
                ),
                'journal'
            )
            """,
            entry_id,
            person_id,
            text,
            source,
            clarity_hint,
        )
        row = await db.fetchrow(
            "SELECT * FROM journal_entries WHERE id = $1",
            entry_id,
        )
        if row:
            LOGGER.info("[observe_entry] inserted entry id=%s person_id=%s layer=%s", entry_id, person_id, row.get("layer"))
            return dict(row)
        LOGGER.warning("[observe_entry] insert returned no row id=%s person_id=%s", entry_id, person_id)
        return {"id": entry_id}
    except Exception as exc:
        LOGGER.exception("[observe_entry] failed insert person_id=%s error=%s", person_id, exc)
        return {"id": entry_id, "error": str(exc)}
    finally:
        await db.close()


__all__ = ["observe_entry"]
