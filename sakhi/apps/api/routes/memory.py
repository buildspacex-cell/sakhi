from __future__ import annotations

import datetime as dt
import logging
import uuid

from fastapi import APIRouter, Query, Request

from sakhi.apps.api.services.memory.recall import recall_advanced
from sakhi.apps.api.services.memory.memory_episodic import build_episodic_from_journals_v2
from sakhi.apps.api.services.memory.synthesis import (
    fetch_monthly_recaps,
    fetch_weekly_summaries,
    run_memory_synthesis,
)
from sakhi.apps.worker.tasks.weekly_rhythm_rollup_worker import run_weekly_rhythm_rollup
from sakhi.apps.worker.tasks.weekly_planner_pressure_worker import run_weekly_planner_pressure
from sakhi.apps.worker.tasks.weekly_signals_worker import run_weekly_signals_worker
from sakhi.apps.worker.tasks.turn_personal_model_update import run_turn_personal_model_update
from sakhi.apps.worker.tasks.weekly_reflection import generate_weekly_reflection, _fetch_weekly_signals
from sakhi.libs.schemas.settings import get_settings
from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.utils.person_resolver import resolve_person

router = APIRouter(tags=["memory"])
logger = logging.getLogger(__name__)


@router.get("/memory/recall")
async def recall_api(person_id: str = Query(...), q: str = Query(...), k: int = Query(5, ge=1, le=25)):
    return await recall_advanced(person_id, q, k=k)


@router.post("/memory/{person_id}/synthesis")
async def trigger_memory_synthesis(
    request: Request,
    person_id: str,
    horizon: str = Query("weekly", description="weekly or monthly"),
):
    resolved_id, person_label, person_key = resolve_person(request)
    logger.info(
        "ACTIVE_DEV_PERSON",
        extra={"person_id": resolved_id, "person_label": person_label, "person_key": person_key},
    )
    return await run_memory_synthesis(resolved_id, horizon=horizon)


@router.get("/memory/{person_id}/weekly")
async def get_weekly_summaries(
    request: Request,
    person_id: str,
    limit: int = Query(4, ge=1, le=12),
    debug: bool = Query(False, description="Run weekly pipeline immediately when true"),
    system_prompt_override: str | None = Query(None, alias="system_prompt_override", description="Optional override for weekly reflection system prompt"),
    user_prompt_override: str | None = Query(None, alias="user_prompt_override", description="Optional override for weekly reflection user prompt template"),
    system_prompt: str | None = Query(None, description="Optional override for weekly reflection system prompt (legacy name)"),
    user_prompt: str | None = Query(None, description="Optional override for weekly reflection user prompt template (legacy name)"),
):
    resolved_id, person_label, person_key = resolve_person(request)
    settings = get_settings()
    system_prompt_final = system_prompt_override or system_prompt
    user_prompt_final = user_prompt_override or user_prompt
    week_start_param = request.query_params.get("week_start")
    target_week_start = None
    if week_start_param:
        try:
            target_week_start = dt.datetime.fromisoformat(week_start_param).date()
        except Exception:
            target_week_start = None
    if settings.debug_weekly_pipeline or debug:
        logger.error(
            "WEEKLY_DEBUG: /memory/{id}/weekly orchestration start",
            extra={"person_id": resolved_id, "person_label": person_label, "person_key": person_key},
        )
        today = dt.datetime.utcnow().date()
        week_start = target_week_start or (today - dt.timedelta(days=today.weekday()))
        week_end = week_start + dt.timedelta(days=6)
        start_ts = dt.datetime.combine(week_start, dt.time.min)
        end_ts = start_ts + dt.timedelta(days=7)
        episodic_window = await q(
            "SELECT COUNT(*) AS count FROM memory_episodic WHERE user_id = $1 AND created_at >= $2 AND created_at < $3",
            resolved_id,
            start_ts,
            end_ts,
            one=True,
        )
        episodic_window_count = (episodic_window or {}).get("count", 0)
        if episodic_window_count == 0:
            logger.error("WEEKLY_DEBUG: episodic missing, using v2 episodic builder", extra={"person_id": resolved_id})
            build_stats = await build_episodic_from_journals_v2(
                person_id=resolved_id,
                start_ts=start_ts,
                end_ts=end_ts,
                source="weekly_debug",
            )
            logger.error("WEEKLY_DEBUG: episodic build stats", extra={"person_id": person_id, **build_stats})
        await run_weekly_rhythm_rollup(resolved_id)
        await run_weekly_planner_pressure(resolved_id)
        await run_weekly_signals_worker(resolved_id, target_week_start=target_week_start)
        await run_turn_personal_model_update(resolved_id)
        episodic_count = await q(
            "SELECT COUNT(*) FROM memory_episodic WHERE user_id = $1",
            resolved_id,
            one=True,
        )
        weekly_signals_count = await q(
            "SELECT COUNT(*) FROM memory_weekly_signals WHERE person_id = $1",
            resolved_id,
            one=True,
        )
        rhythm_rollup_count = await q(
            "SELECT COUNT(*) FROM rhythm_weekly_rollups WHERE person_id = $1",
            resolved_id,
            one=True,
        )
        planner_pressure_count = await q(
            "SELECT COUNT(*) FROM planner_weekly_pressure WHERE person_id = $1",
            resolved_id,
            one=True,
        )
        row = await q("SELECT longitudinal_state FROM personal_model WHERE person_id = $1", resolved_id, one=True)
        longitudinal_state = row.get("longitudinal_state") if row else {}
        logger.error(
            "WEEKLY_BACKEND_INPUT_COUNTS",
            extra={
                "episodic": episodic_count,
                "weekly_signals": weekly_signals_count,
                "rhythm_rollups": rhythm_rollup_count,
                "planner_pressure": planner_pressure_count,
                "longitudinal_present": bool(longitudinal_state),
            },
        )
        reflection = await generate_weekly_reflection(
            resolved_id,
            longitudinal_state or {},
            system_prompt_override=system_prompt_final,
            user_prompt_override=user_prompt_final,
            include_debug=True,
            target_week_start=target_week_start,
        )
        llm_debug = reflection.pop("_debug", None)
        weekly_signals = await _fetch_weekly_signals(resolved_id, target_week_start)
        journal_rows = await q(
            """
            SELECT id, content, mood, tags, created_at
            FROM journal_entries
            WHERE user_id = $1 AND created_at >= $2 AND created_at < $3
            ORDER BY created_at DESC
            LIMIT 50
            """,
            resolved_id,
            start_ts,
            end_ts,
        )
        journals = []
        for row in journal_rows:
            journals.append(
                {
                    "id": str(row.get("id")),
                    "content": row.get("content") or "",
                    "created_at": row.get("created_at"),
                    "mood": row.get("mood"),
                    "tags": row.get("tags") or [],
                }
            )
        response = {
            "status": "ok",
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "reflection": reflection,
            "debug": {
                "llm": llm_debug,
                "journals": journals,
                "weekly_signals": weekly_signals,
                "longitudinal_state": longitudinal_state,
            },
        }
        logger.error(
            "WEEKLY_BACKEND_RESPONSE",
            extra={
                "person_id": person_id,
                "has_reflection": bool(response.get("reflection")),
                "response_keys": list(response.keys()),
                "status": response.get("status"),
            },
        )
        return response
    logger.info(
        "ACTIVE_DEV_PERSON",
        extra={"person_id": resolved_id, "person_label": person_label, "person_key": person_key},
    )
    return await fetch_weekly_summaries(resolved_id, limit=limit)


