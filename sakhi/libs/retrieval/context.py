"""Utilities for assembling retrieval context used in reflective prompts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sakhi.libs.schemas import fetch_all


async def build_reflection_context(
    user_id: str,
    theme: str,
    *,
    limit: int = 5,
) -> Dict[str, Any]:
    """Collect recent salient journal entries and related tasks for reflection."""

    if limit <= 0:
        raise ValueError("limit must be positive")

    window_start = datetime.now(timezone.utc) - timedelta(days=14)

    journal_rows = await fetch_all(
        """
        SELECT id,
               coalesce(title, '') AS title,
               content,
               (facets->>'salience')::numeric AS salience,
               created_at
        FROM journal_entries
        WHERE user_id = $1
          AND created_at >= $2
        ORDER BY COALESCE((facets->>'salience')::numeric, 0) DESC,
                 created_at DESC
        LIMIT $3
        """,
        user_id,
        window_start,
        limit,
    )

    journals: List[Dict[str, Any]] = []
    for row in journal_rows:
        journals.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or "",
                "content": row.get("content") or "",
                "salience": float(row.get("salience") or 0.0),
                "created_at": row.get("created_at"),
            }
        )

    theme_pattern = f"%{theme}%"
    task_rows = await fetch_all(
        """
        SELECT id,
               title,
               coalesce(description, '') AS description,
               status,
               due_at,
               created_at
        FROM tasks
        WHERE user_id = $1
          AND (
                title ILIKE $2
             OR description ILIKE $2
          )
        ORDER BY COALESCE(due_at, created_at) ASC
        LIMIT $3
        """,
        user_id,
        theme_pattern,
        limit,
    )

    tasks: List[Dict[str, Any]] = []
    for row in task_rows:
        tasks.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or "",
                "description": row.get("description") or "",
                "status": row.get("status") or "unknown",
                "due_at": row.get("due_at"),
                "created_at": row.get("created_at"),
            }
        )

    return {
        "theme": theme,
        "journals": journals,
        "tasks": tasks,
        "window_start": window_start,
        "count": {
            "journals": len(journals),
            "tasks": len(tasks),
        },
    }


__all__ = ["build_reflection_context"]

