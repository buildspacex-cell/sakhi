from __future__ import annotations

import json
import os
import time
import datetime
import logging
import asyncio
from typing import Any, Dict

from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
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
from sakhi.apps.api.services.turn.deterministic_context_loader import (
    DeterministicContext,
    load_deterministic_context,
    load_internal_state,
)
from sakhi.apps.api.services.turn.reply_service import build_turn_reply
from sakhi.apps.api.services.turn.async_triggers import enqueue_turn_jobs
from sakhi.apps.api.services.continuity.chat import build_continuity_pack
from sakhi.apps.api.services.conversation.topic_manager import extract_topics, update_conversation_topics
from sakhi.apps.api.core.dialog_state import update_dialog_state
from sakhi.apps.api.services.memory.ingest_reasoning import ingest_reasoning_to_memory
from sakhi.core.soul.narrative_engine import compute_fast_narrative
from sakhi.core.soul.alignment_engine import compute_alignment
from sakhi.core.rhythm.rhythm_soul_engine import compute_fast_rhythm_soul_frame
from sakhi.core.emotion.emotion_soul_rhythm_engine import compute_fast_esr_frame
from sakhi.core.soul.identity_momentum_engine import compute_fast_identity_momentum
from sakhi.core.soul.identity_timeline_engine import compute_fast_identity_timeline_frame
from sakhi.apps.engine.inner_dialogue import engine as inner_dialogue_engine
from sakhi.apps.engine.tone import compute_tone
from sakhi.apps.engine.continuity import update_continuity
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
from sakhi.apps.services import micro_goals_service
from sakhi.apps.api.utils.person_resolver import resolve_person
from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.recommendations import (
    build_recommendation_context,
    generate_personalized_recommendations,
)
from sakhi.apps.api.services.calendar import (
    detect_scheduling_intent,
    parse_scheduling_request,
    get_events_for_day,
    get_week_summary,
    find_best_times,
    detect_confirmation,
    save_pending_request,
    get_pending_request,
    execute_pending_confirmation,
    SchedulingIntent,
)
from sakhi.apps.api.services.relationships.repository import (
    get_relationships_needing_attention,
    get_relationship_for_scheduling,
)
from sakhi.apps.api.services.mesh import (
    find_by_handle,
    are_connected,
    get_trust_level,
    get_profile,
    initiate_coordination,
    get_pending_proposals,
    respond_to_proposal,
    ProposalRequest,
    CoordinationType,
)
from sakhi.apps.api.services.vision.context import (
    get_relevant_media_for_context,
    add_to_visual_context,
)
from sakhi.apps.api.services.context_router import (
    ALL_MODULES,
    map_triage_to_intents,
    # load_recent_intent_evolution parked for continuity MVP — restore with intent evolution
)
from sakhi.apps.api.services.email.integration import (
    get_email_context_for_conversation,
    get_email_friction_contribution,
)
from sakhi.apps.api.services.ayurveda.causal_reasoning import (
    explain_friction_state as explain_friction,
)
from sakhi.apps.api.services.email.contact_preferences import (
    get_preferences as get_contact_preferences,
    format_preferences_for_llm,
)
from sakhi.apps.api.services.vision.processor import (
    process_image,
    analyze_screenshot,
)
from sakhi.apps.api.services.vision.storage import (
    store_media,
    get_media,
    update_media_analysis,
    link_media_to_entry,
)
from sakhi.apps.api.services.vision.memory import learn_from_image
from sakhi.apps.api.services.memory.sessions import (
    ensure_session,
    append_turn,
    load_recent_turns,
    load_context_with_summary,
)
from sakhi.apps.api.services.agent.chat_bridge import (
    detect_agent_task_intent,
    detect_task_confirmation,
    create_pending_task,
    get_pending_task as get_pending_agent_task,
    confirm_task,
    reject_task,
    generate_task_plan,
    start_task_execution,
    get_task_execution_state,
    approve_execution_step,
    format_task_plan_for_chat,
    format_execution_update_for_chat,
    AgentTaskType,
    get_active_agent_for_person,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["conversation-v2"])


class _SkipModule(Exception):
    """Raised to skip a gated module block when the context router didn't activate it."""
    pass

_UNIFIED_INGEST_SCHEMA_OK: bool | None = None


