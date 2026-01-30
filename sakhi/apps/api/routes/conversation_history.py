"""Conversation history endpoints for loading and managing chat sessions."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.utils.person_resolver import resolve_person
from sakhi.apps.api.services.memory.sessions import (
    ensure_session,
    load_recent_turns,
    get_session_info,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/conversation", tags=["conversation-history"])


@router.get("/history")
async def get_conversation_history(
    request: Request,
    user: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session_slug: str = Query(default="converse"),
) -> JSONResponse:
    """
    Load conversation history for the authenticated user.

    Returns the most recent turns from the user's active session.
    """
    user_id, person_label, person_key = resolve_person(request, user)
    logger.info(
        "[conversation_history] Loading history for user=%s label=%s slug=%s limit=%s",
        user_id, person_label, session_slug, limit,
    )

    try:
        # Get or create session for this user
        session_id = await ensure_session(user_id, slug=session_slug)
        session_info = await get_session_info(session_id)

        # Load recent turns
        turns = await load_recent_turns(session_id, limit=limit)

        # Format for frontend
        # Map 'assistant' to 'sakhi' for frontend display
        messages: List[Dict[str, Any]] = []
        for turn in turns:
            role = turn.get("role")
            # Map 'assistant' to 'sakhi' for frontend consistency
            if role == "assistant":
                role = "sakhi"
            messages.append({
                "role": role,
                "content": turn.get("text"),
                "tone": turn.get("tone"),
                "archetype": turn.get("archetype"),
                "source": turn.get("source", "text"),
            })

        return JSONResponse({
            "messages": messages,
            "session_id": str(session_id),
            "session_info": {
                "title": session_info.get("title"),
                "slug": session_info.get("slug"),
                "status": session_info.get("status"),
            },
            "person_id": user_id,
            "count": len(messages),
        })
    except Exception as exc:
        logger.error("[conversation_history] Failed to load history: %s", exc)
        return JSONResponse(
            {"messages": [], "error": str(exc), "person_id": user_id},
            status_code=200,  # Return empty list on error to not break frontend
        )


@router.get("/sessions")
async def list_sessions(
    request: Request,
    user: str | None = Query(default=None),
    status_filter: str = Query(default="active"),
    limit: int = Query(default=10, ge=1, le=50),
) -> JSONResponse:
    """
    List conversation sessions for the user.
    """
    user_id, person_label, _ = resolve_person(request, user)

    try:
        sessions = await q(
            """
            SELECT id, slug, title, status, turn_count, created_at, last_active_at
            FROM conversation_sessions
            WHERE user_id = $1 AND ($2 = 'all' OR status = $2)
            ORDER BY last_active_at DESC NULLS LAST
            LIMIT $3
            """,
            user_id,
            status_filter,
            limit,
        )

        return JSONResponse({
            "sessions": [dict(s) for s in sessions] if sessions else [],
            "person_id": user_id,
        })
    except Exception as exc:
        logger.error("[conversation_history] Failed to list sessions: %s", exc)
        return JSONResponse(
            {"sessions": [], "error": str(exc)},
            status_code=200,
        )


__all__ = ["router"]
