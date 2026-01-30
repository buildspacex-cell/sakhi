"""
Diagnostics Endpoint for Founding Team

Shows what was updated in the DB after a conversation turn:
- Recent journal entries
- Memory episodic updates
- Personal model state changes
- Worker job history

GET /lab/diagnostics?email=user@example.com
POST /lab/diagnostics/turn - Post a test message and see what gets updated
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from sakhi.apps.api.core.db import q, exec as dbexec

router = APIRouter(prefix="/lab/diagnostics", tags=["diagnostics"])
logger = logging.getLogger(__name__)


class TurnTestRequest(BaseModel):
    """Request to test a conversation turn."""
    email: str
    text: str


class DiagnosticsResponse(BaseModel):
    """Response showing what was updated."""
    user: Dict[str, Any]
    recent_entries: List[Dict[str, Any]]
    recent_memories: List[Dict[str, Any]]
    personal_model_summary: Dict[str, Any]
    memory_counts: Dict[str, int]
    last_updated: Dict[str, Any]


async def _get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email from profiles table."""
    row = await q(
        "SELECT user_id, email, created_at, updated_at FROM profiles WHERE email = $1",
        email,
        one=True,
    )
    return dict(row) if row else None


async def _get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID from profiles table."""
    row = await q(
        "SELECT user_id, email, created_at, updated_at FROM profiles WHERE user_id = $1",
        user_id,
        one=True,
    )
    return dict(row) if row else None


async def _get_recent_entries(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent journal entries."""
    rows = await q("""
        SELECT id, content, layer, created_at
        FROM journal_entries
        WHERE person_id = $1::uuid
        ORDER BY created_at DESC
        LIMIT $2
    """, user_id, limit)
    return [
        {
            "id": str(r["id"]),
            "content": (r["content"][:200] + "..." if r["content"] and len(r["content"]) > 200 else r["content"]) or "(no content)",
            "layer": r["layer"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def _get_recent_memories(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent episodic memories."""
    rows = await q("""
        SELECT id, text, created_at
        FROM memory_episodic
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, user_id, limit)
    return [
        {
            "id": str(r["id"]),
            "text": (r["text"][:200] + "..." if r["text"] and len(r["text"]) > 200 else r["text"]) or "(no text)",
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def _get_memory_counts(user_id: str) -> Dict[str, int]:
    """Get counts of various memory types."""
    episodic = await q(
        "SELECT COUNT(*) as count FROM memory_episodic WHERE user_id = $1",
        user_id,
        one=True,
    )
    entries = await q(
        "SELECT COUNT(*) as count FROM journal_entries WHERE person_id = $1::uuid",
        user_id,
        one=True,
    )
    nodes = await q(
        "SELECT COUNT(*) as count FROM memory_nodes WHERE person_id = $1::uuid",
        user_id,
        one=True,
    )
    return {
        "episodic_memories": episodic["count"] if episodic else 0,
        "journal_entries": entries["count"] if entries else 0,
        "memory_nodes": nodes["count"] if nodes else 0,
    }


async def _get_personal_model_summary(user_id: str) -> Dict[str, Any]:
    """Get summary of personal model state."""
    row = await q("""
        SELECT
            person_id,
            updated_at,
            CASE WHEN body_state IS NOT NULL THEN true ELSE false END as has_body_state,
            CASE WHEN emotion_state IS NOT NULL THEN true ELSE false END as has_emotion_state,
            CASE WHEN soul_state IS NOT NULL THEN true ELSE false END as has_soul_state,
            CASE WHEN rhythm_state IS NOT NULL THEN true ELSE false END as has_rhythm_state,
            CASE WHEN identity_momentum_state IS NOT NULL THEN true ELSE false END as has_identity_momentum,
            CASE WHEN longitudinal_state IS NOT NULL THEN true ELSE false END as has_longitudinal,
            last_seen
        FROM personal_model
        WHERE person_id = $1::uuid
    """, user_id, one=True)

    if not row:
        return {"exists": False}

    return {
        "exists": True,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
        "states": {
            "body_state": row["has_body_state"],
            "emotion_state": row["has_emotion_state"],
            "soul_state": row["has_soul_state"],
            "rhythm_state": row["has_rhythm_state"],
            "identity_momentum": row["has_identity_momentum"],
            "longitudinal": row["has_longitudinal"],
        }
    }


async def _get_last_updated(user_id: str) -> Dict[str, Any]:
    """Get timestamps of last updates across tables."""
    personal_model = await q(
        "SELECT updated_at FROM personal_model WHERE person_id = $1::uuid",
        user_id,
        one=True,
    )
    last_entry = await q(
        "SELECT created_at FROM journal_entries WHERE person_id = $1::uuid ORDER BY created_at DESC LIMIT 1",
        user_id,
        one=True,
    )
    last_memory = await q(
        "SELECT created_at FROM memory_episodic WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        user_id,
        one=True,
    )

    return {
        "personal_model": personal_model["updated_at"].isoformat() if personal_model and personal_model["updated_at"] else None,
        "last_journal_entry": last_entry["created_at"].isoformat() if last_entry and last_entry["created_at"] else None,
        "last_memory": last_memory["created_at"].isoformat() if last_memory and last_memory["created_at"] else None,
    }


@router.get("")
async def get_diagnostics(
    email: Optional[str] = Query(None, description="User email"),
    user_id: Optional[str] = Query(None, description="User ID (alternative to email)"),
) -> DiagnosticsResponse:
    """
    Get diagnostics for a user - shows what's in the DB.

    Use either email or user_id to identify the user.
    """
    if not email and not user_id:
        raise HTTPException(status_code=400, detail="Provide either email or user_id")

    # Resolve user
    if email:
        user = await _get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found: {email}")
    else:
        user = await _get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    uid = user["user_id"]

    # Gather diagnostics
    recent_entries = await _get_recent_entries(uid)
    recent_memories = await _get_recent_memories(uid)
    memory_counts = await _get_memory_counts(uid)
    personal_model_summary = await _get_personal_model_summary(uid)
    last_updated = await _get_last_updated(uid)

    return DiagnosticsResponse(
        user={
            "user_id": str(uid),
            "email": user["email"],
            "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        },
        recent_entries=recent_entries,
        recent_memories=recent_memories,
        personal_model_summary=personal_model_summary,
        memory_counts=memory_counts,
        last_updated=last_updated,
    )


@router.post("/turn")
async def test_turn(request: TurnTestRequest) -> Dict[str, Any]:
    """
    Post a test message and see what gets updated.

    1. Creates a journal entry
    2. Triggers memory workers (inline)
    3. Returns before/after comparison
    """
    from sakhi.apps.api.services.ingestion.unified_ingest import ingest_heavy
    from sakhi.apps.worker.tasks.episodic_consolidation_v21 import run_episodic_consolidation_v21

    # Resolve user
    user = await _get_user_by_email(request.email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {request.email}")

    uid = user["user_id"]

    # Snapshot before
    before_counts = await _get_memory_counts(uid)
    before_model = await _get_personal_model_summary(uid)

    # Create entry
    entry_id = str(uuid4())
    ts = dt.datetime.utcnow()

    await dbexec("""
        INSERT INTO journal_entries (id, user_id, person_id, content, layer, created_at)
        VALUES ($1::uuid, $2::uuid, $2::uuid, $3, 'conversation', $4)
    """, entry_id, uid, request.text, ts)

    # Run memory ingestion (inline for testing)
    try:
        await ingest_heavy(
            person_id=uid,
            entry_id=entry_id,
            text=request.text,
            ts=ts,
        )
        ingest_status = "success"
    except Exception as e:
        ingest_status = f"error: {str(e)}"

    # Run episodic consolidation (inline for testing)
    try:
        await run_episodic_consolidation_v21(
            uid,
            {"text": request.text, "entry_id": entry_id, "ts": ts.isoformat()},
        )
        episodic_status = "success"
    except Exception as e:
        episodic_status = f"error: {str(e)}"

    # Snapshot after
    after_counts = await _get_memory_counts(uid)
    after_model = await _get_personal_model_summary(uid)

    return {
        "entry_id": entry_id,
        "text": request.text[:100] + "..." if len(request.text) > 100 else request.text,
        "workers": {
            "ingest_heavy": ingest_status,
            "episodic_consolidation": episodic_status,
        },
        "changes": {
            "memory_counts": {
                "before": before_counts,
                "after": after_counts,
                "delta": {
                    k: after_counts[k] - before_counts[k]
                    for k in before_counts
                }
            },
            "personal_model": {
                "before_updated": before_model.get("updated_at"),
                "after_updated": after_model.get("updated_at"),
            }
        }
    }


@router.get("/worker-status")
async def get_worker_status() -> Dict[str, Any]:
    """
    Get status of the v2 worker architecture.

    Shows which workers run per-turn vs daily.
    """
    return {
        "architecture": "v2",
        "per_turn_workers": [
            {"name": "turn_memory_update", "description": "Ingests text into memory"},
            {"name": "episodic_consolidation_v21", "description": "Creates episodic memories"},
        ],
        "daily_workers": [
            {"name": "ayurvedic_pipeline", "description": "Updates body/constitution state"},
            {"name": "identity_momentum_deep", "description": "Tracks identity patterns"},
            {"name": "emotion_soul_rhythm_deep", "description": "Processes emotional patterns"},
            {"name": "esr_daily", "description": "Emotion state refresh"},
            {"name": "soul_refresh", "description": "Updates soul/values state"},
        ],
        "weekly_workers": [
            {"name": "weekly_learning", "description": "Learns from week's patterns"},
            {"name": "pattern_crystallization", "description": "Crystallizes recurring patterns"},
            {"name": "goal_evolver", "description": "Updates goals based on progress"},
        ],
    }
