from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi.encoders import jsonable_encoder

from sakhi.apps.api.core.db import dbfetchrow, exec as dbexec


def _to_jsonb(value: Any) -> Any:
    """Ensure values are JSON-serializable before sending to asyncpg."""
    if value is None:
        return None
    # asyncpg will coerce text to jsonb; send text to avoid Dict casting errors.
    return json.dumps(jsonable_encoder(value))


async def upsert_environment_context(
    person_id: str,
    *,
    weather: Optional[Dict[str, Any]] = None,
    calendar_blocks: Optional[List[Dict[str, Any]]] = None,
    day_cycle: Optional[str] = None,
    weekend_flag: Optional[bool] = None,
    holiday_flag: Optional[bool] = None,
    travel_flag: Optional[bool] = None,
    environment_tags: Optional[List[str]] = None,
) -> bool:
    sql = """
    INSERT INTO environment_context (
        person_id, weather, calendar_blocks, day_cycle,
        weekend_flag, holiday_flag, travel_flag, environment_tags, updated_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
    ON CONFLICT (person_id) DO UPDATE SET
        weather = COALESCE(EXCLUDED.weather, environment_context.weather),
        calendar_blocks = COALESCE(EXCLUDED.calendar_blocks, environment_context.calendar_blocks),
        day_cycle = COALESCE(EXCLUDED.day_cycle, environment_context.day_cycle),
        weekend_flag = COALESCE(EXCLUDED.weekend_flag, environment_context.weekend_flag),
        holiday_flag = COALESCE(EXCLUDED.holiday_flag, environment_context.holiday_flag),
        travel_flag = COALESCE(EXCLUDED.travel_flag, environment_context.travel_flag),
        environment_tags = COALESCE(EXCLUDED.environment_tags, environment_context.environment_tags),
        updated_at = NOW();
    """
    try:
        await dbexec(
            sql,
            person_id,
            _to_jsonb(weather),
            _to_jsonb(calendar_blocks),
            day_cycle,
            weekend_flag,
            holiday_flag,
            travel_flag,
            _to_jsonb(environment_tags),
        )
        return True
    except Exception as exc:
        # Surface failure to logs so callers can inspect the root cause.
        print(f"[Environment] upsert failed for person={person_id}: {exc}")
        return False


async def get_environment_context(person_id: str) -> Dict[str, Any] | None:
    sql = """
    SELECT person_id, weather, calendar_blocks, day_cycle,
           weekend_flag, holiday_flag, travel_flag, environment_tags, updated_at
    FROM environment_context
    WHERE person_id = $1
    """
    return await dbfetchrow(sql, person_id)


__all__ = ["upsert_environment_context", "get_environment_context"]
