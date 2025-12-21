from __future__ import annotations

import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.memory.retrieve_relevant_longterm import (
    get_relevant_longterm_slice,
)
from sakhi.apps.api.services.conversation_v2.conversation_context_builder import build_conversation_context, _build_deep_recall
from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt
from sakhi.apps.api.services.conversation_v2.conversation_tone import decide_tone
from sakhi.apps.api.services.memory.recall import build_recall_context
from sakhi.apps.api.services.patterns.detector import build_patterns_context

router = APIRouter(prefix="/debug", tags=["debug"])


def _ensure_dict(value: Any) -> Dict[str, Any]:
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


@router.get("/context")
async def debug_context(
    person_id: str = Query(..., description="Target person identifier"),
    latest_message: str = Query("", description="Latest user message for relevance"),
) -> Dict[str, Any]:
    """Expose personal model layers and relevant slices for debugging."""

    person = await q(
        """
        SELECT short_term, long_term
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    short_term = _ensure_dict((person or {}).get("short_term"))
    long_term = _ensure_dict((person or {}).get("long_term"))
    relevant = await get_relevant_longterm_slice(person_id, latest_message)

    return {
        "short_term": short_term,
        "long_term": long_term,
        "relevant_longterm": relevant,
        "latest_message": latest_message,
    }


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []
    return []


def _serialize_record(row: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in row.items():
        if key == "record":
            payload["record"] = _ensure_dict(value)
        elif key == "tags":
            payload["tags"] = _ensure_list(value)
        else:
            payload[key] = value
    return payload


async def _build_prompt_preview(person_id: str, user_text: str) -> Dict[str, Any]:
    context = await build_conversation_context(person_id)
    tone = decide_tone(context)
    metadata: Dict[str, Any] = {"debug": True}
    prompt = build_prompt(user_text, context, tone, metadata=metadata)
    recall_ctx = await build_recall_context(person_id, user_text)
    pattern_ctx = await build_patterns_context(person_id)
    system_ctx = f"{recall_ctx}\n\nPatterns:\n{pattern_ctx}"
    return {
        "user_text": user_text,
        "prompt": prompt,
        "system_context": system_ctx,
        "tone": tone,
        "context": context,
    }


@router.get("/deep_recall")
async def debug_deep_recall(
    person_id: str = Query(..., description="Target person identifier"),
    limit: int = Query(3, ge=1, le=10, description="Number of recall rows to inspect"),
) -> Dict[str, Any]:
    """Inspect deep recall (Build 41): stitched context, life-event links, thread continuity."""

    payload = await _build_deep_recall(person_id, limit=limit)
    return {
        "person_id": person_id,
        "recalls": payload.get("recalls", []),
        "life_events": payload.get("life_events", []),
        "threads": payload.get("threads", []),
    }


@router.get("/person_snapshot")
async def debug_person_snapshot(
    person_id: str = Query(..., description="Target person identifier"),
    limit: int = Query(5, ge=1, le=25),
) -> Dict[str, Any]:
    """Aggregate recent journals and memory views for quick debugging."""

    journal_rows = await q(
        """
        SELECT id, content, layer, tags, mood, created_at
        FROM journal_entries
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )

    journals = []
    for row in journal_rows:
        full_text = row.get("content") or ""
        journals.append(
            {
                "id": str(row["id"]),
                "text": full_text[:480],
                "full_text": full_text,
                "layer": row.get("layer"),
                "mood": row.get("mood"),
                "tags": row.get("tags") or [],
                "created_at": row.get("created_at"),
            }
        )

    short_rows = await q(
        """
        SELECT id, record, created_at
        FROM memory_short_term
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )

    short_term = []
    for row in short_rows:
        record = _ensure_dict(row.get("record"))
        short_term.append(
            {
                "id": str(row["id"]),
                "created_at": row.get("created_at"),
                "text": record.get("text"),
                "tags": record.get("tags"),
                "sentiment": record.get("sentiment"),
                "facets": record.get("facets"),
            }
        )

    episodic_rows = await q(
        """
        SELECT id, record, created_at
        FROM memory_episodic
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )

    episodic = []
    for row in episodic_rows:
        record = _ensure_dict(row.get("record"))
        episodic.append(
            {
                "id": str(row["id"]),
                "created_at": row.get("created_at"),
                "text": record.get("text"),
                "layer": record.get("layer"),
                "mood": record.get("mood"),
                "tags": record.get("tags"),
            }
        )

    personal_row = await q(
        """
        SELECT short_term, long_term, short_term_vector, updated_at
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    ) or {}

    personal_model_payload = {
        "short_term": _ensure_dict(personal_row.get("short_term")),
        "long_term": _ensure_dict(personal_row.get("long_term")),
        "short_term_vector": _ensure_dict(personal_row.get("short_term_vector")),
        "updated_at": personal_row.get("updated_at"),
    }

    prompt_preview: Dict[str, Any] | None = None
    if journals:
        try:
            prompt_preview = await _build_prompt_preview(person_id, journals[0]["full_text"] or "")
        except Exception as exc:
            prompt_preview = {"error": str(exc)}

    return {
        "person_id": person_id,
        "journals": journals,
        "short_term_memory": short_term,
        "episodic_memory": episodic,
        "personal_model": personal_model_payload,
        "count": {
            "journals": len(journals),
            "short_term": len(short_term),
            "episodic": len(episodic),
        },
        "latest_prompt": prompt_preview,
    }


@router.get("/tone_profile")
async def debug_tone_profile(
    person_id: str = Query(..., description="Target person identifier"),
) -> Dict[str, Any]:
    """
    Expose the Build 36 tone profile for a person for debugging.
    """

    context = await build_conversation_context(person_id)
    tone = decide_tone(context)
    return {
        "person_id": person_id,
        "tone": tone,
        "context_preview": {
            "persona_mode": context.get("persona_mode"),
            "conversation": context.get("conversation"),
            "continuity": context.get("continuity"),
            "rhythm": context.get("rhythm"),
            "emotion": context.get("emotion"),
            "themes": context.get("themes"),
        },
    }


@router.get("/trace/full")
async def get_trace_full(trace_id: str):
    trace_uuid = uuid.UUID(trace_id)
    rows = await q("SELECT * FROM debug_traces WHERE trace_id=$1", trace_uuid)
    if not rows:
        raise HTTPException(status_code=404, detail="trace not found")
    row = rows[0]
    return {
        "trace_id": str(row["trace_id"]),
        "flow": row.get("flow"),
        "ok": row.get("ok"),
        "success": row.get("success"),
        "summary": row.get("summary"),
        "events": row.get("events"),
        "human_narrative": row.get("human_narrative"),
        "plain_layers": row.get("plain_layers"),
        "payload": row.get("payload"),
    }