def _agent_task_execution_enabled() -> bool:
    """Agent task planning/execution is opt-in and disabled by default."""
    raw = os.getenv("SAKHI_ENABLE_AGENT_EXECUTION", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _build_agent_task_guard(enabled: bool) -> str:
    if not enabled:
        return (
            "Agent task planning and execution are disabled in this environment. "
            "Do not offer to start autonomous tasks, create execution plans, or ask for "
            "confirmation to run them. If the user asks for an action, respond with "
            "guidance, options, or a manual checklist only."
        )
    return (
        "When agent_task_context is present, respond according to the task state:\n"
        "1. NEW TASK (new_task present): Present the formatted_plan naturally. "
        "Ask 'Would you like me to proceed?' or 'Should I start?'\n"
        "2. PENDING CONFIRMATION (awaiting_confirmation): The user hasn't confirmed yet. "
        "Gently remind them of the pending task if relevant.\n"
        "3. EXECUTION (execution present): Report progress. If waiting_approval, "
        "explain what step needs approval and ask for confirmation.\n"
        "4. REJECTED: Acknowledge cancellation briefly and move on.\n"
        "5. COMPLETED: Celebrate the completion and summarize what was done.\n"
        "CRITICAL: Never execute agent tasks without explicit user confirmation."
    )


@router.get("/turn/probe")
async def __turn_v2_probe(request: Request):
    print("🔥 TURN V2 PROBE HIT", request.url)
    return JSONResponse({"probe": "ok"})


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
    source: str = "text"  # "text", "voice", or "offload"
    ts: str | None = None  # Optional experience timestamp (ISO 8601); defaults to now
    client_id: str | None = None  # Stable device-generated id for idempotent capture retries
    # Vision support
    image_data: str | None = None  # Base64 encoded image
    image_mime_type: str | None = None  # e.g., "image/png"
    media_ids: list[str] | None = None  # Previously uploaded media IDs


_DEEP_REFLECT_MIN_MOMENTS = 4


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_deep_reflect_signal(continuity_pack: dict[str, Any]) -> Dict[str, Any]:
    surface = continuity_pack.get("surface") if isinstance(continuity_pack.get("surface"), dict) else {}
    history = (
        continuity_pack.get("history_compact")
        if isinstance(continuity_pack.get("history_compact"), dict)
        else {}
    )
    evidence = continuity_pack.get("evidence") if isinstance(continuity_pack.get("evidence"), list) else []

    mirror_allowed = bool(surface.get("mirror_allowed", True))
    detail_allowed = bool(surface.get("detail_allowed"))
    selected_count = max(
        _safe_int(history.get("element_count"), 0),
        len(evidence),
    )

    ready = bool(
        mirror_allowed
        and detail_allowed
        and selected_count >= _DEEP_REFLECT_MIN_MOMENTS
    )
    if not mirror_allowed:
        reason = "mirror_blocked"
    elif not detail_allowed:
        reason = "detail_blocked"
    elif selected_count < _DEEP_REFLECT_MIN_MOMENTS:
        reason = "insufficient_depth"
    else:
        reason = "ready"

    return {
        "ready": ready,
        "reason": reason,
        "mirror_allowed": mirror_allowed,
        "detail_allowed": detail_allowed,
        "selected_count": selected_count,
        "min_moments": _DEEP_REFLECT_MIN_MOMENTS,
    }


def _build_public_continuity_signal(continuity_pack: Any) -> Dict[str, Any] | None:
    """Expose a minimal, non-debug continuity summary safe for product clients."""
    if not isinstance(continuity_pack, dict):
        return None
    topic_key = str(continuity_pack.get("topic_key") or "").strip()
    if not topic_key:
        return None
    topic_label = str(continuity_pack.get("topic_label") or "").strip() or topic_key
    payload: Dict[str, Any] = {
        "topic_key": topic_key,
        "topic_label": topic_label,
        "deep_reflect": _build_deep_reflect_signal(continuity_pack),
    }
    for optional_key in ("candidate_topics", "cross_context", "whole_story", "life_dimensions", "what_changed", "open_loops"):
        optional_value = continuity_pack.get(optional_key)
        if optional_value not in (None, [], {}, ""):
            payload[optional_key] = optional_value
    return payload


_CAPTURE_ONLY_QUEUED_JOBS = [
    "turn_memory_update",
    "episodic_consolidation_v21",
    "preference_learning",
    "journal_enrich",
    "intent_extraction",
]


def _build_capture_only_worker_payload(
    *,
    text: str,
    ts_iso: str,
    entry_id: str | None,
    emotion: dict[str, Any],
    intents: list[Any],
    topics: list[Any],
    plans: list[Any],
    triage: dict[str, Any],
    layer: str,
) -> dict[str, Any]:
    inferred_intent = intents[0] if intents else (topics[0] if topics else None)
    return {
        "text": text,
        "ts": ts_iso,
        "entry_id": entry_id,
        "layer": layer,
        "facets": {
            "emotion": emotion,
            "intents": intents,
            "intent": inferred_intent,
            "topics": topics,
            "plans": plans,
            "triage": triage,
        },
    }


# NOTE: _load_internal_state now uses the shared deterministic_context_loader module.
# This ensures consistency between /v2/turn and /lab/live-turn endpoints.
# See: sakhi/apps/api/services/turn/deterministic_context_loader.py
async def _load_internal_state(person_id: str) -> Dict[str, Any]:
    """Load internal state using the shared deterministic context loader."""
    return await load_internal_state(person_id)




async def _write_turn_memory(
    person_id: str,
    dialog_state: Dict[str, Any],
    reasoning: Dict[str, Any] | None,
    entry_id: str | None,
    user_text: str,
) -> Dict[str, Any]:
    """
    Write turn memory (replaces legacy memory_write_controller).
    Handles dialog state and reasoning ingestion.
    """
    dialog_result: Dict[str, Any] | None = None
    reasoning_result: Dict[str, Any] | None = None

    try:
        dialog_result = await update_dialog_state(
            person_id=person_id,
            conv_id=entry_id or person_id,
            state=dialog_state,
        )
    except Exception as exc:
        dialog_result = {"error": str(exc)}

    if reasoning:
        try:
            reasoning_result = await ingest_reasoning_to_memory(
                person_id=person_id,
                reasoning=reasoning,
                source_turn_id=entry_id or person_id,
            )
        except Exception as exc:
            reasoning_result = {"error": str(exc)}

    return {"dialog_state": dialog_result, "reasoning_ingest": reasoning_result}


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
    # Per-turn workers: Only essential memory capture + episodic consolidation
    # Other state workers (ayurvedic, rhythm, soul, etc.) run on daily schedule
    # Context comes from: conversation_history + memory_recall + memory_graph + personal_model
    queued_jobs = [
        "turn_memory_update",           # Essential: captures turn to memory
        "episodic_consolidation_v21",   # Essential: creates episodes + state vectors
        "preference_learning",          # Learn preferences from "I like..." statements
    ]
    # MOVED TO DAILY SCHEDULE (see scheduler.py):
    # - ayurvedic_pipeline, rhythm_forecast, identity_momentum_deep
    # - emotion_soul_rhythm_deep, esr, soul_refresh, longitudinal_update, rhythm_soul_deep
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


async def _run_post_reply_processing(
    user_id: str,
    text: str,
    source: str,
    clarity_phrase: str | None,
    session_id: Any,
    entry_id: Any,
    reply_text: str,
    tone_blueprint: Dict,
    minimal_mode: bool,
    behavior_profile: Dict,
    emotion: Any,
    tone_state: Any,
    empathy_state: Any,
    microreg_state: Any,
    brain_state: Dict,
    stored_intents: list,
    topics: list,
    generated_plans: list,
    turn_context: Dict,
    emotion_update: Dict,
    experience_ts: str | None = None,
    turn_id: str | None = None,
    t_start: float | None = None,
    has_continuity: bool = False,
) -> None:
    """Fire-and-forget post-reply processing. Runs in background after response is sent."""
    # Use caller-supplied experience timestamp when available (e.g. simulation/demo)
    _ts_iso = experience_ts or datetime.datetime.utcnow().isoformat()
    _ts_dt = (
        datetime.datetime.fromisoformat(_ts_iso.replace("Z", "+00:00"))
        if experience_ts
        else datetime.datetime.utcnow()
    )
    try:
        # 1. Persist conversation turns for continuity
        if session_id:
            try:
                await append_turn(user_id=user_id, session_id=str(session_id), role="user", text=text, source=source)
                if reply_text:
                    await append_turn(
                        user_id=user_id, session_id=str(session_id), role="assistant",
                        text=reply_text, tone=tone_blueprint.get("style"), source=source,
                    )
            except Exception as exc:
                logger.error("[turn_v2:bg] Turn persistence failed: %s", exc)

        # 2. Update persona + topics
        persona_update = None
        topic_state: Dict[str, Any] = {}
        try:
            persona_update = await update_session_persona(user_id, text)
        except Exception:
            pass
        try:
            topic_state = await update_conversation_topics(user_id, text)
        except Exception:
            pass

        # 3. Build dialog state and write turn memory
        topics_for_signals = topic_state.get("topics") if isinstance(topic_state, dict) else []
        if not topics_for_signals:
            try:
                topics_for_signals = await extract_topics(text)
            except Exception:
                topics_for_signals = []

        response_preview = (reply_text or "").strip()[:120]
        dialog_state = {
            "intent": None,
            "tone": tone_blueprint.get("style") or "auto",
            "emotion": tone_blueprint.get("mirroring", {}).get("emotion"),
            "context": {"clarity_hint": clarity_phrase},
            "response_preview": response_preview,
        }
        try:
            await _write_turn_memory(
                person_id=user_id, dialog_state=dialog_state, reasoning=None,
                entry_id=str(session_id) if session_id else user_id, user_text=text,
            )
        except Exception as exc:
            logger.error("[turn_v2:bg] _write_turn_memory failed: %s", exc)

        # 4. Update session continuity
        try:
            await update_continuity(
                user_id,
                {
                    "type": "text_message",
                    "text": text,
                    "ts": _ts_iso,
                    "emotion": emotion,
                    "tone_state": tone_state,
                    "empathy_state": empathy_state,
                    "microreg_state": microreg_state,
                    "forecast_state": brain_state.get("forecast_state") or {},
                },
                memory_short_term=[],
                pattern_sense=brain_state.get("pattern_sense"),
            )
        except Exception:
            pass

        # 5. Publish memory event
        try:
            await publish(
                MEMORY_EVENT,
                {
                    "person_id": user_id,
                    "entry_id": str(entry_id) if entry_id else None,
                    "text": text,
                    "layer": "conversation",
                    "ts": _ts_iso,
                },
            )
        except Exception:
            pass

        # 6. Unified ingest (heavy memory processing)
        if entry_id and not minimal_mode:
            try:
                schema_ok = await _unified_ingest_schema_ok()
                if schema_ok:
                    await ingest_heavy(
                        person_id=user_id, entry_id=entry_id,
                        text=text, ts=_ts_dt,
                    )
            except Exception as exc:
                logger.warning("[turn_v2:bg] ingest_heavy failed: %s", exc)

        # 7. Enqueue worker jobs (CRITICAL — feeds background workers)
        turn_id = str(entry_id) if entry_id else str(uuid4())
        queued_jobs = [
            "turn_memory_update",
            "episodic_consolidation_v21",
            "preference_learning",
            "journal_enrich",
            "intent_extraction",
            "continuity_enrichment",
        ]
        inferred_intent = stored_intents[0] if stored_intents else (
            topics_for_signals[0] if topics_for_signals else None
        )
        facets_for_worker = {
            "emotion": emotion,
            "intents": stored_intents,
            "intent": inferred_intent,
            "topics": topics_for_signals or topics,
            "plans": generated_plans,
            "triage": turn_context.get("triage"),
        }
        disable_queue = os.getenv("SAKHI_DISABLE_QUEUE") == "1"
        payload = {
            "text": text,
            "ts": _ts_iso,
            "entry_id": str(entry_id) if entry_id else None,
            "facets": facets_for_worker,
            "thread_id": user_id,
            "behavior_profile": behavior_profile,
            "mode": "today",
            "emotion_update": emotion_update,
            "persona_update": persona_update,
        }
        if disable_queue:
            from sakhi.apps.worker.pipelines.turn_updates.runner import process_turn_job_async
            for job_type in queued_jobs:
                try:
                    await process_turn_job_async(job_type=job_type, turn_id=turn_id, person_id=user_id, payload=payload)
                except Exception as exc:
                    logger.warning("[turn_v2:bg] inline job failed type=%s err=%s", job_type, exc)
        else:
            enqueue_turn_jobs(turn_id, user_id, queued_jobs, payload)

        logger.info("[turn_v2:bg] post-reply completed user=%s turn_id=%s jobs=%s", user_id, turn_id, queued_jobs)

        # Server-side analytics mirror — ensures turn events land even if client drops
        try:
            from sakhi.libs.analytics import capture as analytics_capture
            _latency = int((time.monotonic() - t_start) * 1000) if t_start is not None else 0
            analytics_capture(user_id, "turn_completed", {
                "latency_ms": _latency,
                "status": 200,
                "request_id": turn_id,
                "has_continuity": has_continuity,
            })
        except Exception:
            pass  # Analytics must never affect response

    except Exception as exc:
        logger.error("[turn_v2:bg] post-reply processing failed: %s", exc, exc_info=True)


@router.post("/turn")
async def turn_v2(body: TurnIn, request: Request, user: str | None = Query(default=None)):
    t_start = time.monotonic()
    user_id, person_label, person_key = await resolve_person(request, user)
    logger.info("[turn_v2] entry start user=%s person_id=%s label=%s", user, user_id, person_label)
    logger.info("ACTIVE_DEV_PERSON", extra={"person_id": user_id, "person_label": person_label, "person_key": person_key})

    if not body.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty text")

    # Stable turn identifier — used by reflection trace, worker enqueue, etc.
    turn_id = str(uuid4())

    # Ensure conversation session and load history for context
    # Hybrid approach: recent turns verbatim + summary of older context
    recent_limit = int(os.getenv("SAKHI_CONVERSATION_RECENT_LIMIT", "8"))  # Verbatim turns
    compress_threshold = int(os.getenv("SAKHI_CONVERSATION_COMPRESS_THRESHOLD", "16"))  # When to compress
    session_id = None
    conversation_history = []
    session_summary = ""
    total_turns = 0

    # Step 1: Ensure session exists (critical for saving turns)
    try:
        session_id = await ensure_session(user_id, slug="converse")
        logger.info("[turn_v2] Session ensured: %s", session_id)
    except Exception as exc:
        logger.error("[turn_v2] CRITICAL - Failed to ensure session: %s", exc)

    # Step 2: Load context (non-critical - can proceed without history)
    if session_id:
        try:
            context_data = await load_context_with_summary(str(session_id), recent_limit=recent_limit)
            conversation_history = context_data.get("recent_turns", [])
            session_summary = context_data.get("session_summary", "")
            total_turns = context_data.get("total_turns", 0)

            # Enqueue compression to background if needed (avoid inline LLM call)
            if total_turns >= compress_threshold and not session_summary:
                try:
                    enqueue_turn_jobs(
                        "session-compress",
                        user_id,
                        ["session_compress"],
                        {"session_id": str(session_id), "keep_recent": recent_limit},
                    )
                    logger.info("[turn_v2] Enqueued session_compress for session=%s turns=%s", session_id, total_turns)
                except Exception as comp_exc:
                    logger.warning("[turn_v2] Failed to enqueue session_compress: %s", comp_exc)
        except Exception as exc:
            # Session exists but context loading failed - session_id is preserved for saving turns
            logger.warning("[turn_v2] Context load failed (session preserved): %s", exc)

    # ==========================================================
    # VISION CONTEXT: Process images if provided
    # ==========================================================
    vision_context = {}
    if body.image_data or body.media_ids:
        try:
            import base64

            # Process inline image if provided
            if body.image_data:
                mime_type = body.image_mime_type or "image/png"
                image_bytes = base64.b64decode(body.image_data)

                # Store the image
                media_record = await store_media(
                    person_id=user_id,
                    media_bytes=image_bytes,
                    mime_type=mime_type,
                    media_type="image",
                    source="chat",
                    context=body.text[:100] if body.text else None,
                )

                # Analyze the image
                analysis_result = await process_image(
                    image_bytes,
                    mime_type=mime_type,
                    context=body.text,
                )
                analysis_dict = analysis_result.model_dump()

                # Update media with analysis
                await update_media_analysis(
                    media_id=media_record.id,
                    description=analysis_dict.get("description", ""),
                    extracted_text=analysis_dict.get("extracted_text"),
                    analysis=analysis_dict,
                )

                # Learn from the image
                await learn_from_image(
                    person_id=user_id,
                    media_id=media_record.id,
                    analysis=analysis_dict,
                    description=analysis_dict.get("description", ""),
                )

                # Add to session context
                if session_id:
                    await add_to_visual_context(
                        person_id=user_id,
                        session_id=str(session_id),
                        media_id=media_record.id,
                        description=analysis_dict.get("description", ""),
                    )

                vision_context["current_image"] = {
                    "media_id": media_record.id,
                    "description": analysis_dict.get("description", ""),
                    "extracted_text": analysis_dict.get("extracted_text"),
                    "objects": analysis_dict.get("objects", []),
                    "tags": analysis_dict.get("tags", []),
                }

                logger.info(
                    "[turn_v2] Vision: processed image %s - %s",
                    media_record.id,
                    analysis_dict.get("description", "")[:50],
                )

            # Load previously uploaded media if referenced
            if body.media_ids:
                referenced_media = []
                for media_id in body.media_ids[:5]:  # Max 5 references
                    media_record = await get_media(media_id)
                    if media_record and media_record.person_id == user_id:
                        referenced_media.append({
                            "media_id": media_id,
                            "description": media_record.description,
                            "extracted_text": media_record.extracted_text,
                            "analysis": media_record.analysis,
                        })
                if referenced_media:
                    vision_context["referenced_media"] = referenced_media

            # Load relevant visual context from session
            if session_id:
                relevant_media = await get_relevant_media_for_context(
                    person_id=user_id,
                    session_id=str(session_id),
                    max_items=3,
                )
                if relevant_media:
                    vision_context["session_media"] = relevant_media

        except Exception as vision_exc:
            logger.warning("[turn_v2] Vision processing failed: %s", vision_exc)

    # NOTE: Agentic/web search disabled — was computed pre-LLM via keyword matching
    # but never injected into the prompt. If web search is needed in the future,
    # implement as an LLM tool call so the model decides when to search.
    agentic_context = {}
    agentic_results = []

    minimal_mode = body.capture_only  # Full ingest by default
    logger.info("[turn_v2] user_id=%s text_len=%s capture_only=%s vision=%s", user_id, len(body.text or ""), minimal_mode, bool(vision_context))

    fast_ingest = {}  # Build 50: avoid ingest work in route; delegate to workers
    observe_source = "offload" if body.source == "offload" else "conversation"
    try:
        turn_context = await orchestrate_turn(
            person_id=user_id,
            text=body.text,
            clarity_hint=body.clarity_phrase,
            capture_only=body.capture_only,
            skip_llm=True,  # Defer LLM calls (enrich, embedding, intents) to workers
            ts=body.ts,
            source=observe_source,
            client_id=body.client_id,
        )
    except Exception as orch_exc:
        logger.error("[turn_v2] orchestrate_turn failed: %s", orch_exc)
        turn_context = {"entry_id": None, "embedding": [], "topics": [], "emotion": {}, "intents": [], "plans": []}
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


    # ==========================================================
    # LINK VISION TO JOURNAL ENTRY
    # ==========================================================
    # If we processed images and have an entry_id, link them
    if entry_id and vision_context:
        try:
            # Link current image to entry
            if vision_context.get("current_image"):
                media_id = vision_context["current_image"].get("media_id")
                if media_id:
                    await link_media_to_entry(
                        media_id=media_id,
                        entry_id=str(entry_id),
                        person_id=user_id,
                        relationship="attachment",
                        caption=vision_context["current_image"].get("description"),
                    )
                    logger.info(
                        "[turn_v2] Linked media %s to entry %s",
                        media_id,
                        entry_id,
                    )

            # Link referenced media to entry
            for ref_media in vision_context.get("referenced_media", []):
                ref_media_id = ref_media.get("media_id")
                if ref_media_id:
                    await link_media_to_entry(
                        media_id=ref_media_id,
                        entry_id=str(entry_id),
                        person_id=user_id,
                        relationship="context",
                        caption=ref_media.get("description"),
                    )
        except Exception as link_exc:
            logger.warning("[turn_v2] Failed to link media to entry: %s", link_exc)

    if body.capture_only:
        ts_iso = body.ts or datetime.datetime.utcnow().isoformat()
        try:
            triage_local = extract(body.text, datetime.datetime.utcnow())
        except Exception:
            triage_local = {}

        payload = _build_capture_only_worker_payload(
            text=body.text,
            ts_iso=ts_iso,
            entry_id=str(entry_id) if entry_id else None,
            emotion=emotion,
            intents=stored_intents,
            topics=topics,
            plans=generated_plans,
            triage=triage_local if isinstance(triage_local, dict) else {},
            layer="offload" if body.source == "offload" else "conversation",
        )

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

        disable_queue = os.getenv("SAKHI_DISABLE_QUEUE") == "1"
        turn_id = str(entry_id or body.client_id or uuid4())
        if disable_queue:
            from sakhi.apps.worker.pipelines.turn_updates.runner import process_turn_job_async
            for job_type in _CAPTURE_ONLY_QUEUED_JOBS:
                try:
                    await process_turn_job_async(
                        job_type=job_type,
                        turn_id=turn_id,
                        person_id=user_id,
                        payload=payload,
                    )
                except Exception as exc:
                    logger.warning("[turn_v2:capture_only] inline job failed type=%s err=%s", job_type, exc)
        else:
            enqueue_turn_jobs(turn_id, user_id, _CAPTURE_ONLY_QUEUED_JOBS, payload)

        return {
            "reply": "",
            "entry_id": str(entry_id) if entry_id else None,
            "layer": payload["layer"],
            "queued_jobs": _CAPTURE_ONLY_QUEUED_JOBS,
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
                "jobs_enqueued": True,
                "source": observe_source,
                "note": "Capture-only turns now enqueue the standard ingestion worker set without generating a reply.",
            },
        }

    # Get brain state + internal state in parallel (independent DB reads)
    behavior_profile = {}  # Computed on-demand if needed
    planner_payload = None  # Planner runs in workers
    insight_bundle = None  # Insights generated by workers
    activation = {}  # No longer using legacy activation system
    try:
        triage_local = extract(body.text, datetime.datetime.utcnow())
    except Exception as extract_exc:
        logger.warning("[turn_v2] extract/triage failed: %s", extract_exc)
        triage_local = {}
    mood_affect = (triage_local.get("slots") or {}).get("mood_affect") if isinstance(triage_local, dict) else {}
    emotion_update = {
        "summary": (mood_affect or {}).get("label"),
        "confidence": float((mood_affect or {}).get("score") or 0.5),
    }

    # Bridge triage mood_affect into emotion when orchestrator returned "neutral"
    triage_label = (mood_affect or {}).get("label")
    if triage_label and emotion.get("emotion") == "neutral":
        emotion = {"emotion": triage_label}

    # deterministic context skipped for continuity MVP — restore when rebuilding
    # recommendations / causal / moment / body modules over the continuity foundation
    det_ctx = DeterministicContext()
    internal_state = det_ctx.internal_state

    # Build brain_state dict from det_ctx (single personal_model query, no duplicate)
    brain_state = {
        "operating_system": det_ctx.emotion_state,  # kept for compat but unused downstream
        "emotion_state": det_ctx.emotion_state,
        "soul_state": det_ctx.soul_state,
        "rhythm_state": det_ctx.rhythm_state,
        "longitudinal_state": det_ctx.longitudinal_state,
        "identity_momentum_state": det_ctx.identity_momentum_state,
        "forecast_state": det_ctx.forecast_state,
    }

    agent_task_enabled = _agent_task_execution_enabled()

    # --- Parallel fetch: pending agent task ---
    # intent evolution parked for continuity MVP (1 DB read from intent_evolution table,
    # fed combined_intents → metadata, but build_prompt() never used it). Restore when
    # rebuilding intent-driven tone/metadata shaping over the continuity foundation.
    evolution_intents: list = []
    try:
        if agent_task_enabled:
            pending_agent_task = await get_pending_agent_task(user_id)
            if isinstance(pending_agent_task, Exception):
                pending_agent_task = None
        else:
            pending_agent_task = None
    except Exception:
        pending_agent_task = None

    # Build intent hints from triage (already computed above, zero cost)
    triage_intents = map_triage_to_intents(triage_local)

    # Combine all intent sources for the prompt's enriched_context
    combined_intents = stored_intents + triage_intents + evolution_intents

    # --- MVP: continuity-only routing ---
    # All non-continuity modules parked while showcasing continuity.
    # Restore intent-based routing when building out scheduling/recommendations/causal/agent.
    active_modules: set[str] = {"continuity"}
    logger.info("[turn_v2] Continuity-only modules active (MVP), intents=%s", len(combined_intents))

    # --- Tier 1 fast compute + inner dialogue: parked for continuity MVP ---
    # Restore when building soul/alignment/rhythm features.
    fast_narrative: dict = {}
    inner_dialogue: dict = {}
    nudge_state: dict = {}

    # Fire-and-forget: personal-model side-effect writes.
    # Results are available next turn from DB; not needed for this turn's LLM
    # (continuity pack + brain_state already cover core reply context).
    _user_id_cap = user_id
    _text_cap = body.text
    async def _refresh_person_state() -> None:
        await asyncio.gather(
            compute_microreg(_user_id_cap, _text_cap),
            compute_tone(_user_id_cap),
            compute_empathy(_user_id_cap, _text_cap),
            return_exceptions=True,
        )
    asyncio.create_task(_refresh_person_state())
    microreg_state: dict = {}
    tone_state: dict = {}
    empathy_state: dict = {}

    # micro_goals + scaffolds: parked for continuity MVP
    micro_goals_meta = None
    text_lower = (body.text or "").lower()

    # --- Deterministic context extraction (loaded in parallel above) ---
    continuity_state = det_ctx.continuity_state
    focus_path = det_ctx.focus_path or {}
    mini_flow = det_ctx.mini_flow or {}
    micro_journey = det_ctx.micro_journey or {}
    gap_hours = det_ctx.gap_hours

    # Guards
    focus_path_guard = det_ctx.guards.get("focus_path", "")
    mini_flow_guard = det_ctx.guards.get("mini_flow", "")
    micro_journey_guard = det_ctx.guards.get("micro_journey", "")

    # moment_model / evidence_pack / deliberation / reflection_trace: parked for continuity MVP
    moment_model: dict = {}
    evidence_pack: dict = {}
    deliberation_scaffold = None
    reflection_trace_payload = None

    # ==========================================================================
    # Personalized Recommendations Integration
    # Surfaces recommendations based on: friction state, time of day, user request
    # ==========================================================================
    personalized_recommendations = {}
    recommendation_trigger = None  # Why recommendations are being surfaced

    # Friction state parked for continuity MVP — det_ctx is empty stub, so no real
    # friction data is available. Send empty to avoid fabricating "balanced/0%" state
    # in the prompt. Restore when rebuilding friction/body over the continuity foundation.
    friction_state_computed: dict = {}

    # ==========================================================================
    # Recommendations / causal / body / email: parked for continuity MVP
    # Re-enable when building these features over the continuity foundation.
    # ==========================================================================
    recommendation_trigger = None
    recommendation_guard = ""
    causal_explanation = None
    body_state = det_ctx.body_state_full or {}
    health_trends: dict = {}
    email_context = None
    contact_prefs_context = None

    # ==========================================================================
    # Scheduling: parked for continuity MVP
    # Re-enable when building scheduling over the continuity foundation.
    # ==========================================================================
    scheduling_context = {}
    scheduling_intent_detected = None
    relationship_nudges: list = []
    today_calendar: list = []
    week_summary: dict = {}
    scheduling_confirmation_result = None
    scheduling_guard = ""

    # scheduling logic removed — restore from git when re-enabling

    # ==========================================================================
    # Agent Task Integration
    # Detects autonomous task requests and manages the execution flow.
    # When user says "book me a table" or "find me running shoes on Amazon",
    # Sakhi creates a plan, asks for confirmation, then executes via vision loop.
    # ==========================================================================
    agent_task_context = {}
    agent_task_detected = None
    agent_task_plan = None
    agent_task_execution = None

    if agent_task_enabled:
        try:
            # 1. CHECK FOR TASK CONFIRMATION: Did user confirm/reject a pending task?
            # (pending_agent_task already fetched before router for has_pending_task signal)
            if pending_agent_task:
                confirmation = detect_task_confirmation(body.text)

                if confirmation is True:
                    # User confirmed - start real execution via desktop agent
                    confirmed_task = await confirm_task(pending_agent_task.task_id)
                    if confirmed_task:
                        execution_state = await start_task_execution(confirmed_task)
                        agent_task_execution = {
                            "task_id": confirmed_task.task_id,
                            "status": execution_state.status,
                            "current_step": execution_state.current_step + 1,
                            "total_steps": execution_state.total_steps,
                            "message": format_execution_update_for_chat(execution_state),
                            "agent_id": execution_state.agent_id,
                        }
                        agent_task_context["execution"] = agent_task_execution
                        agent_task_context["confirmed"] = True
                        logger.info(
                            "[turn_v2] Agent task confirmed and started: task_id=%s agent_id=%s",
                            confirmed_task.task_id,
                            execution_state.agent_id,
                        )

                elif confirmation is False:
                    # User rejected
                    await reject_task(pending_agent_task.task_id)
                    agent_task_context["rejected"] = True
                    agent_task_context["message"] = "No problem, I've cancelled that."
                    logger.info(
                        "[turn_v2] Agent task rejected: task_id=%s",
                        pending_agent_task.task_id,
                    )

                else:
                    # User said something else - keep the pending task in context
                    agent_task_context["pending_task"] = {
                        "task_id": pending_agent_task.task_id,
                        "task_type": pending_agent_task.task_type.value,
                        "description": pending_agent_task.task_description,
                        "awaiting_confirmation": True,
                    }

            # 2. DETECT NEW AGENT TASK: Is this a new task request?
            if not pending_agent_task or agent_task_context.get("rejected"):
                task_detection = detect_agent_task_intent(body.text)

                if task_detection:
                    task_type, matched_pattern, confidence = task_detection
                    agent_task_detected = {
                        "type": task_type.value,
                        "confidence": confidence,
                    }

                    # Generate a task plan
                    plan_result = await generate_task_plan(
                        person_id=user_id,
                        task_type=task_type,
                        task_request=body.text,
                    )

                    if plan_result.get("success"):
                        # Create pending task for confirmation
                        new_task = await create_pending_task(
                            person_id=user_id,
                            task_type=task_type,
                            original_request=body.text,
                            plan_steps=plan_result.get("steps", []),
                            context_used=plan_result.get("context", {}),
                        )

                        agent_task_plan = {
                            "task_id": new_task.task_id,
                            "task_type": task_type.value,
                            "steps": plan_result.get("steps", []),
                            "estimated_duration": plan_result.get("estimated_duration", 2),
                            "context_used": plan_result.get("context", {}),
                            "formatted_plan": format_task_plan_for_chat(
                                task_type,
                                plan_result,
                                plan_result.get("context", {}),
                            ),
                        }
                        agent_task_context["new_task"] = agent_task_plan
                        agent_task_context["awaiting_confirmation"] = True

                        logger.info(
                            "[turn_v2] Agent task detected: type=%s task_id=%s steps=%d",
                            task_type.value,
                            new_task.task_id,
                            len(plan_result.get("steps", [])),
                        )

            # 3. CHECK EXECUTION STATE: Is there a running task?
            if pending_agent_task and pending_agent_task.status == "confirmed":
                execution_state = await get_task_execution_state(pending_agent_task.task_id)
                if execution_state:
                    # Check if waiting for step approval
                    step_confirmation = detect_task_confirmation(body.text)

                    if execution_state.status == "waiting_approval" and step_confirmation is True:
                        # Approve the step and continue
                        updated_state = await approve_execution_step(pending_agent_task.task_id)
                        if updated_state:
                            execution_state = updated_state

                    agent_task_execution = {
                        "task_id": pending_agent_task.task_id,
                        "status": execution_state.status,
                        "current_step": execution_state.current_step + 1,
                        "total_steps": execution_state.total_steps,
                        "pending_approval": execution_state.pending_approval,
                        "message": format_execution_update_for_chat(execution_state),
                        "agent_id": execution_state.agent_id,
                    }
                    agent_task_context["execution"] = agent_task_execution

        except Exception as agent_exc:
            logger.warning("[turn_v2] Agent task processing failed: %s", agent_exc)
            agent_task_context = {}

    agent_task_guard = _build_agent_task_guard(agent_task_enabled)

    agentic_guard = ""  # Agentic/web search disabled — see note above

    metadata_payload = {
        "active_modules": sorted(active_modules),  # Context router — tells conversation_reasoner which tier 2 sections to build
        "entry_id": entry_id,
        "topics": topics,
        "emotion": emotion,
        "intents": combined_intents,
        "plans": generated_plans,
        "rhythm_triggers": rhythm_trigger_result,
        "meta_reflection_triggers": meta_reflection_result,
        "behavior_profile": behavior_profile,
        "activation": activation,
        "triage": triage_local,
        "emotion_update": emotion_update,
        "internal_state": internal_state,
        "cognitive_load": internal_state.get("cognitive_load"),
        "priority": internal_state.get("priority"),
        "priority_topics": internal_state.get("priority_topics"),
        "soul_values": internal_state.get("soul_values"),
        "soul_identity": internal_state.get("soul_identity"),
        "life_themes": internal_state.get("life_themes"),
        "identity_graph": internal_state.get("identity_graph"),
        # Friction Framework context
        "operating_system": internal_state.get("operating_system"),
        "dosha_baseline": internal_state.get("dosha_baseline"),
        "life_context": internal_state.get("life_context"),
        "decision_profile": internal_state.get("decision_profile"),
        "narrative_trace": fast_narrative,
        "inner_dialogue": inner_dialogue,
        "tone_state": tone_state,
        "nudge_state": nudge_state,
        "empathy_state": empathy_state,
        "continuity": continuity_state,
        "micro_goals": micro_goals_meta,
        "microreg_state": microreg_state,
        "focus_path": focus_path,
        "focus_path_guard": focus_path_guard,
        "mini_flow": mini_flow,
        "mini_flow_guard": mini_flow_guard,
        "micro_journey": micro_journey,
        "micro_journey_guard": micro_journey_guard,
        "moment_model": moment_model,
        "evidence_pack": evidence_pack,
        "deliberation_scaffold": deliberation_scaffold,
        # Personalized Recommendations (Ayurvedic + personal patterns)
        "friction_state": friction_state_computed,
        "personalized_recommendations": personalized_recommendations,
        "recommendation_trigger": recommendation_trigger,
        "recommendation_guard": recommendation_guard,
        # Scheduling & Calendar Context
        "scheduling_context": scheduling_context,
        "scheduling_intent": scheduling_intent_detected.value if hasattr(scheduling_intent_detected, 'value') else scheduling_intent_detected,
        "relationship_nudges": relationship_nudges,
        "scheduling_guard": scheduling_guard,
        # Sakhi Mesh coordination context
        "mesh_coordination": scheduling_context.get("mesh_coordination") if scheduling_context else None,
        # Vision context (images, documents in conversation)
        "vision_context": vision_context if vision_context else None,
        # Agentic context (web search results, tool outputs)
        "agentic_context": agentic_context if agentic_context else None,
        "agentic_results": agentic_results if agentic_results else None,
        "agentic_guard": agentic_guard,
        # Agent Task context (autonomous task execution)
        "agent_task_context": agent_task_context if agent_task_context else None,
        "agent_task_detected": agent_task_detected,
        "agent_task_plan": agent_task_plan,
        "agent_task_execution": agent_task_execution,
        "agent_task_guard": agent_task_guard,
        # Conversation history for LLM context continuity
        "conversation_history": conversation_history,
        "session_summary": session_summary,  # Compressed older context
        "total_turns": total_turns,
        # Email & Signal Context (reactive only — injected when user asks about email)
        "email_context": email_context,
        "causal_explanation": causal_explanation,
        "contact_preferences": contact_prefs_context,
        # Body & Health Context (longitudinal — always in scan, deep when body module active)
        "body_state": body_state,
        "health_trends": health_trends,
    }

    try:
        continuity_pack = await build_continuity_pack(
            user_id,
            body.text,
        )
        if continuity_pack:
            metadata_payload["continuity_pack"] = continuity_pack
    except Exception as continuity_exc:
        logger.warning("[turn_v2] Continuity pack build failed (non-fatal): %s", continuity_exc)

    # ── GOVERNANCE GATE: parked for continuity MVP ───────────────────────
    # Loads constraints + objectives + 14-day event ledger (3 DB reads) then
    # runs Kala gate.evaluate(). For the MVP showcase the user has no constraints
    # set up so every turn returns action="allow" and governance_guard="".
    # Restore when onboarding surfaces constraint/objective setup.
    governance_decision = None
    governance_guard = ""

    # background task routing refresh when new task intent might be present
    try:
        if stored_intents:
            from sakhi.apps.worker.tasks.task_routing_worker import enqueue_task_routing
            enqueue_task_routing(user_id)
    except Exception:
        pass

    try:
        _return_debug = (
            os.getenv("SAKHI_DEBUG_RESPONSE", "0") == "1"
            or request.query_params.get("debug") == "1"
        )
        reply_bundle = await generate_reply(
            person_id=user_id,
            user_text=body.text,
            metadata=metadata_payload,
            behavior_profile=behavior_profile,
            session_id=str(session_id) if session_id else "",
            return_debug=_return_debug,
        )
    except Exception as reply_exc:
        logger.error("[turn_v2] CRITICAL - generate_reply failed for user=%s: %s", user_id, reply_exc, exc_info=True)
        reply_bundle = {"reply": "I'm here. Could you say that again?", "tone_blueprint": {}, "journaling_ai": None}

    reply_text = reply_bundle.get("reply", "")
    tone_blueprint = reply_bundle.get("tone_blueprint") or {}
    journaling_ai = reply_bundle.get("journaling_ai")
    adaptive_response = reply_bundle.get("adaptive_response")  # Adaptive Response Framework output
    reply_debug = reply_bundle.get("debug") or {}  # Full debug from conversation engine

    # ── GOVERNANCE POST-CHECK ────────────────────────────────────────────
    # If governance blocked but LLM still violated, replace with safe template.
    if governance_decision and governance_decision.get("action") == "block":
        try:
            from sakhi.apps.api.services.governance.service import enforce_block
            reply_text = enforce_block(reply_text, governance_decision)
        except Exception:
            pass  # Non-fatal — let original reply through

    # ── GOVERNANCE EVENT LOG (post-reply) ────────────────────────────────
    try:
        from sakhi.apps.api.services.governance.service import (
            log_turn_event,
            map_decision_to_event_type,
        )
        gov_action = (governance_decision or {}).get("action", "allow")
        await log_turn_event(
            person_id=user_id,
            action=action_type,
            event_type=map_decision_to_event_type(gov_action),
            actor="llm",
            data={
                "governance_action": gov_action,
                "had_violations": bool(
                    governance_decision and governance_decision.get("violations")
                ),
            },
            reason=reply_text[:200],
        )
    except Exception:
        pass  # Non-fatal

    # ── OPTIMIZATION: Return response immediately, process rest in background ──
    product = {
        "reply": reply_text,
        "sessionId": str(session_id) if session_id else user_id,
        "tone": tone_blueprint.get("style") or "auto",
        "toneBlueprint": tone_blueprint,
        "tone_blueprint": tone_blueprint,
        "entry_id": entry_id,
        "friction_state": friction_state_computed,
        "personalized_recommendations": personalized_recommendations,
        "adaptive_response": adaptive_response,
        "journaling_ai": journaling_ai,
        "memory_recall": [],  # Recall already done inside generate_reply
        "agent_task_context": agent_task_context if agent_task_context else None,
        "governance": governance_decision,
    }

    if _return_debug:
        product["debug_data"] = {
            "active_modules": sorted(active_modules),
            "orchestration": orchestration_snapshot,
            "conversation_engine_debug": reply_debug,
            "entry_id": entry_id,
            "topics": topics,
            "emotion": emotion,
            "intents_detected": stored_intents,
            "friction_state": friction_state_computed,
            "continuity_pack": metadata_payload.get("continuity_pack"),
            "internal_state": internal_state,
            "tone_state": tone_state,
            "empathy_state": empathy_state,
            "governance_decision": governance_decision,
            "governance_guard": governance_guard,
            "note": "Post-reply processing (memory, persona, topics, workers) runs in background",
        }

    product["continuity"] = _build_public_continuity_signal(
        metadata_payload.get("continuity_pack"),
    )

    # Fire-and-forget: all post-reply processing in background
    asyncio.create_task(_run_post_reply_processing(
        user_id=user_id,
        text=body.text,
        source=body.source,
        clarity_phrase=body.clarity_phrase,
        session_id=session_id,
        entry_id=entry_id,
        reply_text=reply_text,
        tone_blueprint=tone_blueprint,
        minimal_mode=minimal_mode,
        behavior_profile=behavior_profile,
        emotion=emotion,
        tone_state=tone_state,
        empathy_state=empathy_state,
        microreg_state=microreg_state,
        brain_state=brain_state,
        stored_intents=stored_intents,
        topics=topics,
        generated_plans=generated_plans,
        turn_context=turn_context,
        emotion_update=emotion_update,
        experience_ts=body.ts,
        turn_id=turn_id,
        t_start=t_start,
        has_continuity=bool(product.get("continuity")),
    ))

    logger.info(
        "[turn_v2] response returned entry_id=%s session_id=%s (post-reply in background)",
        entry_id, session_id,
    )
    return product