@router.post("/memory/dev/weekly/run")
async def run_weekly_flow_dev(request: Request):
    """
    Dev-only helper to run the full weekly flow synchronously with optional journal injection.
    Payload (JSON):
    {
      "user": "a",
      "week_start": "2023-05-01",
      "journals": [
        {"content": "...", "created_at": "2023-05-01T08:00:00Z"},
        ...
      ]
    }
    """
    payload = await request.json()
    user = payload.get("user") or "a"
    week_start_param = payload.get("week_start")
    journals = payload.get("journals") or []
    resolved_id, _, _ = resolve_person(request)
    target_week_start = None
    if week_start_param:
        try:
            target_week_start = dt.datetime.fromisoformat(week_start_param).date()
        except Exception:
            target_week_start = None

    # Insert journals if provided
    for j in journals:
        content = (j or {}).get("content") or ""
        created_raw = (j or {}).get("created_at")
        if not content.strip() or not created_raw:
            continue
        try:
            created_at = dt.datetime.fromisoformat(created_raw)
        except Exception:
            continue
        await dbexec(
            """
            INSERT INTO journal_entries (id, user_id, content, layer, created_at, updated_at)
            VALUES ($1, $2, $3, 'journal', $4, $4)
            ON CONFLICT (id) DO NOTHING
            """,
            uuid.uuid4(),
            resolved_id,
            content,
            created_at,
        )

    # Run weekly pipeline for the requested week
    await run_weekly_rhythm_rollup(resolved_id)
    await run_weekly_planner_pressure(resolved_id)
    await run_weekly_signals_worker(resolved_id, target_week_start=target_week_start)
    await run_turn_personal_model_update(resolved_id)

    row = await q("SELECT longitudinal_state FROM personal_model WHERE person_id = $1", resolved_id, one=True)
    longitudinal_state = row.get("longitudinal_state") if row else {}
    reflection = await generate_weekly_reflection(
        resolved_id,
        longitudinal_state or {},
        include_debug=True,
        target_week_start=target_week_start,
    )
    llm_debug = reflection.pop("_debug", None)
    weekly_signals = await _fetch_weekly_signals(resolved_id, target_week_start)
    return {
        "status": "ok",
        "week_start": target_week_start.isoformat() if target_week_start else None,
        "reflection": reflection,
        "debug": {
            "llm": llm_debug,
            "weekly_signals": weekly_signals,
        },
    }


@router.get("/memory/dev/weekly")
async def get_weekly_summaries_dev(
    request: Request,
    limit: int = Query(4, ge=1, le=12),
    debug: bool = Query(False, description="Run weekly pipeline immediately when true"),
    system_prompt_override: str | None = Query(None, alias="system_prompt_override", description="Optional override for weekly reflection system prompt"),
    user_prompt_override: str | None = Query(None, alias="user_prompt_override", description="Optional override for weekly reflection user prompt template"),
    system_prompt: str | None = Query(None, description="Optional override for weekly reflection system prompt (legacy name)"),
    user_prompt: str | None = Query(None, description="Optional override for weekly reflection user prompt template (legacy name)"),
):
    # Delegate to the main handler; path param is unused since resolution happens inside.
    return await get_weekly_summaries(
        request,
        person_id="dev",
        limit=limit,
        debug=debug,
        system_prompt_override=system_prompt_override,
        user_prompt_override=user_prompt_override,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


@router.get("/memory/{person_id}/monthly")
async def get_monthly_recaps(person_id: str, limit: int = Query(3, ge=1, le=6)):
    return await fetch_monthly_recaps(person_id, limit=limit)


__all__ = ["router"]
