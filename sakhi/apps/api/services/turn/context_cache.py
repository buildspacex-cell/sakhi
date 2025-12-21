from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q, exec as dbexec


async def _recent_short_term_entries(person_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT record, created_at
        FROM memory_short_term
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    entries: List[Dict[str, Any]] = []
    for row in rows:
        record = row.get("record") or {}
        if isinstance(record, str):
            try:
                record = json.loads(record)
            except json.JSONDecodeError:
                record = {}
        entries.append(
            {
                "text": record.get("text"),
                "tags": record.get("tags") or [],
                "layer": record.get("layer"),
                "mood": record.get("mood"),
                "sentiment": record.get("sentiment"),
                "facets": record.get("facets"),
                "created_at": row.get("created_at"),
            }
        )
    return entries


async def _personal_model_snapshot(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT short_term, long_term, updated_at
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if not row:
        return {}

    def _coerce(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        return {}

    snapshot = {
        "short_term": _coerce(row.get("short_term")),
        "long_term": _coerce(row.get("long_term")),
        "updated_at": row.get("updated_at"),
    }
    return snapshot


async def refresh_context_cache(person_id: str, *, window_kind: str = "default") -> None:
    entries = await _recent_short_term_entries(person_id)
    personal_snapshot = await _personal_model_snapshot(person_id)
    rhythm_state = (personal_snapshot.get("long_term") or {}).get("layers", {}).get("rhythm") or {}

    await dbexec(
        """
        INSERT INTO memory_context_cache (person_id, window_kind, entries, rhythm_state, persona_snapshot, task_window, updated_at)
        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, '[]'::jsonb, NOW())
        ON CONFLICT (person_id, window_kind)
        DO UPDATE SET
            entries = EXCLUDED.entries,
            rhythm_state = EXCLUDED.rhythm_state,
            persona_snapshot = EXCLUDED.persona_snapshot,
            task_window = EXCLUDED.task_window,
            updated_at = EXCLUDED.updated_at
        """,
        person_id,
        window_kind,
        json.dumps(entries, ensure_ascii=False),
        json.dumps(rhythm_state, ensure_ascii=False),
        json.dumps(personal_snapshot, ensure_ascii=False),
    )


__all__ = ["refresh_context_cache"]
