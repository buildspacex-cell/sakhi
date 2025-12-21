from __future__ import annotations

import os
import datetime
import logging
import asyncio
from typing import Any, Dict

from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from uuid import uuid4

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.events import publish, MEMORY_EVENT
from sakhi.apps.api.services.conversation.orchestrator import orchestrate_turn
from sakhi.apps.api.services.conversation_v2.conversation_engine import generate_reply
from sakhi.apps.api.services.memory.recall import memory_recall
from sakhi.apps.api.services.memory.context_synthesizer import synthesize_memory_context
from sakhi.apps.api.services.planner.engine import planner_suggest
from sakhi.apps.api.services.persona.session_tuning import update_session_persona
from sakhi.libs.insights.human_view import assemble_human_debug_panel
from sakhi.libs.reasoning.engine import run_reasoning
from sakhi.apps.api.services.ingestion.unified_ingest import ingest_heavy
from sakhi.libs.debug.narrative_unified import build_unified_narrative
from sakhi.apps.api.services.turn.context_loader import load_memory_context
from sakhi.apps.api.services.turn.reply_service import build_turn_reply
from sakhi.apps.api.services.turn.async_triggers import enqueue_turn_jobs
from sakhi.apps.api.services.conversation.topic_manager import extract_topics
from sakhi.apps.logic.harmony.orchestrator import run_unified_turn
from sakhi.core.soul.narrative_engine import compute_fast_narrative
from sakhi.core.soul.alignment_engine import compute_alignment
from sakhi.core.rhythm.rhythm_soul_engine import compute_fast_rhythm_soul_frame
from sakhi.core.emotion.emotion_soul_rhythm_engine import compute_fast_esr_frame
from sakhi.core.soul.identity_momentum_engine import compute_fast_identity_momentum
from sakhi.core.soul.identity_timeline_engine import compute_fast_identity_timeline_frame
from sakhi.apps.engine.inner_dialogue import engine as inner_dialogue_engine
from sakhi.apps.engine.tone import compute_tone
from sakhi.apps.engine.continuity import load_continuity, update_continuity, DEFAULT_STATE as CONTINUITY_DEFAULT
from sakhi.apps.engine.empathy import compute_empathy
from sakhi.apps.engine.microreg.engine import compute_microreg
from sakhi.apps.engine.moment_model.engine import compute_moment_model
from sakhi.apps.engine.evidence_pack.engine import select_evidence_anchors
from sakhi.apps.engine.deliberation_scaffold.engine import compute_deliberation_scaffold
from sakhi.apps.engine.reflection_trace.engine import (
    build_reflection_trace,
    persist_reflection_trace,
)
from sakhi.apps.engine.focus_path.engine import generate_focus_path, persist_focus_path
from sakhi.apps.engine.mini_flow.engine import generate_mini_flow, persist_mini_flow
from sakhi.apps.engine.focus_path.engine import generate_focus_path, persist_focus_path
from sakhi.apps.services import micro_goals_service
from sakhi.apps.logic.harmony.memory_write_controller import write_turn_memory
from sakhi.apps.api.utils.person_resolver import resolve_person
from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.emotion_engine import compute as compute_emotion_state
from sakhi.apps.api.services.mind_engine import compute as compute_mind_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["conversation-v2"])
BUILD32_MODE = os.getenv("SAKHI_BUILD32_MODE", "0") == "1"
logger.info("[turn_v2] Build32 mode=%s", BUILD32_MODE)

_UNIFIED_INGEST_SCHEMA_OK: bool | None = None


