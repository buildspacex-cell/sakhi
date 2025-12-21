from __future__ import annotations

import uuid
import json
import datetime as dt
import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

import asyncpg
from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.libs.embeddings import embed_normalized


EPISODIC_CONTRACT_NOTE = (
    "Episodic memory is a stable, write-once record of significant moments. "
    "Do not write to memory_episodic during ingest; use explicit promotion only."
)


async def promote_to_episode(
    *,
    person_id: str,
    source_entry_ids: Sequence[str],
    summary: Optional[str] = None,
    context_tags: Optional[List[Any]] = None,
    embedding: Optional[Sequence[float]] = None,
    content_hash: Optional[str] = None,
    model_version: Optional[str] = None,
    created_at: Optional[dt.datetime] = None,
) -> Dict[str, Any]:
    """
    Explicitly create a single episodic row from one or more source entry ids.
    Episodes are write-once. Identity/soul/long-term signals must not be stored here.
    """
    episode_id = str(uuid.uuid4())
    ts = created_at or dt.datetime.utcnow()
    summary_value = summary or "Summary pending"
    ctx_tags_value = context_tags if isinstance(context_tags, list) else []
    ctx_tags_json = json.dumps(ctx_tags_value)
    embedding_value: Optional[str] = None
    if embedding:
        # pgvector expects a string literal like "[0.1,0.2,0.3]".
        embedding_value = "[" + ",".join(f"{float(val):.6f}" for val in embedding) + "]"
    record_payload = {
        "source_entry_ids": list(source_entry_ids),
        "summary": summary_value,
        "model_version": model_version,
        "created_at": ts.isoformat(),
    }
    record_payload_json = json.dumps(record_payload)

    await dbexec(
        """
        INSERT INTO memory_episodic (
            id,
            user_id,
            record,
            vector_vec,
            content_hash,
            context_tags,
            created_at
        )
        VALUES (
            $1,
            $2,
            $3::jsonb,
            CASE
                WHEN $4::text IS NULL THEN NULL::vector
                ELSE ($4::text)::vector
            END,
            $5,
            $6::jsonb,
            $7
        )
        ON CONFLICT (id) DO NOTHING
        """,
        episode_id,
        person_id,
        record_payload_json,
        embedding_value,
        content_hash,
        ctx_tags_json,
        ts,
    )

    return {
        "episode_id": episode_id,
        "person_id": person_id,
        "source_entry_ids": list(source_entry_ids),
        "created_at": ts.isoformat(),
        "summary": summary_value,
        "context_tags": ctx_tags_value,
        "content_hash": content_hash,
        "model_version": model_version,
    }


def _shallow_summary(text: str, limit: int = 320) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return "No text captured for this entry."
    return normalized[:limit]


async def build_episodic_from_journals_v2(
    *,
    person_id: str,
    start_ts: dt.datetime,
    end_ts: dt.datetime,
    source: str = "weekly_debug",
) -> Dict[str, Any]:
    """
    Build episodic memory directly from journal_entries.

    Deterministic rules:
    - Reads journal_entries only (raw evidence).
    - Writes to memory_episodic via promote_to_episode.
    - No STM writes, no identity/soul/sentiment inference.
    """
    journal_rows: Sequence[Dict[str, Any]] = await q(
        """
        SELECT id, content, created_at
        FROM journal_entries
        WHERE user_id = $1
          AND created_at >= $2
          AND created_at < $3
        ORDER BY created_at ASC
        """,
        person_id,
        start_ts,
        end_ts,
    )
    existing_hashes: set[str] = set()
    try:
        existing_episode_rows: Sequence[Dict[str, Any]] = await q(
            "SELECT content_hash FROM memory_episodic WHERE user_id = $1 AND content_hash IS NOT NULL",
            person_id,
        )
        existing_hashes = {str(row["content_hash"]) for row in existing_episode_rows if row.get("content_hash")}
    except asyncpg.UndefinedColumnError:
        # Environments that predate content_hash will treat all entries as new.
        existing_hashes = set()

    created = 0
    for row in journal_rows:
        entry_id = str(row.get("id"))
        content = row.get("content") or ""
        content_hash = hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()
        if not entry_id or content_hash in existing_hashes:
            continue
        summary_text = _shallow_summary(content)
        created_at: dt.datetime = row.get("created_at") or dt.datetime.utcnow()
        try:
            embedding_vec = await embed_normalized(summary_text)
        except Exception:
            embedding_vec = []

        await promote_to_episode(
            person_id=person_id,
            source_entry_ids=[entry_id],
            summary=summary_text,
            context_tags=[],
            embedding=embedding_vec,
            content_hash=content_hash,
            model_version=source,
            created_at=created_at,
        )
        created += 1

    return {
        "journals_read": len(journal_rows),
        "episodes_created": created,
        "person_id": person_id,
        "window_start": start_ts.isoformat(),
        "window_end": end_ts.isoformat(),
    }


__all__ = ["promote_to_episode", "build_episodic_from_journals_v2"]
