from __future__ import annotations

import uuid
from typing import Any, Dict

from sakhi.apps.api.core.db import get_db


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
        return dict(row) if row else {"id": entry_id}
    finally:
        await db.close()


__all__ = ["observe_entry"]
