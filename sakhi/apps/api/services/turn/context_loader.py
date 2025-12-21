from __future__ import annotations

import os
import logging
from typing import Any, Dict, List

import asyncpg
from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.memory.context_synthesizer import synthesize_memory_context

_CACHE_TABLE = os.getenv("MEMORY_CONTEXT_CACHE_TABLE", "memory_context_cache")
_ENABLE_FALLBACK = os.getenv("SAKHI_BUILD32_CONTEXT_FALLBACK", "1") == "1"
LOGGER = logging.getLogger(__name__)


async def load_memory_context(person_id: str, *, limit: int = 8) -> Dict[str, Any]:
    """Fetch pre-processed conversational context."""

    try:
        cache_rows = await q(
            f"""
            SELECT entries, rhythm_state, persona_snapshot, task_window, updated_at
            FROM {_CACHE_TABLE}
            WHERE person_id = $1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            person_id,
        )
    except asyncpg.UndefinedTableError:
        LOGGER.warning(
            "memory_context_cache table missing; falling back to synthesized context (person_id=%s)",
            person_id,
        )
        cache_rows = []
    except Exception as exc:
        LOGGER.warning(
            "Failed to read memory_context_cache (person_id=%s): %s",
            person_id,
            exc,
        )
        cache_rows = []
    if cache_rows:
        row = cache_rows[0]
        return {
            "entries": row.get("entries") or [],
            "rhythm": row.get("rhythm_state") or {},
            "persona": row.get("persona_snapshot") or {},
            "tasks": row.get("task_window") or [],
            "memory_context": " ".join(entry.get("summary", "") for entry in (row.get("entries") or [])[:limit]),
            "cache_timestamp": row.get("updated_at"),
            "cache_hit": True,
        }

    if not _ENABLE_FALLBACK:
        return {
            "entries": [],
            "rhythm": {},
            "persona": {},
            "tasks": [],
            "memory_context": "",
            "cache_hit": False,
        }

    memory_context = await synthesize_memory_context(person_id=person_id, user_query="", limit=350)
    return {
        "entries": [],
        "rhythm": {},
        "persona": {},
        "tasks": [],
        "memory_context": memory_context,
        "cache_hit": False,
    }


__all__ = ["load_memory_context"]
