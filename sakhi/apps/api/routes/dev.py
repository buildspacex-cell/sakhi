"""
Development-only routes for testing and debugging.

WARNING: These routes are destructive and should NEVER be enabled in production.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sakhi.apps.api.core.db import exec as dbexec, q

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["dev"])

# Only enable in development
IS_DEV = os.getenv("ENV", "development") in {"development", "dev", "local"}


class ResetUserDataRequest(BaseModel):
    person_id: str


class ResetUserDataResponse(BaseModel):
    success: bool
    person_id: str
    tables_cleared: List[str]
    errors: List[str]


# Tables to clear, in order (respecting foreign key constraints)
# Format: (table_name, id_column)
TABLES_TO_CLEAR = [
    # Memory and episodic
    ("memory_short_term", "person_id"),
    ("memory_episodic", "person_id"),
    ("memory_episodic", "user_id"),  # Some rows use user_id
    ("memory_context_cache", "person_id"),
    ("memory_weekly_signals", "person_id"),
    ("memory_weekly_summaries", "person_id"),
    ("memory_nodes", "person_id"),
    ("memory_edges", "person_id"),

    # Journal and entries (journal_inference cascades from journal_entries)
    ("journal_embeddings", "entry_id"),  # Will be handled via cascade from journal_entries
    ("journal_entries", "user_id"),

    # Soul and emotion
    ("soul_values", "person_id"),
    ("soul_state", "person_id"),
    ("emotion_state", "person_id"),

    # Rhythm
    ("rhythm_state", "person_id"),
    ("rhythm_daily_curve", "person_id"),
    ("rhythm_weekly_rollups", "person_id"),
    ("rhythm_planner_alignment", "person_id"),

    # Conversation
    ("conversation_turns", "user_id"),
    ("conversation_sessions", "user_id"),
    ("conversation_state", "person_id"),
    ("dialog_states", "user_id"),

    # Reflection and inquiry
    ("reflection_inquiry_embeddings", "person_id"),
    ("reflection_inquiry_turns", "person_id"),
    ("reflections", "user_id"),

    # Intents and planning
    ("intents", "user_id"),
    ("intent_evolution", "person_id"),
    ("planner_weekly_pressure", "person_id"),
    ("plan_tasks", "person_id"),
    ("plan_goals", "person_id"),

    # Cache tables
    ("daily_reflection_cache", "person_id"),
    ("daily_closure_cache", "person_id"),
    ("morning_preview_cache", "person_id"),
    ("morning_ask_cache", "person_id"),
    ("morning_momentum_cache", "person_id"),
    ("micro_momentum_cache", "person_id"),
    ("micro_recovery_cache", "person_id"),
    ("focus_path_cache", "person_id"),
    ("mini_flow_cache", "person_id"),
    ("micro_journey_cache", "person_id"),

    # Events and tasks
    ("events", "user_id"),
    ("tasks", "user_id"),

    # Presence
    ("presence_outreach", "user_id"),

    # User profile and model (do these last)
    ("user_memories", "user_id"),
    ("user_profile", "user_id"),
    ("personal_model", "person_id"),

    # Auth users - reset onboarding but keep the record
    # ("auth_users", "id"),  # Don't delete, just reset onboarding
]


@router.post("/reset-user-data", response_model=ResetUserDataResponse)
async def reset_user_data(request: ResetUserDataRequest) -> Dict[str, Any]:
    """
    Reset ALL data for a given person_id across all tables.

    WARNING: This is destructive and irreversible!
    """
    if not IS_DEV:
        raise HTTPException(status_code=403, detail="Not available in production")

    person_id = request.person_id
    if not person_id:
        raise HTTPException(status_code=400, detail="person_id is required")

    logger.warning("[DEV] Resetting all data for person_id=%s", person_id)

    tables_cleared: List[str] = []
    errors: List[str] = []

    for table_name, id_column in TABLES_TO_CLEAR:
        try:
            # Check if table exists first
            check = await q(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = $1
                )
                """,
                table_name,
                one=True,
            )
            if not check or not check.get("exists"):
                continue

            # Delete all rows for this person
            await dbexec(
                f"DELETE FROM {table_name} WHERE {id_column} = $1",
                person_id,
            )
            tables_cleared.append(f"{table_name}.{id_column}")
            logger.info("[DEV] Cleared %s.%s for person_id=%s", table_name, id_column, person_id)
        except Exception as e:
            error_msg = f"{table_name}.{id_column}: {str(e)}"
            errors.append(error_msg)
            logger.warning("[DEV] Failed to clear %s: %s", table_name, e)

    # Reset onboarding status in auth_users (don't delete the record)
    try:
        await dbexec(
            """
            UPDATE auth_users
            SET onboarding_completed_at = NULL
            WHERE id = $1
            """,
            person_id,
        )
        tables_cleared.append("auth_users (onboarding reset)")
    except Exception as e:
        errors.append(f"auth_users reset: {str(e)}")

    logger.warning(
        "[DEV] Reset complete for person_id=%s: cleared=%d, errors=%d",
        person_id,
        len(tables_cleared),
        len(errors),
    )

    return {
        "success": len(errors) == 0,
        "person_id": person_id,
        "tables_cleared": tables_cleared,
        "errors": errors,
    }


__all__ = ["router"]
