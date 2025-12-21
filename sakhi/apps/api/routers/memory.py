from __future__ import annotations

import datetime as dt
import json
import os
import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.api.core.event_logger import log_event
from sakhi.apps.api.core.events import publish, MEMORY_EVENT
from sakhi.apps.api.core.metrics import aw_events_written, episodes_written
from sakhi.apps.api.core.trace import Trace
from sakhi.apps.api.core.trace_store import persist_trace
from sakhi.apps.api.core.web_tools import ALLOW_WEB, check_web_rate_limit, smart_search
from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.debug import DebugFlow, trace_id_var
from sakhi.apps.api.services.explain import summarize_layers
from sakhi.apps.api.services.memory.personal_model import update_personal_model
from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.apps.worker.tasks.update_relationship_arcs import update_relationship_arcs
from sakhi.libs.debug.narrative import build_narrative_trace
from sakhi.libs.debug.narrative_unified import build_unified_narrative
from sakhi.apps.api.services.ingestion.unified_ingest import ingest_heavy
from sakhi.apps.api.services.observe.ack import build_acknowledgement
from sakhi.apps.api.services.observe.dispatcher import enqueue_observe_job
from sakhi.apps.api.services.observe.ingest_service import ingest_entry
from sakhi.apps.api.services.observe.models import ObserveJobPayload
from sakhi.apps.api.core.person_utils import resolve_person_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])
BUILD32_MODE = os.getenv("SAKHI_BUILD32_MODE", "0") == "1"
logger.info("[observe] Build32 mode=%s", BUILD32_MODE)

ALLOWED_LAYERS = {"journal", "conversation", "planner", "command"}


class ObserveIn(BaseModel):
    person_id: str | None = None
    layer: str = "journal"
    text: str
    tags: list[str] = []
    mood: str | None = None
    ts: dt.datetime | None = None
    session_id: str | None = None


async def _observe_lightweight(body: ObserveIn) -> Dict[str, Any]:
    normalized_text = (body.text or "").strip()
    if not normalized_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text cannot be empty")
    body.text = normalized_text

    base_ref = body.person_id or os.getenv("DEMO_USER_ID")
    resolved = await resolve_person_id(base_ref)
    if not resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid person_id")
    person_id = resolved
    await dbexec(
        "UPDATE personal_model SET last_seen = NOW() WHERE person_id = $1",
        person_id,
    )
    ack = build_acknowledgement(body.text)
    ts = body.ts or dt.datetime.utcnow()
    safe_layer = body.layer or "journal"
    if safe_layer not in ALLOWED_LAYERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid layer")
    entry = await ingest_entry(
        person_id=person_id,
        text=body.text,
        layer=safe_layer,
        tags=body.tags,
        mood=body.mood,
        ack_text=ack.reply,
        ts=ts,
    )
    payload = ObserveJobPayload(
        entry_id=entry.entry_id,
        person_id=person_id,
        text=body.text,
        layer=safe_layer,
        tags=entry.tags,
        created_at=entry.created_at,
    )
    job_id = enqueue_observe_job(payload)
    response_payload: Dict[str, Any] = {
        "entry_id": entry.entry_id,
        "reply": ack.reply,
        "status": entry.status,
    }
    if job_id:
        response_payload["job_id"] = job_id
    return JSONResponse(response_payload)


def _salience(novelty: float, intensity: float, goal_rel: float) -> float:
    return float(max(0.0, min(1.0, 0.4 * novelty + 0.3 * intensity + 0.3 * goal_rel)))


def _vividness(sensory: float, coherence: float) -> float:
    return float(max(0.0, min(1.0, 0.5 * sensory + 0.5 * coherence)))


def _karmic_weight(sal: float, purified: bool = False) -> float:
    base = 0.5 + 0.5 * sal
    return base * (0.6 if purified else 1.0)


def _should_web_search(text: str) -> bool:
    lowered = text.lower()
    triggers = (
        "review",
        "reviews",
        "rating",
        "best",
        "how to start",
        "beginner",
        "pricing",
        "compare",
        "comparison",
        "which instrument",
    )
    return any(term in lowered for term in triggers)


async def _persist_web_snippet(person_id: str, query: str, snippet: str, ts: dt.datetime) -> str | None:
    source = {"kind": "web_snippet", "query": query}
    try:
        source_json = json.dumps(source, ensure_ascii=False)
        row = await q(
            """
            INSERT INTO journal_entries (user_id, content, layer, tags, source_ref, created_at, updated_at)
            VALUES ($1, $2, 'external', ARRAY['web'], $3::jsonb, $4, $4)
            RETURNING id
            """,
            person_id,
            snippet,
            source_json,
            ts,
            one=True,
        )
        return str(row["id"])
    except Exception:
        return None

