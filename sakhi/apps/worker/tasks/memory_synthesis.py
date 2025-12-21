from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.apps.api.services.memory.personal_model import synthesize_layer
from sakhi.apps.api.services.memory.synthesis import run_memory_synthesis


def _ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


async def consolidate_person_models() -> None:
    rows = await dbfetch(
        "SELECT person_id, short_term, long_term FROM personal_model",
    )
    for row in rows:
        person_id = row.get("person_id")
        if not person_id:
            continue

        short_term = _ensure_dict(row.get("short_term"))
        long_term = _ensure_dict(row.get("long_term"))
        if not short_term:
            continue

        merged = synthesize_layer(long_term, short_term)
        await dbexec(
            """
            UPDATE personal_model
            SET long_term = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            json.dumps(merged),
        )


def run_consolidate_person_models() -> None:
    asyncio.run(consolidate_person_models())


def run_memory_synthesis_job(person_id: str, horizon: str = "weekly") -> None:
    asyncio.run(run_memory_synthesis(person_id, horizon=horizon))


__all__ = ["consolidate_person_models", "run_consolidate_person_models", "run_memory_synthesis_job"]
