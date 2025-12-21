from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
from collections import deque

from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.apps.api.services.planner.engine import planner_commit, planner_suggest
from sakhi.apps.api.services.rhythm.engine import run_rhythm_engine
from sakhi.apps.api.services.persona.session_tuning import update_session_persona
from sakhi.apps.api.services.soul.engine import run_soul_engine
from sakhi.apps.api.services.growth.loop import sync_growth_from_planner
from sakhi.apps.api.services.planner.rhythm_fusion import compute_rhythm_planner_alignment
from sakhi.apps.logic.relationship_engine import update_from_turn
from sakhi.apps.logic.insight import insight_engine
from sakhi.apps.logic.brain import brain_engine
from sakhi.apps.api.core.person_utils import resolve_person_id

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

    LOGGER.info("Turn job start type=%s turn=%s", job_type, turn_id)
    if job_type == "turn_memory_update":
        await _handle_memory_update(turn_id, resolved_id, payload)
    elif job_type == "turn_planner_update":
        await _handle_planner_update(resolved_id, payload)
    elif job_type == "turn_persona_update":
        await _handle_persona_update(resolved_id, payload)
    elif job_type == "turn_rhythm_update":
        await _handle_rhythm_update(resolved_id, payload)
    elif job_type == "turn_insight_update":
        await _handle_insight_update(resolved_id, payload)
    elif job_type == "brain_refresh":
        await _handle_brain_refresh(resolved_id, payload)
    else:
        LOGGER.warning("Unknown turn job type=%s", job_type)


async def _handle_memory_update(turn_id: str, person_id: str, payload: Dict[str, Any]) -> None:
    text = payload.get("text") or ""
    if not text:
        return
    try:
        await ingest_journal_entry(
            {
                "id": turn_id,
                "user_id": person_id,
                "content": text,
                "layer": "conversation",
                "ts": payload.get("ts"),
                "facets": payload.get("facets", {}),
                "thread_id": payload.get("thread_id") or person_id,
            }
        )
    except Exception as exc:  # pragma: no cover - best effort
        LOGGER.warning("turn_memory_update failed turn=%s error=%s", turn_id, exc)


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


__all__ = ["process_turn_job"]
