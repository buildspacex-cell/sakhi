from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

MAX_ACTIVE_SESSIONS = 6

from sakhi.libs.schemas.db import get_async_pool

logger = logging.getLogger(__name__)


def _coerce_uuid(value: uuid.UUID | str | None) -> uuid.UUID | str | None:
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except Exception:
        return value


async def ensure_session(user_id: str, slug: str = "journal") -> str:
    pool = await get_async_pool()
    user_uuid = _coerce_uuid(user_id)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, status FROM conversation_sessions WHERE user_id = $1 AND slug = $2",
            user_uuid,
            slug,
        )
        if existing:
            session_id = existing["id"]
            await conn.execute(
                "UPDATE conversation_sessions SET status = 'active', last_active_at = now() WHERE id = $1",
                session_id,
            )
            return session_id

        active_count = await conn.fetchval(
            "SELECT COUNT(*) FROM conversation_sessions WHERE user_id = $1 AND status = 'active'",
            user_uuid,
        )
        if active_count >= MAX_ACTIVE_SESSIONS:
            await conn.execute(
                """
                WITH oldest AS (
                    SELECT id
                    FROM conversation_sessions
                    WHERE user_id = $1 AND status = 'active'
                    ORDER BY COALESCE(last_active_at, created_at) ASC
                    LIMIT 1
                )
                UPDATE conversation_sessions
                SET status = 'archived', archived_at = now()
                WHERE id IN (SELECT id FROM oldest)
                """,
                user_uuid,
            )

        row = await conn.fetchrow(
            """
            INSERT INTO conversation_sessions (id, user_id, slug, status, last_active_at, turn_count)
            VALUES (gen_random_uuid(), $1, $2, 'active', now(), 0)
            RETURNING id
            """,
            user_uuid,
            slug,
        )
        return row["id"]


async def append_turn(
    user_id: str,
    session_id: str,
    role: str,
    text: str,
    tone: Optional[str] = None,
    archetype: Optional[str] = None,
    source: str = "text",
) -> None:
    """Append a conversation turn to the database."""
    pool = await get_async_pool()
    user_uuid = _coerce_uuid(user_id)
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversation_turns (id, user_id, session_id, role, text, tone, archetype, source)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7)
            """,
            user_uuid,
            session_uuid,
            role,
            text,
            tone,
            archetype,
            source,
        )
        await conn.execute(
            """
            UPDATE conversation_sessions
            SET last_active_at = now(), turn_count = COALESCE(turn_count, 0) + 1
            WHERE id = $1
            """,
            session_uuid,
        )


async def load_recent_turns(session_id: str, limit: int = 12) -> List[Dict]:
    """Load recent conversation turns for a session."""
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, role, text, tone, archetype, source, created_at
            FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            session_uuid,
            limit,
        )
    return [dict(row) for row in reversed(rows)]


async def get_summary(session_id: str) -> str:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT summary FROM session_summaries WHERE session_id = $1",
            session_uuid,
        )
    return row["summary"] if row else ""


async def set_summary(session_id: str, summary: str) -> None:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO session_summaries (session_id, summary, last_updated)
            VALUES ($1, $2, now())
            ON CONFLICT (session_id)
            DO UPDATE SET summary = EXCLUDED.summary, last_updated = now()
            """,
            session_uuid,
            summary,
        )


async def get_session_info(session_id: str) -> Dict[str, Any]:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, slug, title, status FROM conversation_sessions WHERE id = $1",
            session_uuid,
        )
    return dict(row) if row else {}


async def set_session_title(session_id: str, title: str) -> None:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE conversation_sessions SET title = $2 WHERE id = $1",
            session_uuid,
            title,
        )


