from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.libs.embeddings import embed_text, to_pgvector


async def insert_inquiry_turn(
    *,
    person_id: str,
    reflection_id: str,
    reflection_kind: str,
    window_days: int,
    question_text: str,
    answer_text: str,
    answer_mode: str,
    sources_json: Dict[str, Any],
) -> str:
    turn_id = str(uuid4())
    try:
        await dbexec(
            """
            INSERT INTO reflection_inquiry_turns (
                id,
                person_id,
                reflection_id,
                reflection_kind,
                window_days,
                question_text,
                answer_text,
                answer_mode,
                sources_json
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            turn_id,
            person_id,
            reflection_id,
            reflection_kind,
            window_days,
            question_text,
            answer_text,
            answer_mode,
            json.dumps(sources_json or {}),
        )
    except Exception:
        # Fallback for environments where the migration has not yet added window_days.
        await dbexec(
            """
            INSERT INTO reflection_inquiry_turns (
                id,
                person_id,
                reflection_id,
                reflection_kind,
                question_text,
                answer_text,
                answer_mode,
                sources_json
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            turn_id,
            person_id,
            reflection_id,
            reflection_kind,
            question_text,
            answer_text,
            answer_mode,
            json.dumps(sources_json or {}),
        )
    return turn_id


async def insert_inquiry_embedding(
    *,
    turn_id: str,
    person_id: str,
    content_kind: str,
    content_text: str,
    embedding_vec: List[float],
) -> None:
    content_hash = hashlib.sha256((content_text or "").encode("utf-8")).hexdigest()
    vector_literal = to_pgvector(embedding_vec, length=1536)
    await dbexec(
        """
        INSERT INTO reflection_inquiry_embeddings (
            id,
            turn_id,
            person_id,
            content_kind,
            content_text,
            embedding_vec,
            content_hash
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        str(uuid4()),
        turn_id,
        person_id,
        content_kind,
        content_text,
        vector_literal,
        content_hash,
    )


async def embed_and_store_all(
    *,
    turn_id: str,
    person_id: str,
    question_text: str,
    answer_text: str,
) -> None:
    try:
        q_vec = await embed_text(question_text or "")
        a_vec = await embed_text(answer_text or "")
        combined = f"Q: {question_text}\nA: {answer_text}"
        c_vec = await embed_text(combined)
    except Exception:
        return

    async def _maybe_insert(kind: str, text: str, vec: Iterable[float]) -> None:
        if not text:
            return
        try:
            await insert_inquiry_embedding(
                turn_id=turn_id,
                person_id=person_id,
                content_kind=kind,
                content_text=text,
                embedding_vec=list(vec or []),
            )
        except Exception:
            # Best-effort only
            return

    await _maybe_insert("question", question_text or "", q_vec or [])
    await _maybe_insert("answer", answer_text or "", a_vec or [])
    await _maybe_insert("combined", combined, c_vec or [])


async def list_recent_inquiry_turns(
    *,
    person_id: str,
    reflection_id: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    try:
        if reflection_id:
            rows = await q(
                """
                SELECT id, question_text, answer_text, answer_mode, created_at
                FROM reflection_inquiry_turns
                WHERE person_id = $1 AND reflection_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                person_id,
                reflection_id,
                limit,
            )
        else:
            rows = await q(
                """
                SELECT id, question_text, answer_text, answer_mode, created_at
                FROM reflection_inquiry_turns
                WHERE person_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                person_id,
                limit,
            )
    except Exception:
        return []
    return list(rows or [])
