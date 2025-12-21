import uuid
import datetime as dt
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.api.ingest.extractor import extract
from sakhi.libs.embeddings import embed_normalized, to_pgvector
from sakhi.apps.api.services.ingestion.unified_ingest import _hash_text, _normalize_text, _existing_vector
from sakhi.apps.api.services.memory.stm_config import compute_expires_at
from sakhi.apps.api.utils.person_resolver import resolve_person
import logging

router = APIRouter(prefix="/experience", tags=["experience-journal"])
logger = logging.getLogger(__name__)


async def _insert_journal_entry(person_id: str, text: str, layer: str, ts: dt.datetime, entry_id: str) -> None:
    await dbexec(
        """
        INSERT INTO journal_entries (id, user_id, content, layer, created_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO NOTHING
        """,
        entry_id,
        person_id,
        text,
        layer,
        ts,
    )


@router.post("/journal")
async def create_experience_journal(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    layer = payload.get("layer") or "journal"
    ts = dt.datetime.utcnow()
    entry_id = payload.get("entry_id") or str(uuid.uuid4())
    person_id, person_label, person_key = resolve_person(request)
    logger.info(
        "ACTIVE_DEV_PERSON",
        extra={"person_id": person_id, "person_label": person_label, "person_key": person_key},
    )

    normalized = _normalize_text(text)
    content_hash = _hash_text(normalized)
    triage = extract(text, ts)
    try:
        from sakhi.apps.api.services.memory.memory_short_term import cleanup_expired_short_term
        await cleanup_expired_short_term()
    except Exception:
        pass
    # Ensure the entry row exists before any FK inserts.
    await _insert_journal_entry(person_id, text, layer, ts, entry_id)

    vec = await _existing_vector(person_id, content_hash)
    write_embedding = False
    if not vec:
        vec = await embed_normalized(normalized) or []
        write_embedding = True

    vec_literal = to_pgvector(vec)
    if write_embedding:
        # Only write embedding row when we computed it here; dedup hits reuse the existing vector.
        await dbexec(
            """
            INSERT INTO journal_embeddings (entry_id, model, embedding_vec, content_hash, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (entry_id) DO UPDATE SET content_hash = EXCLUDED.content_hash, embedding_vec = EXCLUDED.embedding_vec
            """,
            entry_id,
            "text-embedding-3-small",
            vec_literal,
            content_hash,
        )

    expires_at = compute_expires_at(ts)

    # short term: store only evidence pointer/text; no vectors or derived signals
    await dbexec(
        """
        INSERT INTO memory_short_term (id, user_id, entry_id, text, layer, expires_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (entry_id) DO NOTHING
        """,
        str(uuid.uuid4()),
        person_id,
        entry_id,
        text,
        layer,
        expires_at,
    )

    return {
        "entry_id": entry_id,
        "person_id": person_id,
        "created_at": ts.isoformat(),
        "text_echo": text,
        "normalized": normalized,
        "layer": layer,
        "content_hash": content_hash,
        "triage": triage if isinstance(triage, dict) else {},
    }


@router.get("/journal/{entry_id}/debug")
async def debug_experience_journal(entry_id: str) -> Dict[str, Any]:
    entry = await q("SELECT * FROM journal_entries WHERE id = $1", entry_id, one=True) or {}
    embedding = await q("SELECT model, content_hash FROM journal_embeddings WHERE entry_id = $1", entry_id, one=True) or {}
    st = await q("SELECT id, content_hash, layer, triage FROM memory_short_term WHERE entry_id = $1", entry_id, one=True) or {}
    ep = await q("SELECT id, content_hash, time_scope, context_tags FROM memory_episodic WHERE entry_id = $1", entry_id, one=True) or {}
    return {
        "entry": entry,
        "embedding": embedding,
        "short_term": st,
        "episodic": ep,
    }
