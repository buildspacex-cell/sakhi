from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, List, Sequence

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.libs.embeddings import embed_text, to_pgvector


def _coerce_float_list(value: Any) -> List[float]:
    if isinstance(value, list):
        try:
            return [float(x) for x in value]
        except Exception:
            return []
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except Exception:
            return []
        if isinstance(decoded, list):
            return _coerce_float_list(decoded)
    return []


def _to_1024(vec: Sequence[float]) -> List[float]:
    trimmed = [float(v) for v in list(vec)[:1024]]
    if len(trimmed) < 1024:
        trimmed.extend([0.0] * (1024 - len(trimmed)))
    return trimmed


async def backfill_journal_embeddings(*, person_id: str | None, limit: int, dry_run: bool) -> int:
    rows = await q(
        """
        SELECT je.id, je.user_id, je.content
        FROM journal_entries je
        LEFT JOIN journal_embeddings emb ON je.id = emb.entry_id
        WHERE emb.entry_id IS NULL
          AND ($1::text IS NULL OR je.user_id = $1)
        ORDER BY je.ts DESC NULLS LAST, je.created_at DESC NULLS LAST
        LIMIT $2
        """,
        person_id,
        limit,
    )
    if dry_run:
        print(f"[dry-run] journal_embeddings to backfill: {len(rows)}")
        return 0

    updated = 0
    for row in rows:
        entry_id = str(row["id"])
        text = (row.get("content") or "").strip()
        if not text:
            continue
        vec = await embed_text(text)
        if isinstance(vec, list) and vec and isinstance(vec[0], list):
            vec = vec[0]
        floats = _coerce_float_list(vec)
        if not floats:
            continue
        vector_literal = to_pgvector(floats, length=1536)
        await dbexec(
            """
            INSERT INTO journal_embeddings (entry_id, model, embedding_vec)
            VALUES ($1, 'text-embedding-3-small', $2::vector)
            ON CONFLICT (entry_id)
            DO UPDATE SET embedding_vec = EXCLUDED.embedding_vec
            """,
            entry_id,
            vector_literal,
        )
        updated += 1
    return updated


async def backfill_short_term_record_embeddings(*, person_id: str | None, limit: int, dry_run: bool) -> int:
    rows = await q(
        """
        SELECT id, user_id, record
        FROM memory_short_term
        WHERE (record->'embedding' IS NULL OR jsonb_array_length(COALESCE(record->'embedding','[]'::jsonb)) = 0)
          AND COALESCE(record->>'text','') <> ''
          AND ($1::text IS NULL OR user_id = $1)
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    if dry_run:
        print(f"[dry-run] memory_short_term.record.embedding to backfill: {len(rows)}")
        return 0

    updated = 0
    for row in rows:
        row_id = str(row["id"])
        rec = row.get("record") or {}
        text = ""
        if isinstance(rec, dict):
            text = str(rec.get("text") or "").strip()
        if not text:
            continue
        vec = await embed_text(text)
        if isinstance(vec, list) and vec and isinstance(vec[0], list):
            vec = vec[0]
        floats = _coerce_float_list(vec)
        if not floats:
            continue
        vec_1024 = _to_1024(floats)
        await dbexec(
            """
            UPDATE memory_short_term
            SET record = jsonb_set(record, '{embedding}', to_jsonb($2::float8[]), true)
            WHERE id = $1
            """,
            row_id,
            vec_1024,
        )
        updated += 1
    return updated


async def amain() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing embeddings (one-time or scheduled).")
    parser.add_argument("--person-id", default=None, help="Optional person_id to scope backfill.")
    parser.add_argument("--limit", type=int, default=200, help="Max rows per table to backfill in this run.")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing.")
    args = parser.parse_args()

    if not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required.")

    total_updated = 0
    updated_journals = await backfill_journal_embeddings(
        person_id=args.person_id,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    updated_short_term = await backfill_short_term_record_embeddings(
        person_id=args.person_id,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    total_updated += updated_journals + updated_short_term

    if args.dry_run:
        return 0

    print(f"Backfilled: journal_embeddings={updated_journals} memory_short_term.record.embedding={updated_short_term}")
    return 0 if total_updated >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(amain()))

