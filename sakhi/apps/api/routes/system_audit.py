from __future__ import annotations

from fastapi import APIRouter, Depends

from sakhi.apps.api.core.db import get_db

router = APIRouter()

SQL = """
SELECT
    NOW() AS audit_time,

    /* Journals */
    (SELECT MAX(created_at) FROM journal_entries) AS journal_latest,
    (SELECT COUNT(*) FROM journal_entries) AS journal_count,

    /* Embeddings */
    (SELECT MAX(created_at) FROM journal_embeddings) AS embedding_latest,
    (SELECT COUNT(*) FROM journal_embeddings) AS embedding_count,

    /* Reflections */
    (SELECT MAX(created_at) FROM reflections) AS reflections_latest,
    (SELECT COUNT(*) FROM reflections) AS reflections_count,

    /* Meta Reflection */
    (SELECT MAX(updated_at) FROM meta_reflection_scores) AS meta_latest,
    (SELECT COUNT(*) FROM meta_reflection_scores) AS meta_count,

    /* Personal model */
    (SELECT MAX(updated_at) FROM personal_model) AS personal_model_latest,
    (SELECT COUNT(*) FROM personal_model) AS personal_model_count,

    /* Rhythm forecast */
    (SELECT MAX(updated_at) FROM rhythm_forecasts) AS forecast_latest,
    (SELECT COUNT(*) FROM rhythm_forecasts) AS forecast_count,
    (
        SELECT COALESCE(
            (
                SELECT vector_dims(forecast_vector)
                FROM rhythm_forecasts
                WHERE forecast_vector IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 1
            ),
            0
        )
    ) AS forecast_vector_dims,

    /* Theme links */
    (SELECT MAX(updated_at) FROM theme_rhythm_links) AS theme_links_latest,
    (SELECT COUNT(*) FROM theme_rhythm_links) AS theme_links_count,

    /* Presence */
    (SELECT MAX(created_at) FROM presence_state) AS presence_latest,
    (SELECT COUNT(*) FROM presence_state) AS presence_count,

    /* Dialog state */
    (SELECT MAX(updated_at) FROM dialog_states) AS dialog_latest,
    (SELECT COUNT(*) FROM dialog_states) AS dialog_count,

    /* Analytics */
    (SELECT MAX(computed_at) FROM analytics_cache) AS analytics_latest,
    (SELECT COUNT(*) FROM analytics_cache) AS analytics_count,

    /* System events */
    (SELECT MAX(ts) FROM system_events) AS system_event_latest,
    (SELECT COUNT(*) FROM system_events) AS system_event_count,

    /* Debug traces */
    (SELECT MAX(created_at) FROM debug_traces) AS debug_latest,
    (SELECT COUNT(*) FROM debug_traces) AS debug_count
"""

@router.get("/system/audit")
async def system_audit(db=Depends(get_db)):
    row = await db.fetchrow(SQL)
    return dict(row)
