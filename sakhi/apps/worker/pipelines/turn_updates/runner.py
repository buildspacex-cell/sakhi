from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
from collections import deque
import datetime as dt

from sakhi.apps.api.services.ingestion.unified_ingest import ingest_heavy
from sakhi.apps.api.services.planner.engine import planner_commit, planner_suggest
from sakhi.apps.api.services.rhythm.engine import run_rhythm_engine
from sakhi.apps.worker.tasks.rhythm_forecast import run_rhythm_forecast
from core.workers.signals.neutral_signal_extraction_worker import run_neutral_signal_extraction_worker
from sakhi.apps.api.services.persona.session_tuning import update_session_persona
from sakhi.apps.api.services.soul.engine import run_soul_engine
from sakhi.apps.api.services.growth.loop import sync_growth_from_planner
from sakhi.apps.api.services.planner.rhythm_fusion import compute_rhythm_planner_alignment
from sakhi.apps.logic.relationship_engine import update_from_turn
from sakhi.apps.logic.insight import insight_engine
from sakhi.apps.logic.brain import brain_engine
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.api.services.journaling.enrich import enrich_journal_entry
from sakhi.apps.api.services.memory_graph.graph import build_graph_from_enrichment
from sakhi.apps.api.services.memory_graph.persist import persist_enrichment, persist_memory_graph
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.worker.tasks.episodic_consolidation_v21 import run_episodic_consolidation_v21
from sakhi.apps.worker.tasks.ayurvedic_pipeline import run_ayurvedic_pipeline

LOGGER = logging.getLogger(__name__)
_PROCESSED_MAX = 1000
_processed_jobs: deque[str] = deque()
_processed_set: set[str] = set()


def process_turn_job(*, job_type: str, turn_id: str, person_id: str, payload: Dict[str, Any]) -> None:
    asyncio.run(_process(job_type, turn_id, person_id, payload))


async def _process(job_type: str, turn_id: str, person_id: str, payload: Dict[str, Any]) -> None:
    resolved_id = await resolve_person_id(person_id) or person_id
    job_key = f"{job_type}:{turn_id}"
    if job_key in _processed_set:
        LOGGER.info("Skipping duplicate turn job type=%s turn=%s", job_type, turn_id)
        return
    _processed_set.add(job_key)
    _processed_jobs.append(job_key)
    if len(_processed_jobs) > _PROCESSED_MAX:
        old = _processed_jobs.popleft()
        _processed_set.discard(old)

    LOGGER.info("----- TURN JOB BEGIN ----- type=%s turn=%s person=%s -----", job_type, turn_id, resolved_id)
    if job_type == "turn_memory_update":
        await _handle_memory_update(turn_id, resolved_id, payload)
    elif job_type == "turn_planner_update":
        await _handle_planner_update(resolved_id, payload)
    elif job_type == "turn_persona_update":
        await _handle_persona_update(resolved_id, payload)
    elif job_type == "turn_rhythm_update":
        await _handle_rhythm_update(resolved_id, payload)
    elif job_type == "rhythm_forecast":
        await _handle_rhythm_forecast(resolved_id)
    elif job_type == "turn_insight_update":
        await _handle_insight_update(resolved_id, payload)
    elif job_type == "brain_refresh":
        await _handle_brain_refresh(resolved_id, payload)
    elif job_type == "journal_enrich":
        await _handle_journal_enrich(resolved_id, payload)
    elif job_type == "episodic_consolidation_v21":
        await run_episodic_consolidation_v21(resolved_id, payload)
    elif job_type == "ayurvedic_pipeline":
        try:
            result = await run_ayurvedic_pipeline(resolved_id)
            LOGGER.info(
                "[AyurvedicPipeline] finished",
                extra={
                    "person_id": resolved_id,
                    "executed": (result or {}).get("executed"),
                },
            )
        except Exception as exc:
            LOGGER.error(
                "[AyurvedicPipeline] failed",
                extra={"person_id": resolved_id, "error": str(exc)},
            )
            raise
    elif job_type == "neutral_signal_extraction":
        try:
            result = await run_neutral_signal_extraction_worker(resolved_id, dt.datetime.utcnow(), mode="pipeline")
            LOGGER.info(
                "[NeutralSignalExtraction] finished",
                extra={"person_id": resolved_id, "outputs": result.get("outputs")},
            )
        except Exception as exc:
            LOGGER.error(
                "[NeutralSignalExtraction] failed",
                extra={"person_id": resolved_id, "error": str(exc)},
            )
            raise
    else:
        LOGGER.warning("Unknown turn job type=%s", job_type)


async def _handle_memory_update(turn_id: str, person_id: str, payload: Dict[str, Any]) -> None:
    text = payload.get("text") or ""
    if not text:
        return
    entry_id = payload.get("entry_id") or turn_id
    layer = payload.get("layer") or "journal"
    ts_raw = payload.get("ts")
    ts = ts_raw
    if isinstance(ts_raw, str):
        try:
            ts = dt.datetime.fromisoformat(ts_raw)
        except Exception:
            ts = None
    if not isinstance(ts, dt.datetime):
        ts = dt.datetime.utcnow()
    LOGGER.info(
        "[MemoryWorker] ingest start entry=%s person=%s layer=%s len_text=%s ts=%s",
        entry_id,
        person_id,
        layer,
        len(text),
        payload.get("ts"),
    )
    await ingest_heavy(
        person_id=person_id,
        entry_id=entry_id,
        text=text,
        ts=ts,
    )
    LOGGER.info("[MemoryWorker] ingest done entry=%s person=%s", entry_id, person_id)