async def load_context_with_summary(
    session_id: str,
    recent_limit: int = 8,
    total_limit: int = 20,
) -> Dict[str, Any]:
    """
    Load conversation context with hybrid approach:
    - Recent turns (verbatim) for immediate context
    - Session summary for older compressed context
    - Total turn count for awareness of conversation length

    Returns:
        {
            "recent_turns": [...],      # Last N turns verbatim
            "session_summary": "...",   # Compressed older context
            "total_turns": int,         # Total conversation length
            "has_more_context": bool,   # Whether summary represents older turns
        }
    """
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)

    async with pool.acquire() as conn:
        # Get total turn count
        count_row = await conn.fetchrow(
            "SELECT turn_count FROM conversation_sessions WHERE id = $1",
            session_uuid,
        )
        total_turns = count_row["turn_count"] if count_row else 0

        # Load recent turns (verbatim)
        rows = await conn.fetch(
            """
            SELECT role, text, tone, archetype, created_at
            FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            session_uuid,
            recent_limit,
        )
        recent_turns = [dict(row) for row in reversed(rows)]

        # Load session summary (compressed older context)
        summary_row = await conn.fetchrow(
            "SELECT summary FROM session_summaries WHERE session_id = $1",
            session_uuid,
        )
        session_summary = summary_row["summary"] if summary_row else ""

    has_more_context = total_turns > recent_limit and bool(session_summary)

    return {
        "recent_turns": recent_turns,
        "session_summary": session_summary,
        "total_turns": total_turns,
        "has_more_context": has_more_context,
    }


async def compress_older_turns_to_summary(
    session_id: str,
    keep_recent: int = 8,
    use_llm: bool = True,
) -> Optional[str]:
    """
    Compress older turns (beyond keep_recent) into an intelligent session summary.
    Called periodically or when turn count exceeds threshold.

    The summary preserves:
    - Pronoun references (who "she", "he", "they" refer to)
    - Topic markers (what "it", "that project" refer to)
    - Key entities (people, places, decisions)
    - Emotional threads (ongoing concerns, feelings)
    - Unresolved topics or questions

    Returns the generated summary or None if not enough turns to compress.
    """
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)

    async with pool.acquire() as conn:
        # Get turns older than the recent window
        rows = await conn.fetch(
            """
            SELECT role, text, created_at
            FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at DESC
            OFFSET $2
            """,
            session_uuid,
            keep_recent,
        )

        if not rows or len(rows) < 4:  # Need at least 2 exchanges to summarize
            return None

        # Build text to summarize (oldest first)
        older_turns = list(reversed([dict(row) for row in rows]))

        # Use LLM for intelligent summarization if enabled
        use_intelligent_summary = use_llm and os.getenv("SAKHI_INTELLIGENT_SUMMARY", "1") == "1"

        if use_intelligent_summary:
            summary = await _generate_intelligent_summary(older_turns)
        else:
            # Fallback: simple compression
            summary = _generate_simple_summary(older_turns)

        # Store the summary
        await conn.execute(
            """
            INSERT INTO session_summaries (session_id, summary, last_updated, turn_count_at_summary)
            VALUES ($1, $2, now(), $3)
            ON CONFLICT (session_id)
            DO UPDATE SET summary = EXCLUDED.summary, last_updated = now(), turn_count_at_summary = EXCLUDED.turn_count_at_summary
            """,
            session_uuid,
            summary,
            len(older_turns),
        )

        return summary


def _generate_simple_summary(turns: List[Dict]) -> str:
    """Simple fallback summary - text excerpts."""
    summary_parts = []
    for turn in turns[-10:]:
        role_label = "User" if turn["role"] == "user" else "Sakhi"
        text_preview = turn["text"][:100] + "..." if len(turn["text"]) > 100 else turn["text"]
        summary_parts.append(f"{role_label}: {text_preview}")
    return "Earlier in this conversation:\n" + "\n".join(summary_parts)


async def _generate_intelligent_summary(turns: List[Dict]) -> str:
    """
    Use LLM to generate an intelligent context summary that preserves
    semantic markers for continuity.
    """
    try:
        from sakhi.apps.api.core.llm import call_llm
    except ImportError:
        logger.warning("[sessions] LLM unavailable for intelligent summary, using fallback")
        return _generate_simple_summary(turns)

    # Build conversation transcript
    transcript_lines = []
    for turn in turns:
        role_label = "User" if turn["role"] == "user" else "Sakhi"
        transcript_lines.append(f"{role_label}: {turn['text']}")

    transcript = "\n".join(transcript_lines)

    # Prompt for intelligent summarization
    summary_prompt = """You are creating a context summary for an ongoing conversation. This summary will be used to maintain continuity when the conversation continues later.

Extract and preserve the following in a structured format:

## People & Relationships
- List any people mentioned with their relationship to the user
- Example: "Mom (Priya) - user is worried about her health"

## Topics & References
- Key topics discussed with enough context to understand pronouns
- Example: "The project = user's wellness app startup idea, still in planning phase"

## Emotional Thread
- User's emotional state and any unresolved feelings
- Example: "Feeling overwhelmed about career decision, seeking clarity"

## Open Threads
- Questions asked but not fully resolved
- Topics the user might return to
- Example: "User mentioned wanting to discuss meditation routine later"

## Key Facts
- Important details that might be referenced later
- Example: "User has interview on Thursday, works in tech"

Be concise but preserve enough context that pronouns and references can be understood.

CONVERSATION:
{transcript}

CONTEXT SUMMARY:"""

    messages = [
        {"role": "system", "content": "You extract conversation context for continuity. Be concise and structured."},
        {"role": "user", "content": summary_prompt.format(transcript=transcript[:4000])},  # Limit transcript size
    ]

    try:
        model_name = os.getenv("MODEL_SUMMARY", os.getenv("MODEL_CONVERSATION", "gpt-4o-mini"))
        response = await call_llm(
            messages=messages,
            person_id="system",
            model=model_name,
        )
        summary = response if isinstance(response, str) else (response.get("text") or "")
        summary = summary.strip()

        if summary:
            return summary
    except Exception as e:
        logger.warning("[sessions] Intelligent summary failed: %s, using fallback", e)

    return _generate_simple_summary(turns)
