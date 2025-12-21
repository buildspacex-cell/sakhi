from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sakhi.apps.api.core.db import exec as dbexec, q


async def get_raw(person_id: str) -> Optional[Dict[str, Any]]:
    row = await q(
        "SELECT * FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    return row


async def upsert_personal_model(person_id: str, payload: Dict[str, Any]) -> None:
    await dbexec(
        """
        INSERT INTO personal_model
            (person_id, short_term, long_term, updated_at)
        VALUES ($1, $2::jsonb, $3::jsonb, NOW())
        ON CONFLICT (person_id) DO UPDATE
        SET short_term = EXCLUDED.short_term,
            long_term = personal_model.long_term || jsonb_build_object(
                'last_seen', NOW()
            ),
            updated_at = NOW();
        """,
        person_id,
        json.dumps(payload.get("short_term", {})),
        json.dumps(payload.get("long_term", {})),
    )


# Backwards compatibility for older call sites
async def upsert(person_id: str, payload: Dict[str, Any]) -> None:  # pragma: no cover - temporary shim
    await upsert_personal_model(person_id, payload)
