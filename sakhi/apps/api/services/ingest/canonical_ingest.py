from __future__ import annotations

import logging
import os
import datetime as dt
from typing import Any, Dict, Optional, List

from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.apps.api.services.memory.personal_model import update_personal_model
from sakhi.apps.api.services.memory.recall import memory_recall
from sakhi.apps.api.services.memory.context_synthesizer import synthesize_memory_context
from sakhi.apps.api.services.persona.session_tuning import update_session_persona

LOGGER = logging.getLogger(__name__)

try:
    from sakhi.libs.reasoning.engine import run_reasoning
except Exception:  # pragma: no cover - optional
    run_reasoning = None

try:
    from sakhi.apps.api.services.conversation.topic_manager import update_conversation_topics
except Exception:  # pragma: no cover - optional
    update_conversation_topics = None


async def canonical_ingest(
    *,
    person_id: str,
    text: str,
    layer: str = "conversation",
    tags: Optional[List[str]] = None,
    mood: Optional[str] = None,
    ts: Any = None,
    entry_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    facets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if os.getenv("SAKHI_UNIFIED_INGEST") != "1":
        return {"status": "disabled", "reason": "SAKHI_UNIFIED_INGEST=0"}

    if isinstance(ts, str):
        try:
            ts = dt.datetime.fromisoformat(ts.replace("Z", ""))
        except Exception:
            ts = dt.datetime.utcnow()
    if not isinstance(ts, dt.datetime):
        ts = dt.datetime.utcnow()
    tags = tags or []
    meta = meta or {}
    if entry_id is not None:
        meta["entry_id"] = entry_id

    try:
        triage = facets or extract(text, ts)
    except Exception as exc:
        LOGGER.error("[CanonicalIngest] extractor failed: %s", exc)
        triage = dict(facets or {})

    entry_payload = {
        "id": entry_id,
        "user_id": person_id,
        "content": text,
        "mood": mood,
        "tags": tags,
        "layer": layer,
        "ts": ts.isoformat(),
        "facets": triage,
    }

    try:
        entry_id = await ingest_journal_entry(entry_payload)
    except Exception as exc:
        return {"error": "ingest_failed", "details": str(exc)}

    personal_update = {}
    try:
        obs = {
            "intent": triage.get("triage", [{}])[0].get("type"),
            "mood": triage.get("slots", {}).get("mood_affect", {}).get("label"),
            "time_scope": triage.get("slots", {}).get("time_window", {}).get("start"),
            "layer": layer,
            "text": text,
        }
        obs = {k: v for k, v in obs.items() if v}
        if obs:
            personal_update = await update_personal_model(person_id, obs)
    except Exception:
        personal_update = {}

    reasoning = {}
    if run_reasoning:
        try:
            mem_ctx = await synthesize_memory_context(person_id=person_id, user_query=text, limit=300)
            reasoning = await run_reasoning(person_id=person_id, query=text, memory_context=mem_ctx)
        except Exception:
            reasoning = {}

    topics = {}
    if update_conversation_topics:
        try:
            topics = await update_conversation_topics(person_id, text)
        except Exception:
            topics = {}

    planner = {}  # planner work deferred to workers (Build 50)

    try:
        persona = await update_session_persona(person_id, text)
    except Exception:
        persona = {}

    try:
        recall = await memory_recall(person_id=person_id, query=text, limit=5)
    except Exception:
        recall = []

    return {
        "entry_id": entry_id,
        "triage": triage,
        "personal_model": personal_update,
        "reasoning": reasoning,
        "topics": topics,
        "planner": planner,
        "persona": persona,
        "recall": recall,
        "ts": ts.isoformat(),
        "meta": meta,
    }
