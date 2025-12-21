from __future__ import annotations

import json

from sakhi.apps.api.core.db import get_db


async def update_dialog_state(person_id: str, conv_id: str, state: dict) -> None:
    """
    Upsert dialogue memory for the given conversation.
    """

    if not person_id or not conv_id:
        return

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO dialog_states (conversation_id, user_id, state, updated_at)
            VALUES ($1, $2, $3::jsonb, NOW())
            ON CONFLICT (conversation_id)
            DO UPDATE SET
                state = EXCLUDED.state,
                updated_at = NOW()
            """,
            conv_id,
            person_id,
            json.dumps(state or {}),
        )
    finally:
        await db.close()


__all__ = ["update_dialog_state"]