async def _handle_planner_update(person_id: str, payload: Dict[str, Any]) -> None:
    try:
        text = payload.get("text") or ""
        if not text:
            return
        bundle = await planner_suggest(person_id, text)
        plan_graph = (bundle or {}).get("plan_graph") or {}
        if plan_graph.get("tasks"):
            await planner_commit(person_id, plan_graph)
            LOGGER.info("Planner worker committed tasks person=%s counts=%s", person_id, {k: len(v) for k, v in plan_graph.items() if isinstance(v, list)})
        await sync_growth_from_planner(person_id, plan_graph or bundle)
        await compute_rhythm_planner_alignment(person_id, plan_graph or {})
    except Exception as exc:
        LOGGER.warning("turn_planner_update failed person=%s error=%s", person_id, exc)


async def _handle_persona_update(person_id: str, payload: Dict[str, Any]) -> None:
    try:
        text = payload.get("text", "")
        await update_session_persona(person_id, text)
        await run_soul_engine(person_id)
        try:
            from sakhi.apps.api.services.narrative.engine import run_narrative_engine

            await run_narrative_engine(person_id)
        except Exception as exc:
            LOGGER.warning("[Narrative] run failed person=%s error=%s", person_id, exc)
        # Relationship: nudge trust/attunement based on turn emotion/pushback.
        try:
            facets = payload.get("facets") or {}
            emotion = facets.get("emotion") if isinstance(facets, dict) else {}
            sentiment = None
            if isinstance(emotion, dict):
                sentiment = emotion.get("mood") or emotion.get("sentiment")
            lower_text = (text or "").lower()
            pushback = any(phrase in lower_text for phrase in ["stop", "back off", "no more", "leave me"])
            await update_from_turn(person_id, sentiment=sentiment, pushback=pushback)
        except Exception as exc:
            LOGGER.warning("[Relationship] turn hook failed person=%s error=%s", person_id, exc)
        LOGGER.info("Persona update + soul refresh person=%s", person_id)
    except Exception as exc:
        LOGGER.warning("turn_persona_update failed person=%s error=%s", person_id, exc)


async def _handle_rhythm_update(person_id: str, payload: Dict[str, Any]) -> None:
    try:
        text = payload.get("text")
        result = await run_rhythm_engine(person_id, text=text)
        LOGGER.info(
            "Rhythm worker refreshed state person=%s energy=%.2f fatigue=%.2f stress=%.2f",
            person_id,
            result.get("state", {}).get("body_energy", 0.0),
            result.get("state", {}).get("fatigue_level", 0.0),
            result.get("state", {}).get("stress_level", 0.0),
        )
    except Exception as exc:
        LOGGER.warning("turn_rhythm_update failed person=%s error=%s", person_id, exc)


async def _handle_rhythm_forecast(person_id: str) -> None:
    try:
        result = await run_rhythm_forecast(person_id)
        LOGGER.info(
            "[RhythmForecast] updated personal_model.rhythm_state",
            extra={
                "person_id": person_id,
                "has_state": bool(result),
            },
        )
    except Exception as exc:
        LOGGER.warning("rhythm_forecast failed person=%s error=%s", person_id, exc)


async def _handle_insight_update(person_id: str, payload: Dict[str, Any]) -> None:
    try:
        behavior_profile = payload.get("behavior_profile") or {}
        mode = payload.get("mode") or "today"
        bundle = await insight_engine.generate_insights(person_id, mode=mode, behavior_profile=behavior_profile)
        LOGGER.info("Insight bundle generated person=%s mode=%s summary=%s", person_id, mode, bundle.get("summary"))
    except Exception as exc:
        LOGGER.warning("turn_insight_update failed person=%s error=%s", person_id, exc)


async def _handle_brain_refresh(person_id: str, payload: Dict[str, Any]) -> None:
    try:
        await brain_engine.refresh_brain(person_id, refresh_journey=False)
        LOGGER.info("Brain refresh completed person=%s", person_id)
    except Exception as exc:
        LOGGER.warning("brain_refresh failed person=%s error=%s", person_id, exc)


async def _handle_journal_enrich(person_id: str, payload: Dict[str, Any]) -> None:
    """Build/persist enrichment + memory graph off the turn path."""
    entry_id = payload.get("entry_id")
    text = payload.get("text") or ""
    if not text and entry_id:
        try:
            row = await dbfetch(
                "SELECT content FROM journal_entries WHERE id = $1 AND user_id = $2",
                entry_id,
                person_id,
                one=True,
            )
            text = (row or {}).get("content") or ""
        except Exception as exc:  # pragma: no cover - best effort
            LOGGER.warning("journal_enrich fetch failed person=%s entry=%s err=%s", person_id, entry_id, exc)
    if not text:
        LOGGER.info("journal_enrich skipped person=%s entry=%s (no text)", person_id, entry_id)
        return
    try:
        enrichment = await enrich_journal_entry(text, person_id=person_id)
        graph = build_graph_from_enrichment(enrichment)
        await persist_enrichment(entry_id, enrichment)
        await persist_memory_graph(person_id, graph)
        LOGGER.info(
            "journal_enrich done person=%s entry=%s nodes=%s edges=%s",
            person_id,
            entry_id,
            len(graph.get("nodes") or []),
            len(graph.get("edges") or []),
        )
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("journal_enrich failed person=%s entry=%s err=%s", person_id, entry_id, exc)


__all__ = ["process_turn_job"]