async def _unified_ingest_schema_ok() -> bool:
    global _UNIFIED_INGEST_SCHEMA_OK
    if _UNIFIED_INGEST_SCHEMA_OK is not None:
        return _UNIFIED_INGEST_SCHEMA_OK
    try:
        row = await q(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'memory_short_term'
              AND column_name = 'entry_id'
            LIMIT 1
            """,
            one=True,
        )
        _UNIFIED_INGEST_SCHEMA_OK = bool(row)
    except Exception:
        _UNIFIED_INGEST_SCHEMA_OK = False
    return _UNIFIED_INGEST_SCHEMA_OK


class TurnIn(BaseModel):
    text: str
    clarity_phrase: str | None = None
    capture_only: bool = False


async def _load_internal_state(person_id: str) -> Dict[str, Any]:
    state = {
        "emotion": None,
        "mind": None,
        "context_vector_available": False,
        "cognitive_load": None,
        "priority": None,
        "priority_topics": None,
        "soul_values": None,
        "soul_identity": None,
        "life_themes": None,
        "identity_graph": None,
    }
    try:
        row = await q(
            "SELECT long_term FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        if row and row.get("long_term"):
            long_term = row["long_term"]
            layers = long_term.get("layers") if isinstance(long_term, dict) else {}
            emotion = layers.get("emotion") if layers else {}
            mind = layers.get("mind") if layers else {}
            state["emotion"] = (emotion or {}).get("summary")
            state["mind"] = (mind or {}).get("summary")
            metrics = (mind or {}).get("metrics") or {}
            state["cognitive_load"] = metrics.get("cognitive_load")
            state["priority"] = metrics.get("top_priority")
            state["priority_topics"] = metrics.get("priority_topics")
            soul = layers.get("soul") if layers else {}
            soul_metrics = (soul or {}).get("metrics") or {}
            state["soul_values"] = soul_metrics.get("values")
            state["soul_identity"] = soul_metrics.get("identity_anchors")
            state["life_themes"] = soul_metrics.get("life_themes")
            if isinstance(long_term, dict) and long_term.get("identity_graph"):
                state["identity_graph"] = long_term.get("identity_graph")
    except Exception:
        pass

    try:
        ctx_row = await q(
            "SELECT merged_context_vector FROM memory_context_cache WHERE person_id = $1",
            person_id,
            one=True,
        )
        if ctx_row and ctx_row.get("merged_context_vector") is not None:
            state["context_vector_available"] = True
    except Exception:
        pass

    # fallback quick compute if missing
    if not state.get("emotion"):
        try:
            summary = await compute_emotion_state(person_id)
            state["emotion"] = summary.get("summary")
        except Exception:
            state["emotion"] = None
    if not state.get("mind"):
        try:
            summary = await compute_mind_state(person_id)
            state["mind"] = summary.get("summary")
            metrics = summary.get("metrics") or {}
            state["cognitive_load"] = metrics.get("cognitive_load")
            state["priority"] = metrics.get("top_priority")
            state["priority_topics"] = metrics.get("priority_topics")
        except Exception:
            state["mind"] = None
    if not state.get("soul_values"):
        try:
            row = await q(
                "SELECT long_term FROM personal_model WHERE person_id = $1",
                person_id,
                one=True,
            )
            if row and row.get("long_term"):
                long_term = row["long_term"]
                layers = long_term.get("layers") if isinstance(long_term, dict) else {}
                soul = layers.get("soul") if layers else {}
                metrics = (soul or {}).get("metrics") or {}
                state["soul_values"] = metrics.get("values")
                state["soul_identity"] = metrics.get("identity_anchors")
                state["life_themes"] = metrics.get("life_themes")
                if isinstance(long_term, dict) and long_term.get("identity_graph"):
                    state["identity_graph"] = long_term.get("identity_graph")
        except Exception:
            pass

    return state

async def _turn_lightweight(body: TurnIn, user_id: str) -> Dict[str, Any]:
    context_snapshot = await load_memory_context(user_id)
    triage = extract(body.text, datetime.datetime.utcnow())
    mood_affect = (triage.get("slots") or {}).get("mood_affect") if isinstance(triage, dict) else {}
    emotion_update = {
        "summary": (mood_affect or {}).get("label"),
        "confidence": float((mood_affect or {}).get("score") or 0.5),
    }
    try:
        persona_update = await update_session_persona(user_id, body.text)
    except Exception:
        persona_update = None
    reply_package = await build_turn_reply(
        person_id=user_id,
        user_text=body.text,
        context_snapshot=context_snapshot,
    )
    turn_id = str(uuid4())
    queued_jobs = [
        "turn_memory_update",
        "turn_planner_update",
        "turn_rhythm_update",
        "turn_persona_update",
        "turn_insight_update",
        "brain_refresh",
    ]
    enqueue_turn_jobs(
        turn_id,
        user_id,
        queued_jobs,
        {
            "text": body.text,
            "ts": datetime.datetime.utcnow().isoformat(),
            "intents": [],
            "emotion_update": emotion_update,
            "persona_update": persona_update,
        },
    )
    tone_blueprint = reply_package.get("tone") or {}
    journaling_ai = reply_package.get("journaling_ai")
    return {
        "reply": reply_package["reply"],
        "entry_id": None,
        "context": context_snapshot,
        "queued_jobs": queued_jobs,
        "metadata": reply_package["metadata"],
        "status": "completed",
        "sessionId": user_id,
        "clarityHint": body.clarity_phrase,
        "tone": tone_blueprint.get("style") or "auto",
        "toneBlueprint": tone_blueprint,
        "journaling_ai": journaling_ai,
    }


@router.post("/turn")
async def turn_v2(body: TurnIn, request: Request, user: str | None = Query(default=None)):
    user_id, person_label, person_key = resolve_person(request, user)
    print("TURN V2 FASTAPI ROUTE HIT", user)
    logger.info("ACTIVE_DEV_PERSON", extra={"person_id": user_id, "person_label": person_label, "person_key": person_key})

    if not body.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty text")
    if BUILD32_MODE:
        return await _turn_lightweight(body, user_id)

    minimal_mode = body.capture_only or os.getenv("SAKHI_TURN_MINIMAL_WRITE") == "1" or os.getenv("SAKHI_UNIFIED_INGEST") != "1"

    fast_ingest = {}  # Build 50: avoid ingest work in route; delegate to workers
    turn_context = await orchestrate_turn(
        person_id=user_id,
        text=body.text,
        clarity_hint=body.clarity_phrase,
        capture_only=body.capture_only,
    )
    orchestration_snapshot = dict(turn_context)
    embedding_snapshot = orchestration_snapshot.pop("embedding", [])
    if embedding_snapshot:
        orchestration_snapshot["embedding_dim"] = len(embedding_snapshot)

    entry_id = turn_context.get("entry_id")
    embedding = turn_context.get("embedding") or []
    topics = turn_context.get("topics") or []
    emotion = turn_context.get("emotion") or {}
    stored_intents = turn_context.get("intents") or []
    generated_plans = turn_context.get("plans") or []
    rhythm_trigger_result = turn_context.get("rhythm_triggers")
    meta_reflection_result = turn_context.get("meta_reflection_triggers")

    if body.capture_only:
        schema_ok = False
        try:
            schema_ok = await _unified_ingest_schema_ok()
        except Exception:
            schema_ok = False

        try:
            await publish(
                MEMORY_EVENT,
                {
                    "person_id": user_id,
                    "entry_id": str(entry_id) if entry_id else None,
                    "text": body.text,
                    "layer": "conversation",
                    "ts": datetime.datetime.utcnow().isoformat(),
                },
            )
        except Exception:
            pass

        # Defer everything else to workers/schedulers.
        return {
            "reply": "",
            "entry_id": str(entry_id) if entry_id else None,
            "layer": "conversation",
            "queued_jobs": ["turn_memory_update", "turn_planner_update", "turn_rhythm_update", "turn_persona_update"],
            "status": "recorded",
            "sessionId": user_id,
            "clarityHint": body.clarity_phrase,
            "debug": {
                "capture_only": True,
                "minimal_mode": True,
                "entry_table": "journal_entries",
                "embedding_table": "journal_embeddings",
                "entry_written": bool(entry_id),
                "embedding_enqueued": bool(entry_id),
                "unified_ingest_env": os.getenv("SAKHI_UNIFIED_INGEST"),
                "unified_ingest_schema_ok": schema_ok,
                "note": "No embed-on-read. Embedding is done once on write via background task/worker.",
            },
        }

    try:
        brain_state = await personal_brain.get_brain_state(user_id, force_refresh=False)
        behavior_profile = compute_behavior_profile(brain_state)
    except Exception:
        behavior_profile = {}

    orchestration = await run_unified_turn(user_id, body.text)
    behavior_profile = orchestration.get("behavior_profile") or {}
    planner_payload = orchestration.get("planner")
    insight_bundle = orchestration.get("insight")
    activation = orchestration.get("activation") or {}
    triage = orchestration.get("triage") or {}
    triage_local = triage or extract(body.text, datetime.datetime.utcnow())
    mood_affect = (triage_local.get("slots") or {}).get("mood_affect") if isinstance(triage_local, dict) else {}
    emotion_update = {
        "summary": (mood_affect or {}).get("label"),
        "confidence": float((mood_affect or {}).get("score") or 0.5),
    }

    internal_state = await _load_internal_state(user_id)

    fast_narrative = compute_fast_narrative([], (orchestration.get("brain") or {}).get("soul_state") or {})
    alignment = compute_alignment(
        None,
        (orchestration.get("brain") or {}).get("soul_state") or {},
        (orchestration.get("brain") or {}).get("goals_state") or {},
    )
    fast_rhythm_soul = compute_fast_rhythm_soul_frame(
        [],
        (orchestration.get("brain") or {}).get("rhythm_state") or {},
        (orchestration.get("brain") or {}).get("soul_state") or {},
    )
    fast_esr = compute_fast_esr_frame(
        (orchestration.get("brain") or {}).get("emotion_state") or {},
        (orchestration.get("brain") or {}).get("soul_state") or {},
        (orchestration.get("brain") or {}).get("rhythm_state") or {},
    )
    fast_identity_momentum = compute_fast_identity_momentum(
        [],
        (orchestration.get("brain") or {}).get("soul_state") or {},
        (orchestration.get("brain") or {}).get("emotion_state") or {},
        (orchestration.get("brain") or {}).get("rhythm_state") or {},
    )
    fast_identity_timeline = compute_fast_identity_timeline_frame(
        [],
        (orchestration.get("brain") or {}).get("soul_state") or {},
        (orchestration.get("brain") or {}).get("emotion_state") or {},
        (orchestration.get("brain") or {}).get("rhythm_state") or {},
        (orchestration.get("brain") or {}).get("identity_momentum_state") or {},
    )
    try:
        inner_dialogue = await inner_dialogue_engine.compute_inner_dialogue(
            user_id, body.text, {"triage": triage_local, "behavior_profile": behavior_profile}
        )
    except Exception:
        inner_dialogue = {}
    try:
        microreg_state = await compute_microreg(user_id, body.text)
    except Exception:
        microreg_state = {}
    try:
        tone_state = await compute_tone(user_id)
    except Exception:
        tone_state = {}
    try:
        nudge_row = await q("SELECT nudge_state FROM personal_model WHERE person_id = $1", user_id, one=True) or {}
        nudge_state = nudge_row.get("nudge_state") or {}
    except Exception:
        nudge_state = {}
    try:
        empathy_state = await compute_empathy(user_id, body.text)
    except Exception:
        empathy_state = {}

    micro_goals_meta = None
    text_lower = (body.text or "").lower()
    trigger_phrases = [
        "i want", "i need to", "i should", "i must", "i plan to", "i wish i could",
        "buy", "fix", "join", "start", "learn", "upgrade", "clean", "improve", "reduce", "increase",
    ]
    if any(p in text_lower for p in trigger_phrases):
        try:
            micro_goals_meta = await micro_goals_service.create_micro_goals(user_id, body.text)
        except Exception:
            micro_goals_meta = None

    try:
        continuity_state = await load_continuity(user_id)
    except Exception:
        continuity_state = CONTINUITY_DEFAULT
    try:
        today = datetime.date.today()
        reflection_rows = await q(
            """
            SELECT summary, reflection_date, generated_at
            FROM daily_reflection_cache
            WHERE person_id = $1 AND reflection_date = $2
            """,
            user_id,
            today,
        )
        daily_reflection = reflection_rows[0] if reflection_rows else None
    except Exception:
        daily_reflection = None
    daily_reflection_guard = (
        "Use this reflection only as surface context. "
        "Do not infer emotions, causes, diagnoses, or psychological interpretations."
    )
    evening_closure = None
    closure_guard = (
        "Evening closure is surface-level only. "
        "Do not infer emotions, causes, diagnoses, or psychological interpretations."
    )
    try:
        if datetime.datetime.utcnow().hour >= 20:
            closure_rows = await q(
                """
                SELECT completed, pending, signals, summary, closure_date, generated_at
                FROM daily_closure_cache
                WHERE person_id = $1 AND closure_date = $2
                """,
                user_id,
                today,
            )
            evening_closure = closure_rows[0] if closure_rows else None
    except Exception:
        evening_closure = None
    morning_preview = {}
    morning_preview_guard = (
        "Use morning preview only as surface-level context. "
        "Do not infer mood, meaning, or causes."
    )
    morning_ask = {}
    morning_ask_guard = (
        "Use morning ask only as surface-level context. "
        "Do not infer mood, meaning, or causes."
    )
    morning_momentum = {}
    morning_momentum_guard = (
        "Use morning momentum only as surface-level context. "
        "Do not infer mood, meaning, or causes."
    )
    micro_momentum = {}
    micro_momentum_guard = (
        "Use micro momentum only as small optional suggestions. "
        "Do not infer mood, meaning, or causes."
    )
    micro_recovery = {}
    micro_recovery_guard = (
        "Micro-recovery is optional and surface-level. "
        "No emotion inference or meaning attribution."
    )
    mini_flow = {}
    mini_flow_guard = (
        "Mini-flow is a 10–20 minute routine. Use only as surface context; do not infer emotions or causes."
    )
    micro_journey = {}
    micro_journey_guard = (
        "Micro-journey is deterministic and read-only. Do not infer emotions, causes, or modify the flows."
    )
    micro_journey = {}
    micro_journey_guard = (
        "Micro-journey is deterministic and read-only. Do not infer emotions, causes, or modify the flows."
    )
    focus_path = {}
    focus_path_guard = (
        "Focus path is a simple 3-step plan. Use only as surface context; do not infer emotions or causes."
    )
    try:
        if datetime.datetime.utcnow().hour <= 11:
            preview_rows = await q(
                """
                SELECT focus_areas, key_tasks, reminders, rhythm_hint, summary, preview_date, generated_at
                FROM morning_preview_cache
                WHERE person_id = $1 AND preview_date = $2
                """,
                user_id,
                today,
            )
            morning_preview = preview_rows[0] if preview_rows else {}
            ask_rows = await q(
                """
                SELECT question, reason, ask_date, generated_at
                FROM morning_ask_cache
                WHERE person_id = $1 AND ask_date = $2
                """,
                user_id,
                today,
            )
            morning_ask = ask_rows[0] if ask_rows else {}
            momentum_rows = await q(
                """
                SELECT momentum_hint, suggested_start, reason, momentum_date, generated_at
                FROM morning_momentum_cache
                WHERE person_id = $1 AND momentum_date = $2
                """,
                user_id,
                today,
            )
            morning_momentum = momentum_rows[0] if momentum_rows else {}
    except Exception:
        morning_preview = {}
        morning_ask = {}
        morning_momentum = {}
    try:
        if datetime.datetime.utcnow().hour <= 15:
            micro_rows = await q(
                """
                SELECT nudge, reason, nudge_date, generated_at
                FROM micro_momentum_cache
                WHERE person_id = $1 AND nudge_date = $2
                """,
                user_id,
                today,
            )
        micro_momentum = micro_rows[0] if micro_rows else {}
    except Exception:
        micro_momentum = {}
    gap_hours = None
    try:
        text_lower = (body.text or "").lower()
        restart_phrases = ["restart", "where were we", "how do i restart", "let's continue", "resume"]
        gap_reason = any(p in text_lower for p in restart_phrases)
        last_turn_row = await q(
            "SELECT created_at FROM conversation_turns WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1",
            user_id,
            one=True,
        )
        if last_turn_row and last_turn_row.get("created_at"):
            delta = datetime.datetime.utcnow() - last_turn_row["created_at"]
            gap_hours = delta.total_seconds() / 3600.0
        if gap_reason or (gap_hours is not None and gap_hours > 3) or datetime.datetime.utcnow().hour >= 14:
            recovery_rows = await q(
                """
                SELECT nudge, reason, recovery_date, generated_at
                FROM micro_recovery_cache
                WHERE person_id = $1 AND recovery_date = $2
                """,
                user_id,
                today,
            )
            micro_recovery = recovery_rows[0] if recovery_rows else {}
    except Exception:
        micro_recovery = {}
    try:
        text_lower = (body.text or "").lower()
        focus_patterns = ["help me focus", "where do i start", "work on", "help me begin", "focus on"]
        trigger_focus = any(p in text_lower for p in focus_patterns)
        if trigger_focus:
            path = await generate_focus_path(user_id, intent_text=body.text)
            await persist_focus_path(user_id, path)
            focus_path = path
        if not focus_path:
            path_rows = await q(
                """
                SELECT anchor_step, progress_step, closure_step, intent_source, path_date, generated_at
                FROM focus_path_cache
                WHERE person_id = $1 AND path_date = $2
                """,
                user_id,
                today,
            )
            focus_path = path_rows[0] if path_rows else {}
    except Exception:
        focus_path = {}
    try:
        flow_patterns = ["short routine", "start flow", "10 minute", "focus for 10", "give me a short routine"]
        flow_trigger = any(p in (body.text or "").lower() for p in flow_patterns)
        if flow_trigger:
            flow = await generate_mini_flow(user_id)
            await persist_mini_flow(user_id, flow)
            mini_flow = flow
        if not mini_flow:
            flow_rows = await q(
                """
                SELECT warmup_step, focus_block_step, closure_step, optional_reward, source, flow_date, generated_at, rhythm_slot
                FROM mini_flow_cache
                WHERE person_id = $1 AND flow_date = $2
                """,
                user_id,
                today,
            )
            mini_flow = flow_rows[0] if flow_rows else {}
    except Exception:
        mini_flow = {}
    try:
        journey_rows = await q(
            """
            SELECT flow_count, rhythm_slot, journey, generated_at
            FROM micro_journey_cache
            WHERE person_id = $1
            """,
            user_id,
        )
        micro_journey = journey_rows[0] if journey_rows else {}
    except Exception:
        micro_journey = {}
    try:
        if isinstance(micro_journey, dict) and micro_journey.get("journey"):
            structure = micro_journey.get("journey", {}).get("structure") or {}
            micro_journey["total_estimated_minutes"] = structure.get("total_estimated_minutes")
            micro_journey["pacing"] = structure.get("pacing") or {}
    except Exception:
        pass
    try:
        journey_rows = await q(
            """
            SELECT flow_count, rhythm_slot, journey, generated_at
            FROM micro_journey_cache
            WHERE person_id = $1
            """,
            user_id,
        )
        micro_journey = journey_rows[0] if journey_rows else {}
    except Exception:
        micro_journey = {}
    try:
        state_row = await q(
            """
            SELECT forecast_state, coherence_state, alignment_state
            FROM personal_model
            WHERE person_id = $1
            """,
            user_id,
            one=True,
        ) or {}
    except Exception:
        state_row = {}

    try:
        moment_model = compute_moment_model(
            emotion_state=(orchestration.get("brain") or {}).get("emotion_state") or {},
            coherence_state=state_row.get("coherence_state") or {},
            alignment_state=state_row.get("alignment_state") or {},
            mind_state={"cognitive_load": internal_state.get("cognitive_load")},
            forecast_state=state_row.get("forecast_state") or {},
            continuity_state=continuity_state or {},
            gap_hours=gap_hours,
            restart=gap_reason if "gap_reason" in locals() else False,
            active_scaffolds={
                "focus_path": bool(focus_path),
                "mini_flow": bool(mini_flow),
                "micro_journey": bool(micro_journey),
            },
        )
    except Exception:
        moment_model = {}
    try:
        evidence_pack = await select_evidence_anchors(user_id)
    except Exception:
        evidence_pack = {}
    try:
        deliberation_scaffold = compute_deliberation_scaffold(
            moment_model=moment_model,
            evidence_pack=evidence_pack,
            conflict_state=state_row.get("conflict_state") or {},
            alignment_state=state_row.get("alignment_state") or {},
            identity_state=state_row.get("identity_state") or {},
            forecast_state=state_row.get("forecast_state") or {},
            continuity_state=continuity_state or {},
        )
    except Exception:
        deliberation_scaffold = None
    try:
        reflection_trace_payload = build_reflection_trace(
            person_id=user_id,
            turn_id=turn_id,
            session_id=user_id,
            moment_model=moment_model or {},
            evidence_pack=evidence_pack or {},
            deliberation_scaffold=deliberation_scaffold,
        )
        await persist_reflection_trace(dbexec, reflection_trace_payload)
    except Exception:
        reflection_trace_payload = None

    metadata_payload = {
        "entry_id": entry_id,
        "topics": topics,
        "emotion": emotion,
        "intents": stored_intents,
        "plans": generated_plans,
        "rhythm_triggers": rhythm_trigger_result,
        "meta_reflection_triggers": meta_reflection_result,
        "behavior_profile": behavior_profile,
        "activation": activation,
        "triage": triage,
        "emotion_update": emotion_update,
        "internal_state": internal_state,
        "cognitive_load": internal_state.get("cognitive_load"),
        "priority": internal_state.get("priority"),
        "priority_topics": internal_state.get("priority_topics"),
        "soul_values": internal_state.get("soul_values"),
        "soul_identity": internal_state.get("soul_identity"),
        "life_themes": internal_state.get("life_themes"),
        "identity_graph": internal_state.get("identity_graph"),
        "narrative_trace": fast_narrative,
        "alignment_frame": alignment,
        "rhythm_soul_frame": fast_rhythm_soul,
        "emotion_soul_rhythm_frame": fast_esr,
        "identity_momentum_frame": fast_identity_momentum,
        "identity_timeline_frame": fast_identity_timeline,
        "inner_dialogue": inner_dialogue,
        "tone_state": tone_state,
        "nudge_state": nudge_state,
        "empathy_state": empathy_state,
        "continuity": continuity_state,
        "micro_goals": micro_goals_meta,
        "daily_reflection": daily_reflection,
        "microreg_state": microreg_state,
        "daily_reflection_guard": daily_reflection_guard,
        "evening_closure": evening_closure,
        "evening_closure_guard": closure_guard,
        "morning_preview": morning_preview,
        "morning_preview_guard": morning_preview_guard,
        "morning_ask": morning_ask,
        "morning_ask_guard": morning_ask_guard,
        "morning_momentum": morning_momentum,
        "morning_momentum_guard": morning_momentum_guard,
        "micro_momentum": micro_momentum,
        "micro_momentum_guard": micro_momentum_guard,
        "micro_recovery": micro_recovery,
        "micro_recovery_guard": micro_recovery_guard,
        "focus_path": focus_path,
        "focus_path_guard": focus_path_guard,
        "mini_flow": mini_flow,
        "mini_flow_guard": mini_flow_guard,
        "micro_journey": micro_journey,
        "micro_journey_guard": micro_journey_guard,
        "moment_model": moment_model,
        "evidence_pack": evidence_pack,
        "deliberation_scaffold": deliberation_scaffold,
    }

    # background task routing refresh when new task intent might be present
    try:
        if stored_intents:
            from sakhi.apps.worker.tasks.task_routing_worker import enqueue_task_routing
            enqueue_task_routing(user_id)
    except Exception:
        pass

    reply_bundle = await generate_reply(
        person_id=user_id,
        user_text=body.text,
        metadata=metadata_payload,
        behavior_profile=behavior_profile,
    )
    reply_text = reply_bundle.get("reply", "")
    tone_blueprint = reply_bundle.get("tone_blueprint") or {}
    journaling_ai = reply_bundle.get("journaling_ai")
    result = {
        "reply": reply_text,
        "sessionId": user_id,
        "tone": tone_blueprint.get("style") or "auto",
        "toneBlueprint": tone_blueprint,
        "tone_used": (tone_state or {}).get("final"),
        "mood": tone_blueprint.get("mirroring", {}).get("emotion"),
        "clarityHint": body.clarity_phrase,
        "lastObjective": None,
        "suggestions": [],
        "decisions": [],
        "journaling_ai": journaling_ai,
        "behavior_profile": behavior_profile,
        "internal_state": internal_state,
        "cognitive_load": internal_state.get("cognitive_load"),
        "priority": internal_state.get("priority"),
        "priority_topics": internal_state.get("priority_topics"),
        "soul_values": internal_state.get("soul_values"),
        "soul_identity": internal_state.get("soul_identity"),
        "life_themes": internal_state.get("life_themes"),
        "identity_graph": internal_state.get("identity_graph"),
        "rhythm_soul_frame": fast_rhythm_soul,
        "emotion_soul_rhythm_frame": fast_esr,
        "identity_momentum_frame": fast_identity_momentum,
        "identity_timeline_frame": fast_identity_timeline,
        "inner_dialogue": inner_dialogue,
        "tone_state": tone_state,
        "nudge_state": nudge_state,
        "empathy_state": empathy_state,
        "continuity": continuity_state,
        "micro_goals": micro_goals_meta,
        "daily_reflection": daily_reflection,
        "microreg_state": microreg_state,
        "evening_closure": evening_closure,
        "morning_preview": morning_preview,
        "morning_ask": morning_ask,
        "morning_momentum": morning_momentum,
        "micro_momentum": micro_momentum,
        "micro_recovery": micro_recovery,
        "focus_path": focus_path,
        "mini_flow": mini_flow,
        "micro_journey": micro_journey,
        "moment_model": moment_model,
        "evidence_pack": evidence_pack,
        "deliberation_scaffold": deliberation_scaffold,
    }

    session_id = result.get("sessionId") or result.get("session_id")
    reflection_hint = None
    try:
        summary_row = await q(
            """
            SELECT summary
            FROM meta_reflections
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
        )
        if summary_row:
            reflection_hint = (summary_row[0]["summary"] or "").strip()[:200]
    except Exception:
        reflection_hint = None

    if minimal_mode:
        mem_context = ""
    else:
        try:
            mem_context = await synthesize_memory_context(
                person_id=user_id,
                user_query=body.text,
                limit=350,
            )
        except Exception:
            mem_context = ""

    # Patch AA — unified reasoning engine
    reasoning = {}
    # Build 50: avoid heavy reasoning unless reflective/stress/growth
    if behavior_profile.get("conversation_depth") == "reflective" or behavior_profile.get("session_context", {}).get("reason") in {"stress", "growth"}:
        try:
            reasoning = await run_reasoning(person_id=user_id, query=body.text, memory_context=mem_context)
        except Exception as exc:  # pragma: no cover - do not break turn flow
            reasoning = {
                "insights": [],
                "contradictions": [],
                "opportunities": [],
                "open_loops": [],
                "error": str(exc),
            }

    # Patch DD — Memory recall (can be expensive: includes query embedding).
    if minimal_mode:
        recall = []
    else:
        try:
            recall = await memory_recall(person_id=user_id, query=body.text, limit=5)
        except Exception as exc:  # pragma: no cover - best effort
            recall = {"error": str(exc)}

    # Planner work is deferred to workers; keep payload None to avoid inline heavy calls.

    try:
        persona_update = await update_session_persona(user_id, body.text)
    except Exception as exc:  # pragma: no cover - best effort
        persona_update = {"error": str(exc)}

    try:
        topic_state = await update_conversation_topics(user_id, body.text)
    except Exception as exc:  # pragma: no cover - best effort
        topic_state = {"error": str(exc)}

    # Backup topic extraction if state is empty for signals
    topics_for_signals = topic_state.get("topics") if isinstance(topic_state, dict) else []
    if not topics_for_signals:
        try:
            topics_for_signals = await extract_topics(body.text)
        except Exception:
            topics_for_signals = []

    result["topics"] = topic_state

    # Inline insight generation removed (Build 50); worker handles insight creation.
    insight_bundle = None

    response_text = (result.get("reply") or "").strip()
    dialog_state = {
        "intent": result.get("lastObjective"),
        "tone": result.get("tone"),
        "emotion": result.get("mood"),
        "context": {
            "reasoning": reasoning,
            "clarity_hint": result.get("clarityHint"),
            "suggestions": result.get("suggestions"),
            "decisions": result.get("decisions"),
            "reflection_hint": reflection_hint,
        },
        "response_preview": response_text[:120],
    }

    memory_write = await write_turn_memory(
        person_id=user_id,
        dialog_state=dialog_state,
        reasoning=reasoning,
        entry_id=session_id,
        user_text=body.text,
    )

    # Best-effort continuity update with latest emotion/tone/empathy/forecast snapshot
    try:
        await update_continuity(
            user_id,
            {
                "type": "text_message",
                "text": body.text,
                "ts": datetime.datetime.utcnow().isoformat(),
                "emotion": emotion,
                "tone_state": tone_state,
                "empathy_state": empathy_state,
                "microreg_state": microreg_state,
                "forecast_state": (orchestration.get("brain") or {}).get("forecast_state") or {},
            },
            memory_short_term=[],
            pattern_sense=(orchestration.get("brain") or {}).get("pattern_sense"),
        )
    except Exception:
        pass

    # ----------------------------------------------------------------------
    # Patch BB — Expose reasoning in the debug panel
    # ----------------------------------------------------------------------
    engine_snapshot = deepcopy(result)

    debug_section = {
        "input_text": body.text,
        "raw_engine_output": engine_snapshot,
        "reasoning": reasoning,
        "topics": topic_state,
        "behavior_profile": behavior_profile,
        "activation": activation,
        "triage": triage,
        "insights": insight_bundle,
        "flags": {
            "clarity_hint_applied": bool(body.clarity_phrase),
            "has_intents": bool(result.get("intents")),
            "has_memory_updates": bool(result.get("memoryUpdate")),
        },
    }

    if isinstance(result.get("debug"), dict):
        existing = result["debug"]
        existing.update(debug_section)
        result["debug"] = existing
    else:
        result["debug"] = debug_section

    api_debug = {
        "reasoning": reasoning,
        "engine_raw": engine_snapshot,
        "loop_trace": debug_section,
        "memory_context": mem_context,
        "persona": persona_update,
        "topics": topic_state,
        "behavior_profile": behavior_profile,
        "insights": insight_bundle,
        "activation": activation,
        "triage": triage,
        "reflection_trace": reflection_trace_payload,
    }

    human_insights = None
    if os.getenv("SAKHI_DEV_DEBUG") == "1":
        try:
            payload = await assemble_human_debug_panel(
                person_id=user_id,
                input_text=body.text,
                reply_text=response_text,
            )
        except Exception as exc:  # pragma: no cover - best effort
            payload = {"error": str(exc)}
        human_insights = payload or None

    # ----------------------------------------------------------------------
    # NEW: Narrative Trace (non-technical explanation)
    # ----------------------------------------------------------------------
    try:
        from sakhi.libs.reasoning.narrative import build_narrative_trace
    except Exception:  # pragma: no cover - import guards
        build_narrative_trace = None

    narrative_trace = None
    unified_narrative = None
    if build_narrative_trace:
        try:
            narrative_trace = await build_narrative_trace(
                person_id=user_id,
                text=body.text,
                reply=response_text,
                memory_context=mem_context,
                reasoning=reasoning,
                intents=stored_intents,
                emotion=emotion,
                topics=topics,
            )
        except Exception:  # pragma: no cover - best effort
            narrative_trace = None

    if os.getenv("SAKHI_DEV_DEBUG") == "1":
        try:
            unified_narrative = build_unified_narrative(
                {
                    "person_id": user_id,
                    "input_text": body.text,
                    "reply_text": response_text,
                    "triage": turn_context.get("triage"),
                    "intents": stored_intents,
                    "emotion": emotion,
                    "topics": topics,
                    "memory_context": mem_context,
                    "reasoning": reasoning,
                    "personal_model": persona_update,
                    "planner": planner_payload,
                    "layer": "conversation",
                }
            )
        except Exception as exc:
            unified_narrative = {"error": str(exc)}

    try:
        await publish(
            MEMORY_EVENT,
            {
                "person_id": user_id,
                "entry_id": str(entry_id) if entry_id else None,
                "text": body.text,
                "layer": "conversation",
                "ts": datetime.datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        pass

    if os.getenv("SAKHI_UNIFIED_INGEST") == "1" and entry_id and not minimal_mode:
        if not await _unified_ingest_schema_ok():
            logger.warning(
                "[UnifiedIngest] Skipping ingest_heavy: DB schema missing memory_short_term.entry_id (set SAKHI_UNIFIED_INGEST=0 or migrate schema)",
            )
        else:
            try:
                asyncio.create_task(
                    ingest_heavy(
                        person_id=user_id,
                        entry_id=entry_id,
                        text=body.text,
                        ts=datetime.datetime.utcnow(),
                    )
                )
            except Exception as exc:
                logger.warning(
                    "[UnifiedIngest] turn_v2 ingest_heavy enqueue failed user=%s entry=%s error=%s",
                    user_id,
                    entry_id,
                    exc,
                )

    turn_id = str(entry_id) if entry_id else str(uuid4())
    queued_jobs = [
        "turn_memory_update",
        "turn_planner_update",
        "turn_rhythm_update",
        "turn_persona_update",
        "turn_insight_update",
        "brain_refresh",
    ]
    inferred_intent = stored_intents[0] if stored_intents else (topics_for_signals[0] if topics_for_signals else None)
    facets_for_worker = {
        "emotion": emotion,
        "intents": stored_intents,
        "intent": inferred_intent,
        "topics": topics_for_signals or topics,
        "plans": generated_plans,
        "triage": turn_context.get("triage"),
    }
    enqueue_turn_jobs(
        turn_id,
        user_id,
        queued_jobs,
        {
            "text": body.text,
            "ts": datetime.datetime.utcnow().isoformat(),
            "facets": facets_for_worker,
            "thread_id": user_id,
            "behavior_profile": behavior_profile,
            "mode": "today",
            "emotion_update": emotion_update,
            "persona_update": persona_update,
        },
    )

    return {
        **result,
        "unified_fast": fast_ingest,
        "entry_id": entry_id,
        "topics_snapshot": topics,
        "topic_state": topic_state,
        "emotion": emotion,
        "intents_detected": stored_intents,
        "plans_generated": generated_plans,
        "rhythm_triggered": rhythm_trigger_result,
        "meta_reflection_triggered": meta_reflection_result,
        "embedding_dim": len(embedding),
        "orchestration": orchestration_snapshot,
        "reasoning": reasoning,
        "memory_write": memory_write,
        "memory_recall": recall,
        "memory_context": mem_context,
        "reflection_hint": reflection_hint,
        "planner": planner_payload,
        "persona_update": persona_update,
        "debug": api_debug,
        "human_insights": human_insights,
        "narrative_trace": narrative_trace,
        "narrative": unified_narrative,
        "journaling_ai": journaling_ai,
        "insight_bundle": insight_bundle,
    }
