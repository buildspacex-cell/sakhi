from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List

from sakhi.apps.api.services.journaling.observe import observe_entry
from sakhi.apps.api.services.journaling.enrich import enrich_journal_entry
from sakhi.apps.api.services.memory.embedding import generate_journal_embedding
from sakhi.apps.api.services.memory.topic_extract import extract_topics_for_entry
from sakhi.apps.api.services.memory.emotion_tagging import detect_emotion_for_entry
from sakhi.apps.api.services.memory.short_term import enrich_short_term_memory
from sakhi.apps.api.services.intents.extract import extract_intents_for_entry
from sakhi.apps.api.services.intents.store import store_intent
from sakhi.apps.api.services.intents.planning import plan_from_intents
from sakhi.apps.api.services.intents.store_plans import store_planned_items
from sakhi.apps.api.services.rhythm.triggers import (
    detect_rhythm_related_intents,
    apply_rhythm_triggers,
)
from sakhi.apps.api.services.meta_reflection.triggers import (
    detect_meta_reflection_intents,
    apply_meta_reflection_triggers,
)
from sakhi.apps.api.services.triggers.trigger_engine import compute_triggers

try:
    from sakhi.apps.api.services.ingest.canonical_ingest import canonical_ingest
except Exception:  # pragma: no cover
    canonical_ingest = None

LOGGER = logging.getLogger(__name__)


async def orchestrate_turn(
    person_id: str,
    text: str,
    clarity_hint: str | None = None,
    *,
    capture_only: bool = False,
) -> Dict[str, Any]:
    """
    Run the journaling + intent/memory pipeline for a single turn.
    Returns the full metadata bundle used by the conversation engine.
    """

    result: Dict[str, Any] = {
        "entry_id": None,
        "embedding": [],
        "topics": [],
        "emotion": {},
        "intents": [],
        "plans": [],
        "rhythm_triggers": None,
        "meta_reflection_triggers": None,
    }

    minimal_write = capture_only or os.getenv("SAKHI_TURN_MINIMAL_WRITE") == "1" or os.getenv("SAKHI_UNIFIED_INGEST") != "1"
    LOGGER.error(
        "[orchestrate_turn] start person_id=%s capture_only=%s minimal_write=%s text_len=%s",
        person_id,
        capture_only,
        minimal_write,
        len(text or ""),
    )

    try:
        LOGGER.error("[orchestrate_turn] observe_entry start person_id=%s capture_only=%s", person_id, capture_only)
        entry = await observe_entry(
            person_id=person_id,
            text=text,
            source="conversation",
            clarity_hint=clarity_hint,
        )
        LOGGER.error("[orchestrate_turn] observe_entry done person_id=%s entry_id=%s", person_id, entry.get("id"))
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception("[orchestrate_turn] observe_entry failed person_id=%s error=%s", person_id, exc)
        entry = {}
    entry_id = entry.get("id")
    result["entry_id"] = entry_id
    if not entry_id:
        LOGGER.warning("[orchestrate_turn] missing entry_id person_id=%s capture_only=%s", person_id, capture_only)

    if minimal_write:
        # Persist the journal row and return quickly. Heavy work (embeddings, topics,
        # emotion, intents, short-term merges) should be handled by workers/schedulers.
        if entry_id:
            try:
                asyncio.create_task(generate_journal_embedding(entry_id, text))
            except RuntimeError:
                await generate_journal_embedding(entry_id, text)
        LOGGER.info(
            "[Turn Orchestrator] entry=%s minimal_write=1 (capture_only=%s)",
            entry_id,
            capture_only,
        )
        return result

    if not minimal_write:
        enrichment = await enrich_journal_entry(text, person_id=person_id)
        result["enrichment"] = enrichment

    embedding: List[float] = []
    if entry_id:
        embedding = await generate_journal_embedding(entry_id, text) or []
    result["embedding"] = embedding

    topics = await extract_topics_for_entry(entry_id, text)
    emotion = await detect_emotion_for_entry(entry_id, text) or {}
    result["topics"] = topics or []
    result["emotion"] = emotion or {}

    if entry_id and not minimal_write:
        await enrich_short_term_memory(
            person_id=person_id,
            entry_id=entry_id,
            text=text,
            topics=topics or [],
            emotion=emotion,
            embedding=embedding or [],
        )

    intents = await extract_intents_for_entry(
        entry_id=entry_id,
        text=text,
        topics=topics or [],
        emotion=emotion,
    )

    stored_intents: List[Dict[str, Any]] = []
    for intent in intents or []:
        saved = await store_intent(
            person_id=person_id,
            entry_id=entry_id,
            intent=intent,
        )
        stored_intents.append(saved)
    result["intents"] = stored_intents

    generated_plans: List[Dict[str, Any]] = []
    if stored_intents:
        generated_plans = await plan_from_intents(
            person_id=person_id,
            intents=stored_intents,
        )
        if generated_plans:
            await store_planned_items(person_id=person_id, plans=generated_plans)
    result["plans"] = generated_plans or []

    rhythm_trigger_result = None
    rhythm_related = detect_rhythm_related_intents(stored_intents)
    if rhythm_related:
        rhythm_trigger_result = await apply_rhythm_triggers(
            person_id=person_id,
            intents=rhythm_related,
        )
    result["rhythm_triggers"] = rhythm_trigger_result

    meta_trigger_result = None
    meta_related = detect_meta_reflection_intents(stored_intents)
    if meta_related:
        meta_trigger_result = await apply_meta_reflection_triggers(
            person_id=person_id,
            intents=meta_related,
            entry_id=entry_id,
        )
    result["meta_reflection_triggers"] = meta_trigger_result

    triggers = await compute_triggers(
        person_id=person_id,
        intents=stored_intents,
        journal_entry=entry,
        mood=(emotion or {}).get("label"),
    )
    result["triggers"] = triggers

    LOGGER.info(
        "[Turn Orchestrator] entry=%s intents=%s plans=%s rhythm=%s meta=%s",
        entry_id,
        len(stored_intents),
        len(generated_plans),
        bool(rhythm_trigger_result and rhythm_trigger_result.get("applied")),
        bool(meta_trigger_result and meta_trigger_result.get("applied")),
    )
    LOGGER.error(
        "[orchestrate_turn] end person_id=%s entry_id=%s minimal_write=%s intents=%s plans=%s",
        person_id,
        entry_id,
        minimal_write,
        len(stored_intents),
        len(generated_plans),
    )
    return result


__all__ = ["orchestrate_turn"]
