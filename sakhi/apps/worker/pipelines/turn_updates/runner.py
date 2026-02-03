from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
from collections import deque
import datetime as dt

from sakhi.apps.api.services.ingestion.unified_ingest import ingest_heavy
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.worker.tasks.episodic_consolidation_v21 import run_episodic_consolidation_v21

# NOTE: Deep workers (ayurvedic_pipeline, identity_momentum, emotion_soul_rhythm,
# esr, soul_refresh, rhythm_soul_deep, longitudinal_update) have been moved to
# daily schedule in scheduler.py. They are no longer triggered per-turn.
# See: docs/WORKERS.md for v2 architecture

LOGGER = logging.getLogger(__name__)
_PROCESSED_MAX = 1000
_processed_jobs: deque[str] = deque()
_processed_set: set[str] = set()


def process_turn_job(*, job_type: str, turn_id: str, person_id: str, payload: Dict[str, Any]) -> None:
    """Sync wrapper - use process_turn_job_async when already in an async context."""
    asyncio.run(_process(job_type, turn_id, person_id, payload))


async def process_turn_job_async(*, job_type: str, turn_id: str, person_id: str, payload: Dict[str, Any]) -> None:
    """Async version for use within existing event loop (e.g., FastAPI handlers)."""
    await _process(job_type, turn_id, person_id, payload)


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

    # ---- CORE WORKERS (v2: only 3 essential per-turn workers) ----
    # Other state workers run on daily schedule via scheduler.py
    if job_type == "turn_memory_update":
        await _handle_memory_update(turn_id, resolved_id, payload)
    elif job_type == "episodic_consolidation_v21":
        await run_episodic_consolidation_v21(resolved_id, payload)
    elif job_type == "preference_learning":
        await _handle_preference_learning(turn_id, resolved_id, payload)
    else:
        LOGGER.warning("Unknown turn job type=%s (deep workers now run daily via scheduler)", job_type)


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


async def _handle_preference_learning(turn_id: str, person_id: str, payload: Dict[str, Any]) -> None:
    """Extract and store preferences from conversation text."""
    from sakhi.apps.api.services.memory.preference_learning import (
        extract_preferences_from_turn,
        should_learn_preferences,
    )

    text = payload.get("text") or ""
    if not text:
        return

    # Quick check to avoid unnecessary LLM calls
    if not await should_learn_preferences(text):
        LOGGER.debug("[PreferenceLearning] No preference indicators in text, skipping")
        return

    LOGGER.info(
        "[PreferenceLearning] Analyzing turn=%s person=%s text_len=%d",
        turn_id,
        person_id[:8] if person_id else "?",
        len(text),
    )

    try:
        learned = await extract_preferences_from_turn(
            person_id=person_id,
            user_text=text,
        )

        if learned:
            LOGGER.info(
                "[PreferenceLearning] Learned %d preferences for %s",
                len(learned),
                person_id[:8] if person_id else "?",
            )
        else:
            LOGGER.debug("[PreferenceLearning] No preferences extracted from text")

    except Exception as e:
        LOGGER.exception("[PreferenceLearning] Failed to process turn: %s", e)


__all__ = ["process_turn_job", "process_turn_job_async"]