@router.post("/observe")
async def observe(body: ObserveIn) -> Dict[str, Any]:
    UNIFIED = os.getenv("SAKHI_UNIFIED_INGEST") == "1"
    normalized_text = (body.text or "").strip()
    if not normalized_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text cannot be empty")
    body.text = normalized_text
    if BUILD32_MODE:
        return await _observe_lightweight(body)

    base_ref = body.person_id or os.getenv("DEMO_USER_ID")
    resolved = await resolve_person_id(base_ref)
    if not resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid person_id")
    person_id = resolved
    await dbexec(
        "UPDATE personal_model SET last_seen = NOW() WHERE person_id = $1",
        person_id,
    )

    trace = Trace(person_id=person_id, flow="observe")
    dbg = DebugFlow(trace_id=trace.trace_id, person_id=person_id)
    token = trace_id_var.set(trace.trace_id)

    ts = body.ts or dt.datetime.utcnow()
    if not UNIFIED:
        triage = extract(body.text, ts)
    else:
        triage = {}

    fast_ingest = {"status": "skipped"}  # Build 50: keep API light; heavy done in workers
    trace.add(
        "extract",
        "L1 extraction",
        {
            "triage": triage,
            "summary_text": "Parsed the message for intent, time references, and mood signals.",
        },
        explanation="Identified any intents, time windows, and emotions mentioned in the message.",
    )

    mood_affect = triage.get("slots", {}).get("mood_affect", {}) if triage else {}
    novelty = 0.6
    intensity = float(abs(mood_affect.get("score", 0.3)))
    goal_rel = 0.7 if "goal" in triage.get("slots", {}) else 0.3
    if not UNIFIED:
        sal = _salience(novelty, intensity, goal_rel)
        viv = _vividness(0.5, 0.6)
        karm = _karmic_weight(sal, purified=False)
    else:
        sal = 0
        viv = 0
        karm = 0
    trace.add(
        "metrics",
        "Computed salience/vividness/karmic_weight",
        {"salience": sal, "vividness": viv, "karmic_weight": karm},
        explanation="Estimated how memorable and impactful this moment is to decide if it should be surfaced later.",
    )

    snippet_text: str | None = None
    snippet_query: str | None = None
    snippet_entry_id: str | None = None
    if not UNIFIED and ALLOW_WEB and _should_web_search(body.text):
        await check_web_rate_limit()
        snippet_query = body.text
        lowered = body.text.lower()
        if "learn music" in lowered or "music" in lowered:
            snippet_query = "beginner instrument choice adults voice vs guitar vs piano pros and cons"
        snippet_text = await smart_search(snippet_query)
        snippet_entry_id = await _persist_web_snippet(person_id, snippet_query, snippet_text, ts) if snippet_text else None
        trace.add(
            "observe.web",
            "Fetched web snippet",
            {
                "query": snippet_query,
                "snippet": (snippet_text or "")[:400],
                "summary_text": "Looked up a privacy-screened web snippet to enrich the memory.",
            },
            explanation="Grabbed a privacy-screened web snippet to reference later.",
        )

    source_ref = {"triage": triage, "mood": body.mood}
    source_ref_json = json.dumps(source_ref, ensure_ascii=False)

    row = await q(
        """
        INSERT INTO journal_entries (
            user_id, content, layer, tags, mood, mood_score, source_ref,
            created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $8)
        RETURNING id
        """,
        person_id,
        body.text,
        safe_layer,
        body.tags,
        body.mood,
        mood_affect.get("score"),
        source_ref_json,
        ts,
        one=True,
    )
    entry_id = str(row["id"])

    await publish(
        MEMORY_EVENT,
        {
            "person_id": person_id,
            "entry_id": entry_id,
            "text": body.text,
            "layer": safe_layer,
            "ts": ts.isoformat(),
        },
    )

    asyncio.create_task(
        ingest_journal_entry(
            {
                "id": entry_id,
                "user_id": person_id,
                "content": body.text,
                "mood": body.mood,
                "tags": body.tags,
                "layer": safe_layer,
                "ts": ts.isoformat(),
                "facets": triage,
            }
        )
    )

    # Build 50: canonical_ingest removed from route to avoid duplicate heavy work; heavy ingest remains queued.
    try:
        asyncio.create_task(
            ingest_heavy(
                person_id=person_id,
                entry_id=entry_id,
                text=body.text,
                ts=ts,
            )
        )
        trace.add(
            "unify.heavy",
            "Scheduled heavy ingestion",
            {
                "entry_id": entry_id,
                "summary_text": "Scheduled deep enrichment: themes, graph updates, persona, planner.",
            },
            explanation="Heavy ingestion runs asynchronously so the endpoint stays fast.",
        )
    except Exception as exc:
        trace.add(
            "unify.heavy.error",
            "Failed to schedule heavy ingestion",
            {"error": str(exc)},
            explanation="Heavy ingestion task failed to schedule, but observe continues safely.",
        )
    await log_event(
        person_id,
        "journal",
        "Journal entry stored",
        {"entry_id": entry_id, "layer": safe_layer, "text": body.text[:160]},
    )
    episodes_written.inc()
    event_id = f"evt_{entry_id}"
    event_payload_json = json.dumps({"episode_id": str(entry_id), "text": body.text}, ensure_ascii=False)
    context_json = json.dumps(
        {
            "tz": "Asia/Kolkata",
            "device": "web",
            "session_id": body.session_id or "unknown",
            "privacy_flags": ["pii_masked"],
        },
        ensure_ascii=False,
    )
    await q(
        """
        INSERT INTO aw_event(id, actor, modality, person_id, payload, context_json, schema_version, hash)
        VALUES ($1, 'user', 'text', $2, $3::jsonb, $4::jsonb, 'aw_1', $5)
        ON CONFLICT (id) DO NOTHING
        """,
        event_id,
        person_id,
        event_payload_json,
        context_json,
        f"episode:{entry_id}",
    )
    aw_events_written.inc()
    await q(
        "INSERT INTO aw_edge(src_id, dst_id, kind) VALUES ($1, $2, 'derives') ON CONFLICT DO NOTHING",
        event_id,
        str(entry_id),
    )
    await publish(
        "journal.entry.created",
        {
            "person_id": person_id,
            "entry_id": str(entry_id),
            "created_at": ts.isoformat(),
            "layer": safe_layer,
        },
    )

    low = body.text.lower()
    domains: list[str] = []
    intents: list[str] = []
    if "music" in low:
        domains.append("music")
    if any(w in low for w in ["learn", "practice", "start", "train"]):
        intents.append("learn")

    micro_block_min = int(20)

    if not UNIFIED:
        await q(
            """
            UPDATE journal_entries
            SET facets_v2 = COALESCE(facets_v2, '{}'::jsonb)
                || jsonb_build_object(
                     'domains', COALESCE(facets_v2->'domains','[]'::jsonb) || to_jsonb($2::text[]),
                     'intents', COALESCE(facets_v2->'intents','[]'::jsonb) || to_jsonb($3::text[]),
                     'horizon', COALESCE(facets_v2->>'horizon','near'),
                     'practice_pref',
                        COALESCE(facets_v2->'practice_pref','{}'::jsonb)
                        || jsonb_build_object('micro_block_min', to_jsonb($4::int))
                   )
            WHERE id = $1
            """,
            entry_id,
            domains,
            intents,
            micro_block_min,
        )

    theme = None
    if not UNIFIED and "music" in low:
        theme = "Learning:Music"

    if not UNIFIED and theme:
        await q(
            """
            INSERT INTO journal_themes (user_id, theme, time_window, metrics)
            VALUES ($1, $2, '14d',
              jsonb_build_object(
                'mentions', to_jsonb(1),
                'salience', to_jsonb(0.6::numeric),
                'significance', to_jsonb(0.35::numeric),
                'emotion_avg', to_jsonb(0.5::numeric),
                'impact', to_jsonb(0.5::numeric),
                'last_seen', to_jsonb(now())
              )
            )
            ON CONFLICT DO NOTHING
            """,
            person_id,
            theme,
        )

        emotion = 0.5
        await q(
            """
            UPDATE journal_themes
            SET metrics =
                jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(metrics, '{mentions}',
                        to_jsonb((COALESCE((metrics->>'mentions')::int,0) + 1))
                      ),
                      '{salience}',
                      to_jsonb(LEAST(0.95::numeric, COALESCE((metrics->>'salience')::numeric,0.6) + 0.05::numeric))
                    ),
                    '{emotion_avg}',
                    to_jsonb((COALESCE((metrics->>'emotion_avg')::numeric,0)*0.8 + $3::numeric*0.2))
                  ),
                  '{significance}',
                  to_jsonb(LEAST(1.0::numeric,
                         COALESCE((metrics->>'significance')::numeric,0.35)
                       + 0.04::numeric*(1 + COALESCE((metrics->>'impact')::numeric,0.5))*(0.5 + $3::numeric*0.5)
                  ))
                ),
                metrics = jsonb_set(metrics, '{last_seen}', to_jsonb(now()))
            WHERE user_id = $1 AND theme = $2
            """,
            person_id,
            theme,
            emotion,
        )

    trace.add(
        "observe.write",
        "Stored entry",
        {
            "entry_id": entry_id,
            "layer": body.layer,
            "summary_text": f"Saved the memory entry with layer '{body.layer}' and tagged it for enrichment.",
        },
        explanation=f"Persisted the entry under layer '{body.layer}' with initial metrics for enrichment.",
    )

    intent_labels = [
        item.get("type")
        for item in triage.get("triage", [])
        if isinstance(item, dict) and item.get("type")
    ]
    mood_affect = triage.get("slots", {}).get("mood_affect", {})
    mood_label = mood_affect.get("label")
    time_window = triage.get("slots", {}).get("time_window", {}).get("start")

    personal_observation = {
        "intent": intent_labels[0] if intent_labels else None,
        "theme": theme,
        "mood": mood_label,
        "time_scope": time_window,
        "layer": body.layer,
        "text": body.text,
    }
    personal_observation = {k: v for k, v in personal_observation.items() if v}
    personal_model_payload: Dict[str, Any] = {}
    if not UNIFIED and personal_observation:
        personal_model_payload = await update_personal_model(person_id, personal_observation)
        trace.add(
            "memory.personal_model",
            "Updated layered personal model",
            {
                "keys": list(personal_observation.keys()),
                "summary_text": "Merged memory observation into personal model layers.",
            },
        )
        dbg.add(
            "memory.personal_model",
            "Updated layered personal model",
            {"keys": list(personal_observation.keys())},
        )
        asyncio.create_task(update_relationship_arcs(person_id, body.text))

    debug_payload = trace.to_dict()
    debug_payload["person_id"] = person_id
    debug_payload["flow"] = "observe"
    if personal_model_payload:
        debug_payload["personal_model"] = personal_model_payload.get("data")
        debug_payload["personal_model_full"] = personal_model_payload
    await persist_trace(debug_payload)

    human_narrative, layer_summaries = summarize_layers(debug_payload.get("steps", []))
    debug_payload["human_narrative"] = human_narrative
    debug_payload["plain_layers"] = layer_summaries

    receipts: list[Dict[str, Any]] = [
        {"kind": "episode", "entry_id": str(entry_id)},
    ]
    if snippet_entry_id:
        receipts.append({"kind": "web_snippet", "entry_id": snippet_entry_id, "query": snippet_query})
    if theme:
        receipts.append({"kind": "theme", "theme": theme})

    dbg.events = debug_payload.get("steps", [])
    summary_payload = {"entry_id": str(entry_id), "receipts": receipts}
    if personal_model_payload:
        summary_payload["personal_model"] = personal_model_payload.get("data")
    await dbg.finish(True, summary_payload)

    response_payload: Dict[str, Any] = {
        "entry_id": str(entry_id),
        "triage": triage,
        "salience": sal,
        "debug": debug_payload,
    }
    if fast_ingest:
        response_payload["unified_fast"] = fast_ingest
    if personal_model_payload:
        response_payload["personal_model"] = personal_model_payload.get("data")
    if snippet_text and snippet_query:
        response_payload["web"] = {
            "query": snippet_query,
            "snippet": snippet_text,
            "entry_id": snippet_entry_id,
        }

    interpretation_summary = {
        "summary": ", ".join(intent_labels) or "General reflection",
        "triage": triage,
    }
    memory_layer_summary = " ".join(
        layer.get("summary", "") for layer in layer_summaries[:4]
    ).strip() or human_narrative
    if not UNIFIED:
        narrative_debug = build_narrative_trace(
            user_text=body.text,
            interpretation=interpretation_summary,
            memory={"summary": memory_layer_summary},
            context_used="Journal enrichment + meaning extraction",
            reasoning=human_narrative,
            llm_prompt=None,
            llm_reply=None,
        )
        if narrative_debug:
            response_payload["narrative_debug"] = narrative_debug
    else:
        narrative_debug = None

    unified_narrative = None
    if os.getenv("SAKHI_DEV_DEBUG") == "1":
        try:
            unified_narrative = build_unified_narrative(
                {
                    "person_id": person_id,
                    "input_text": body.text,
                    "reply_text": None,
                    "triage": triage,
                    "intents": intent_labels,
                    "emotion": mood_affect,
                    "topics": [theme] if theme else [],
                    "memory_context": memory_layer_summary,
                    "reasoning": {"summary": human_narrative},
                    "personal_model": personal_model_payload.get("data") if personal_model_payload else {},
                    "planner": {},
                    "layer": body.layer,
                }
            )
        except Exception as exc:
            unified_narrative = {"error": str(exc)}

    if unified_narrative:
        response_payload["narrative"] = unified_narrative

    response = JSONResponse(response_payload, headers={"x-trace-id": trace.trace_id})
    trace_id_var.reset(token)
    return response


@router.post("/consolidate/{person_id}")
async def consolidate(person_id: str) -> Dict[str, Any]:
    from sakhi.apps.api.services.memory.consolidation import consolidate_memory

    return await consolidate_memory(person_id)
