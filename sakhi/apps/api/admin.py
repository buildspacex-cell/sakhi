"""Administrative endpoints for metrics, costs, and data export."""

from __future__ import annotations

import secrets
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from sakhi.libs.flags.flags import set_flag
from sakhi.libs.schemas.db import get_async_pool
from sakhi.apps.api.services.memory.sessions import load_recent_turns, get_summary, set_summary
from sakhi.apps.api.services.memory.summarize import roll_summary
from sakhi.apps.api.services.memory.session_vectors import upsert_session_vector

SUMMARY_CONTEXT_LIMIT = 20

admin = APIRouter(prefix="/admin")


@admin.get("/metrics")
async def metrics() -> Dict[str, Any]:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        reqs_row = await connection.fetchrow(
            "SELECT COUNT(*) AS c FROM request_logs WHERE created_at > now() - interval '24 hours'"
        )
        cost_row = await connection.fetchrow(
            "SELECT COALESCE(SUM(cost_usd), 0) AS c FROM token_usage WHERE created_at > now() - interval '24 hours'"
        )
        incidents_rows = await connection.fetch(
            "SELECT kind, COUNT(*) AS c FROM incidents WHERE created_at > now() - interval '24 hours' GROUP BY kind"
        )

    req_count = reqs_row.get("c", 0) if reqs_row else 0
    cost_total = float(cost_row.get("c", 0.0) if cost_row else 0.0)
    incidents = [dict(row) for row in incidents_rows]
    return {"req_24h": req_count, "cost_24h": cost_total, "incidents_24h": incidents}


@admin.get("/costs")
async def costs() -> Dict[str, Any]:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT model,
                   SUM(tokens_in) AS tin,
                   SUM(tokens_out) AS tout,
                   SUM(cost_usd) AS cost
            FROM token_usage
            GROUP BY model
            ORDER BY cost DESC
            """
        )
    return {"by_model": [dict(row) for row in rows]}


@admin.get("/status/router")
async def router_status() -> Dict[str, bool]:
    from sakhi.libs.llm_router.router import LLMRouter

    ok = True
    try:
        _ = LLMRouter()
    except Exception:
        ok = False
    return {"router_constructed": ok}


@admin.get("/export")
async def export(user_id: str) -> Dict[str, Any]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    pool = await get_async_pool()
    datasets: Dict[str, Any] = {}
    async with pool.acquire() as connection:
        queries = [
            (
                "journals",
                "SELECT * FROM export_journals_redacted WHERE user_id = $1 ORDER BY created_at",
            ),
            (
                "embeddings",
                """
                SELECT entry_id, left(embedding::text, 60) || '...' AS preview
                FROM journal_embeddings
                WHERE entry_id IN (
                    SELECT id FROM journal_entries WHERE user_id = $1
                )
                """,
            ),
            (
                "tasks",
                "SELECT * FROM tasks WHERE user_id = $1 ORDER BY created_at",
            ),
            (
                "reflections",
                "SELECT * FROM reflections WHERE user_id = $1 ORDER BY created_at",
            ),
            (
                "body_signals",
                "SELECT * FROM body_signals WHERE user_id = $1 ORDER BY at",
            ),
            (
                "alignment",
                "SELECT * FROM alignment_scores WHERE user_id = $1 ORDER BY created_at",
            ),
        ]
        for key, sql in queries:
            records = await connection.fetch(sql, user_id)
            datasets[key] = [dict(record) for record in records]

    return datasets


@admin.post("/flag")
async def flag(key: str, enabled: bool) -> Dict[str, bool]:
    await set_flag(key, enabled)
    return {"ok": True}


@admin.post("/pilot/add")
async def pilot_add(user_id: str) -> Dict[str, str]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    api_key = secrets.token_urlsafe(24)
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO pilot_users(user_id, api_key)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET api_key = EXCLUDED.api_key
            """,
            user_id,
            api_key,
        )

    return {"user_id": user_id, "api_key": api_key}


@admin.post("/sessions/merge")
async def merge_sessions(source_id: str, target_id: str) -> Dict[str, Any]:
    if not source_id or not target_id:
        raise HTTPException(status_code=400, detail="source_id and target_id are required")
    if source_id == target_id:
        raise HTTPException(status_code=400, detail="source_id and target_id must differ")

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        source = await connection.fetchrow(
            "SELECT id, user_id, slug, title FROM conversation_sessions WHERE id = $1",
            source_id,
        )
        target = await connection.fetchrow(
            "SELECT id, user_id, slug, title FROM conversation_sessions WHERE id = $1",
            target_id,
        )

        if not source or not target:
            raise HTTPException(status_code=404, detail="One or both sessions not found")
        if source["user_id"] != target["user_id"]:
            raise HTTPException(status_code=400, detail="Sessions belong to different users")

        await connection.execute(
            "UPDATE conversation_turns SET session_id = $2 WHERE session_id = $1",
            source_id,
            target_id,
        )
        await connection.execute(
            "UPDATE conversation_sessions SET status = 'archived', archived_at = now() WHERE id = $1",
            source_id,
        )
        await connection.execute(
            """
            UPDATE conversation_sessions
            SET turn_count = (SELECT COUNT(*) FROM conversation_turns WHERE session_id = $1),
                last_active_at = now()
            WHERE id = $1
            """,
            target_id,
        )

    target_summary = await get_summary(target_id)
    source_summary = await get_summary(source_id)
    combined_turns = await load_recent_turns(target_id, limit=SUMMARY_CONTEXT_LIMIT)

    merged_summary = await roll_summary(
        f"{target_summary}\n{source_summary}".strip(),
        combined_turns,
    )
    if merged_summary:
        await set_summary(target_id, merged_summary)
        await upsert_session_vector(target_id, target.get("title"), merged_summary)

    return {
        "merged": True,
        "source": source_id,
        "target": target_id,
        "turnCount": len(combined_turns),
        "summary": merged_summary,
    }
