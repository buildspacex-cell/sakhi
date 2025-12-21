from __future__ import annotations

import datetime as dt
import asyncio
from typing import Any, Dict, Optional

from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.memory.personal_model import update_personal_model
from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.apps.api.services.memory.recall import memory_recall
from sakhi.apps.api.services.memory.context_synthesizer import synthesize_memory_context
from sakhi.apps.api.services.memory.ingest_reasoning import ingest_reasoning_to_memory
from sakhi.apps.api.services.persona.session_tuning import update_session_persona
from sakhi.apps.api.services.conversation.topic_manager import update_conversation_topics
from sakhi.apps.api.services.debug import DebugFlow, trace_id_var
from sakhi.apps.api.core.trace import Trace
from sakhi.apps.api.core.trace_store import persist_trace
from sakhi.apps.api.core.events import publish
from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.event_logger import log_event
from sakhi.apps.worker.tasks.update_relationship_arcs import update_relationship_arcs

from sakhi.libs.reasoning.engine import run_reasoning
from sakhi.libs.embeddings import embed_text
from sakhi.libs.insights.human_view import assemble_human_debug_panel
from sakhi.libs.debug.narrative import build_narrative_trace


def _salience(novelty: float, intensity: float, goal_rel: float) -> float:
    return float(max(0.0, min(1.0, 0.4 * novelty + 0.3 * intensity + 0.3 * goal_rel)))


def _vividness(sensory: float, coherence: float) -> float:
    return float(max(0.0, min(1.0, 0.5 * sensory + 0.5 * coherence)))


def _karmic_weight(sal: float, purified: bool = False) -> float:
    base = 0.5 + 0.5 * sal
    return base * (0.6 if purified else 1.0)


