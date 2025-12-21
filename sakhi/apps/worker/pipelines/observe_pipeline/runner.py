from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.ingestion.unified_ingest import ingest_fast, ingest_heavy
from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.apps.api.services.turn.context_cache import refresh_context_cache
from sakhi.apps.api.core.person_utils import resolve_person_id

LOGGER = logging.getLogger(__name__)


def run_pipeline_job(*, payload: Dict[str, Any]) -> None:
    """RQ entrypoint."""

    asyncio.run(_run_pipeline(payload))


async def _run_pipeline(payload: Dict[str, Any]) -> None:
    entry_id = payload["entry_id"]
    candidate_id = payload["person_id"]
    resolved_id = await resolve_person_id(candidate_id)
    if not resolved_id:
        LOGGER.warning("Observe pipeline could not resolve person_id=%s entry=%s", candidate_id, entry_id)
        return
    person_id = resolved_id
    LOGGER.info("Observe pipeline start entry=%s person=%s", entry_id, person_id)

    row = await q(
        """
        SELECT content, layer, tags, mood, created_at
        FROM journal_entries
        WHERE id = $1
        """,
        entry_id,
        one=True,
    )
    if not row:
        LOGGER.warning("Observe pipeline missing entry_id=%s", entry_id)
        return

    text = row["content"] or ""
    tags = row.get("tags") or []
    ts = row.get("created_at")
    layer = row.get("layer") or "conversation"

    try:
        triage = extract(text, ts)
    except Exception as exc:
        LOGGER.warning("extract failed entry=%s error=%s", entry_id, exc)
        triage = {}

    ingest_payload = {
        "id": entry_id,
        "user_id": person_id,
        "content": text,
        "mood": row.get("mood"),
        "tags": tags,
        "layer": layer,
        "ts": ts.isoformat() if ts else None,
        "facets": triage,
    }

    try:
        await ingest_journal_entry(ingest_payload)
    except Exception as exc:
        LOGGER.exception("ingest_journal_entry failed entry=%s error=%s", entry_id, exc)

    # Build 50: keep observe worker; ingest_fast + ingest_heavy are sufficient. canonical_ingest removed to avoid duplicate work.
    try:
        await ingest_fast(
            person_id=person_id,
            text=text,
            layer=layer,
            ts=ts,
            session_id=None,
            entry_id=entry_id,
        )
    except Exception as exc:  # pragma: no cover - best effort
        LOGGER.warning("ingest_fast failed entry=%s error=%s", entry_id, exc)

    try:
        await ingest_heavy(
            person_id=person_id,
            entry_id=entry_id,
            text=text,
            ts=ts,
        )
    except Exception as exc:
        LOGGER.exception("ingest_heavy failed entry=%s error=%s", entry_id, exc)

    await _mark_completed(entry_id)
    try:
        await refresh_context_cache(person_id)
    except Exception as exc:
        LOGGER.warning("Failed to refresh context cache person=%s entry=%s error=%s", person_id, entry_id, exc)


async def _mark_completed(entry_id: str) -> None:
    try:
        await dbexec(
            """
            UPDATE journal_entries
            SET processing_state = 'completed',
                processed_at = now(),
                updated_at = now()
            WHERE id = $1
            """,
            entry_id,
        )
    except Exception as exc:
        LOGGER.warning("Failed to mark entry complete id=%s error=%s", entry_id, exc)


__all__ = ["run_pipeline_job"]