async def process_observation(
    *,
    person_id: str,
    text: str,
    layer: str = "conversation",
    ts: Optional[dt.datetime] = None,
    entry_id: Optional[str] = None,
    raw_extraction: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> Dict[str, Any]:
    ts = ts or dt.datetime.utcnow()

    trace = Trace(person_id=person_id, flow="canonical_ingest")
    dbg = DebugFlow(trace_id=trace.trace_id, person_id=person_id)
    token = trace_id_var.set(trace.trace_id)

    extraction = raw_extraction or extract(text, ts)
    trace.add("L1.extraction", "Initial extraction", extraction)

    mood_affect = extraction.get("slots", {}).get("mood_affect", {})
    novelty = 0.6
    intensity = float(abs(mood_affect.get("score", 0.3)))
    goal_rel = 0.7 if "goal" in extraction.get("slots", {}) else 0.3
    sal = _salience(novelty, intensity, goal_rel)
    viv = _vividness(0.5, 0.6)
    karm = _karmic_weight(sal)

    trace.add(
        "metrics",
        "Salience/vividness/karmic_weight",
        {"salience": sal, "vividness": viv, "karmic": karm},
    )

    low = text.lower()
    domains = []
    intents = []
    if "music" in low:
        domains.append("music")
    if any(w in low for w in ["learn", "practice", "start", "train"]):
        intents.append("learn")

    if entry_id:
        micro_block_min = 20
        await q(
            """
            INSERT INTO journal_inference (entry_id, container, payload, inference_type, source)
            VALUES ($1, 'context',
              jsonb_build_object(
                'domains', to_jsonb($2::text[]),
                'intents', to_jsonb($3::text[]),
                'horizon', 'near',
                'practice_pref', jsonb_build_object('micro_block_min', to_jsonb($4::int))
              ),
              'interpretive',
              'canonical_ingest')
            """,
            entry_id,
            domains,
            intents,
            micro_block_min,
        )

    theme = None
    if "music" in low:
        theme = "Learning:Music"
        try:
            await q(
                """
                INSERT INTO journal_themes (user_id, theme, time_window, metrics)
                VALUES ($1,$2,'14d',
                  jsonb_build_object(
                    'mentions',1,
                    'salience',0.6,
                    'significance',0.35,
                    'emotion_avg',0.5,
                    'impact',0.5,
                    'last_seen',now()
                  )
                )
                ON CONFLICT DO NOTHING
                """,
                person_id,
                theme,
            )
            await q(
                """
                UPDATE journal_themes
                SET metrics = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(metrics,'{mentions}',
                        to_jsonb((COALESCE((metrics->>'mentions')::int,0) + 1))
                      ),
                      '{salience}',
                      to_jsonb(LEAST(0.95, COALESCE((metrics->>'salience')::float,0.6) + 0.05))
                    ),
                    '{emotion_avg}',
                    to_jsonb((COALESCE((metrics->>'emotion_avg')::float,0)*0.8 + 0.5*0.2))
                  ),
                  '{significance}',
                  to_jsonb(LEAST(1.0,
                         COALESCE((metrics->>'significance')::float,0.35)
                       + 0.04*(1 + COALESCE((metrics->>'impact')::float,0.5))*(0.5 + 0.5*0.5)
                  ))
                ),
                metrics = jsonb_set(metrics,'{last_seen}',to_jsonb(now()))
                WHERE user_id = $1 AND theme = $2
                """,
                person_id,
                theme,
            )
        except Exception:
            pass

    personal_obs = {
        "intent": intents[0] if intents else None,
        "theme": theme,
        "mood": mood_affect.get("label"),
        "layer": layer,
        "text": text,
    }
    personal_obs = {k: v for k, v in personal_obs.items() if v}

    personal_update = None
    if personal_obs:
        personal_update = await update_personal_model(person_id, personal_obs)
        asyncio.create_task(update_relationship_arcs(person_id, text))

    mem_context = ""
    try:
        mem_context = await synthesize_memory_context(person_id=person_id, user_query=text, limit=350)
    except Exception:
        pass

    try:
        reasoning = await run_reasoning(person_id=person_id, query=text, memory_context=mem_context)
    except Exception as exc:
        reasoning = {"error": str(exc)}

    try:
        reasoning_ingest = await ingest_reasoning_to_memory(
            person_id=person_id,
            reasoning=reasoning,
            source_turn_id=entry_id or "canonical",
        )
    except Exception as exc:
        reasoning_ingest = {"error": str(exc)}

    try:
        recall = await memory_recall(person_id=person_id, query=text, limit=5)
    except Exception as exc:
        recall = {"error": str(exc)}

    planner_payload = None  # planner handled in workers (Build 50)

    try:
        persona_update = await update_session_persona(person_id, text)
    except Exception:
        persona_update = None

    try:
        topic_state = await update_conversation_topics(person_id, text)
    except Exception:
        topic_state = None

    if entry_id:
        await publish(
            "journal.entry.processed",
            {
                "person_id": person_id,
                "entry_id": entry_id,
                "layer": layer,
                "ts": ts.isoformat(),
            },
        )

    api_debug = {
        "extraction": extraction,
        "salience": sal,
        "themes": theme,
        "personal_model": personal_update,
        "reasoning": reasoning,
        "recall": recall,
        "planner": planner_payload,
        "persona": persona_update,
        "topics": topic_state,
        "memory_context": mem_context,
        "metadata": metadata or {},
    }

    trace.add("summary", "Canonical ingestion completed", api_debug)
    debug_payload = trace.to_dict()
    await persist_trace(debug_payload)

    try:
        human_insights = await assemble_human_debug_panel(
            person_id=person_id, input_text=text, reply_text=None
        )
    except Exception:
        human_insights = None

    try:
        narrative_debug = await build_narrative_trace(
            person_id=person_id,
            text=text,
            reply=None,
            memory_context=mem_context,
            reasoning=reasoning,
            intents=intents,
            emotion=mood_affect,
            topics=topic_state,
        )
    except Exception:
        narrative_debug = None

    trace_id_var.reset(token)

    return {
        "person_id": person_id,
        "entry_id": entry_id,
        "extraction": extraction,
        "salience": sal,
        "themes": theme,
        "personal_model": personal_update,
        "reasoning": reasoning,
        "reasoning_ingest": reasoning_ingest,
        "recall": recall,
        "planner": planner_payload,
        "persona": persona_update,
        "topics": topic_state,
        "memory_context": mem_context,
        "debug": api_debug,
        "human_insights": human_insights,
        "narrative_debug": narrative_debug,
        "ts": ts.isoformat(),
    }
