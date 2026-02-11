from __future__ import annotations

import json
import os
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
    load_deterministic_context,
    load_internal_state,
    calculate_gap_hours,
)
from sakhi.apps.api.services.turn.reply_service import build_turn_reply
from sakhi.apps.api.services.turn.async_triggers import enqueue_turn_jobs
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
from sakhi.apps.api.utils.person_resolver import resolve_person
from sakhi.apps.api.ingest.extractor import extract
from sakhi.apps.api.services.emotion_engine import compute as compute_emotion_state
from sakhi.apps.api.services.mind_engine import compute as compute_mind_state
from sakhi.apps.api.services.ayurveda.vikriti import (
    compute_current_vikriti,
    compute_baseline_drift,
    classify_friction_state,
)
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
from sakhi.apps.api.services.context_router import route_context
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
from sakhi.apps.api.services.agentic.search import (
    web_search,
    summarize_search_results,
)
from sakhi.apps.api.services.agentic.tools import (
    get_available_tools,
    execute_tool,
    can_auto_execute,
)
from sakhi.apps.api.services.memory.sessions import (
    ensure_session,
    append_turn,
    load_recent_turns,
    load_context_with_summary,
    compress_older_turns_to_summary,
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
    source: str = "text"  # "text" or "voice"
    # Vision support
    image_data: str | None = None  # Base64 encoded image
    image_mime_type: str | None = None  # e.g., "image/png"
    media_ids: list[str] | None = None  # Previously uploaded media IDs


# NOTE: _load_internal_state now uses the shared deterministic_context_loader module.
# This ensures consistency between /v2/turn and /lab/live-turn endpoints.
# See: sakhi/apps/api/services/turn/deterministic_context_loader.py
async def _load_internal_state(person_id: str) -> Dict[str, Any]:
    """Load internal state using the shared deterministic context loader."""
    return await load_internal_state(person_id)


def _ensure_dict(value: Any) -> Dict[str, Any]:
    """Safely ensure a value is a dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            import json
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


async def _get_brain_state_from_personal_model(person_id: str) -> Dict[str, Any]:
    """
    Get brain state directly from personal_model (replaces legacy brain_engine).
    Returns the key state fields used for context in turn processing.
    """
    row = await q(
        """
        SELECT operating_system, emotion_state, soul_state, rhythm_state,
               longitudinal_state, identity_momentum_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if not row:
        return {}
    return {
        "operating_system": _ensure_dict(row.get("operating_system")),
        "emotion_state": _ensure_dict(row.get("emotion_state")),
        "soul_state": _ensure_dict(row.get("soul_state")),
        "rhythm_state": _ensure_dict(row.get("rhythm_state")),
        "longitudinal_state": _ensure_dict(row.get("longitudinal_state")),
        "identity_momentum_state": _ensure_dict(row.get("identity_momentum_state")),
    }


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


@router.post("/turn")
async def turn_v2(body: TurnIn, request: Request, user: str | None = Query(default=None)):
    user_id, person_label, person_key = resolve_person(request, user)
    logger.error("[turn_v2] entry start user=%s person_id=%s label=%s", user, user_id, person_label)
    logger.info("ACTIVE_DEV_PERSON", extra={"person_id": user_id, "person_label": person_label, "person_key": person_key})

    if not body.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty text")

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

            # Trigger compression if we have many turns and no summary yet
            if total_turns >= compress_threshold and not session_summary:
                try:
                    await compress_older_turns_to_summary(str(session_id), keep_recent=recent_limit)
                    context_data = await load_context_with_summary(str(session_id), recent_limit=recent_limit)
                    session_summary = context_data.get("session_summary", "")
                except Exception as comp_exc:
                    logger.warning("[turn_v2] Failed to compress older turns: %s", comp_exc)
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

    # ==========================================================
    # AGENTIC CONTEXT: Detect and execute tools when needed
    # ==========================================================
    # Sakhi can automatically search the web, fetch URLs, or use tools
    # when the user asks questions that need external information.
    agentic_context = {}
    agentic_results = []

    try:
        text_lower = (body.text or "").lower()

        # Detect if the query needs external information
        search_triggers = [
            "search for", "find out", "look up", "google",
            "what is the latest", "what's new", "current",
            "news about", "latest on", "tell me about",
            "who is", "what happened", "recent",
            "how do i", "how to", "what are the best",
        ]
        question_patterns = [
            "what is", "what are", "who is", "when is",
            "where is", "how much", "how many",
        ]

        needs_search = any(trigger in text_lower for trigger in search_triggers)
        is_factual_question = any(p in text_lower for p in question_patterns)

        # Only auto-search for queries that clearly need external info
        # and aren't about the user's personal life
        personal_indicators = [
            "i feel", "i'm feeling", "i want", "i need", "my ",
            "i've been", "i have", "i am", "i think", "i believe",
        ]
        is_personal = any(p in text_lower for p in personal_indicators)

        if needs_search and not is_personal:
            # Execute web search
            try:
                search_results = await web_search(
                    query=body.text,
                    max_results=5,
                )

                if search_results:
                    # Summarize results for context
                    summary = await summarize_search_results(
                        results=search_results,
                        query=body.text,
                    )

                    agentic_context["web_search"] = {
                        "query": body.text,
                        "result_count": len(search_results),
                        "summary": summary,
                        "sources": [
                            {
                                "title": r.get("title"),
                                "url": r.get("url"),
                                "snippet": r.get("snippet", "")[:200],
                            }
                            for r in search_results[:3]
                        ],
                    }
                    agentic_results.append({
                        "tool": "web_search",
                        "success": True,
                        "summary": summary,
                    })
                    logger.info(
                        "[turn_v2] Agentic: web search executed for '%s' - %d results",
                        body.text[:50],
                        len(search_results),
                    )
            except Exception as search_exc:
                logger.warning("[turn_v2] Web search failed: %s", search_exc)
                agentic_context["web_search_error"] = str(search_exc)

        # Store available tools info for context
        try:
            available_tools = await get_available_tools(user_id)
            agentic_context["available_tools"] = [
                {
                    "name": t.tool_name,
                    "description": t.description,
                    "category": t.category,
                }
                for t in available_tools[:5]  # Limit to top 5
            ]
        except Exception:
            pass

    except Exception as agentic_exc:
        logger.warning("[turn_v2] Agentic context failed: %s", agentic_exc)

    minimal_mode = body.capture_only  # Full ingest by default
    logger.info("[turn_v2] user_id=%s text_len=%s capture_only=%s vision=%s agentic=%s", user_id, len(body.text or ""), minimal_mode, bool(vision_context), bool(agentic_context))

    fast_ingest = {}  # Build 50: avoid ingest work in route; delegate to workers
    try:
        turn_context = await orchestrate_turn(
            person_id=user_id,
            text=body.text,
            clarity_hint=body.clarity_phrase,
            capture_only=body.capture_only,
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
                "note": "Embedding is done once on write via background task/worker.",
            },
        }

    # Get brain state directly from personal_model (replaces legacy harmony orchestrator)
    try:
        brain_state = await _get_brain_state_from_personal_model(user_id)
    except Exception as bs_exc:
        logger.warning("[turn_v2] brain_state load failed: %s", bs_exc)
        brain_state = {}
    behavior_profile = {}  # Computed on-demand if needed
    planner_payload = None  # Planner runs in workers
    insight_bundle = None  # Insights generated by workers
    activation = {}  # No longer using legacy activation system
    triage = {}  # No longer using legacy triage
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

    try:
        internal_state = await _load_internal_state(user_id)
    except Exception as is_exc:
        logger.warning("[turn_v2] internal_state load failed: %s", is_exc)
        internal_state = {}

    # --- Context Router: determine which modules to activate ---
    try:
        active_modules = await route_context(
            text=body.text,
            intents=stored_intents,
            topics=topics,
            emotion=(emotion or {}).get("label", "neutral") if isinstance(emotion, dict) else str(emotion or "neutral"),
            hour=datetime.datetime.utcnow().hour,
            has_image=bool(getattr(body, "image_data", None) or getattr(body, "media_ids", None)),
            has_pending_task=bool(pending_agent_task) if "pending_agent_task" in locals() else False,
        )
    except Exception as rc_exc:
        logger.warning("[turn_v2] Context router failed: %s", rc_exc)
        active_modules = set()
    logger.info("[turn_v2] Context router: active_modules=%s", active_modules)

    # --- Tier 1: Always-compute (cheap, feeds 360° context scan) ---
    fast_narrative = compute_fast_narrative([], brain_state.get("soul_state") or {})
    alignment = compute_alignment(
        None,
        brain_state.get("soul_state") or {},
        brain_state.get("goals_state") or {},
    )
    fast_rhythm_soul = compute_fast_rhythm_soul_frame(
        [],
        brain_state.get("rhythm_state") or {},
        brain_state.get("soul_state") or {},
    )
    fast_esr = compute_fast_esr_frame(
        brain_state.get("emotion_state") or {},
        brain_state.get("soul_state") or {},
        brain_state.get("rhythm_state") or {},
    )
    fast_identity_momentum = compute_fast_identity_momentum(
        [],
        brain_state.get("soul_state") or {},
        brain_state.get("emotion_state") or {},
        brain_state.get("rhythm_state") or {},
    )
    fast_identity_timeline = compute_fast_identity_timeline_frame(
        [],
        brain_state.get("soul_state") or {},
        brain_state.get("emotion_state") or {},
        brain_state.get("rhythm_state") or {},
        brain_state.get("identity_momentum_state") or {},
    )
    # --- Tier 2 gating: emotional_depth (inner_dialogue + nudge_state are LLM/DB calls) ---
    if "emotional_depth" in active_modules:
        try:
            inner_dialogue = await inner_dialogue_engine.compute_inner_dialogue(
                user_id, body.text, {"triage": triage_local, "behavior_profile": behavior_profile}
            )
        except Exception:
            inner_dialogue = {}
        try:
            nudge_row = await q("SELECT nudge_state FROM personal_model WHERE person_id = $1", user_id, one=True) or {}
            nudge_state = nudge_row.get("nudge_state") or {}
        except Exception:
            nudge_state = {}
    else:
        inner_dialogue = {}
        nudge_state = {}

    # Always compute — DB side effects (writes to personal_model)
    try:
        microreg_state = await compute_microreg(user_id, body.text)
    except Exception:
        microreg_state = {}
    try:
        tone_state = await compute_tone(user_id)
    except Exception:
        tone_state = {}
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
        if trigger_focus and "micro_flow" in active_modules:
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
        if flow_trigger and "micro_flow" in active_modules:
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
            emotion_state=brain_state.get("emotion_state") or {},
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
    # --- Tier 2 gating: moment (evidence_pack + deliberation are expensive) ---
    if "moment" in active_modules:
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
        # Reflection trace (has DB side effects — only when evidence_pack computed)
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
    else:
        evidence_pack = {}
        deliberation_scaffold = None
        reflection_trace_payload = None

    # ==========================================================================
    # Personalized Recommendations Integration
    # Surfaces recommendations based on: friction state, time of day, user request
    # ==========================================================================
    friction_state_computed = {}
    personalized_recommendations = {}
    recommendation_trigger = None  # Why recommendations are being surfaced
    drift_percentage = 0

    try:
        # Build prakruti dict from internal_state for drift computation
        # operating_system is a string (e.g. "Conservation"), dosha_baseline is the actual values
        prakruti = {"dosha_baseline": internal_state.get("dosha_baseline") or {}}

        # Compute current vikriti (present state deviation)
        vikriti = await compute_current_vikriti(user_id)

        # Compute drift from baseline (Prakruti)
        drift = compute_baseline_drift(prakruti, vikriti)
        drift_percentage = drift.get("drift_percentage", 0)

        # Classify the friction state
        friction = classify_friction_state(drift)
        friction_state_computed = {
            "state": friction.get("state", "Balanced"),
            "description": friction.get("description"),
            "drift_percentage": drift_percentage,
            "drift_direction": drift.get("direction"),
            "primary_contributor": drift.get("primary_contributor"),
        }

        # Determine if recommendations should be proactively surfaced
        # Triggers:
        # 1. REACTIVE: User explicitly asks (detected via patterns)
        # 2. PROACTIVE: High friction drift (>25%)
        # 3. CONTEXTUAL: Morning (before 10am) or evening (after 7pm)
        # 4. NUDGE: Moderate drift (15-25%) with relevant patterns

        text_lower = (body.text or "").lower()
        recommendation_patterns = [
            "what should i", "recommend", "suggestion", "help me",
            "what can i do", "how can i", "what would help",
            "feeling off", "out of balance", "what do you suggest",
        ]
        is_reactive_request = any(p in text_lower for p in recommendation_patterns)

        current_hour = datetime.datetime.utcnow().hour
        is_morning = current_hour < 10
        is_evening = current_hour >= 19

        # Determine trigger reason
        if is_reactive_request:
            recommendation_trigger = "reactive"  # User asked
        elif drift_percentage > 25:
            recommendation_trigger = "proactive"  # High friction
        elif is_morning or is_evening:
            recommendation_trigger = "contextual"  # Scheduled moment
        elif 15 <= drift_percentage <= 25:
            recommendation_trigger = "nudge"  # Gentle suggestion

        # When body module is active (user mentions symptoms), ensure recommendations can flow
        if "body" in active_modules and not recommendation_trigger:
            recommendation_trigger = "reactive"

        # Generate recommendations if triggered AND router allows (or high drift/body overrides)
        if recommendation_trigger and ("recommendations" in active_modules or drift_percentage > 25 or "body" in active_modules):
            try:
                rec_context = await build_recommendation_context(user_id)
                recs = await generate_personalized_recommendations(
                    context=rec_context,
                    max_foods=3,
                    max_practices=3,
                )
                personalized_recommendations = {
                    "friction_state": recs.friction_state,
                    "urgency_level": recs.urgency_level,
                    "personalization_confidence": recs.personalization_confidence,
                    "why_this_state": recs.why_this_state,
                    "personal_insight": recs.personal_insight,
                    "immediate_actions": [r.model_dump() for r in recs.immediate_actions[:2]],
                    "foods": [r.model_dump() for r in recs.foods[:3]],
                    "practices": [r.model_dump() for r in recs.practices[:2]],
                    "watch_for": recs.watch_for,
                    "trigger": recommendation_trigger,
                    "trigger_reason": {
                        "reactive": "You asked for suggestions",
                        "proactive": f"Your friction drift is {drift_percentage:.0f}% - let me suggest some rebalancing",
                        "contextual": "Morning check-in" if is_morning else "Evening wind-down time",
                        "nudge": "A gentle suggestion based on your patterns",
                    }.get(recommendation_trigger),
                }
                logger.info(
                    "[turn_v2] Recommendations surfaced: trigger=%s drift=%.1f%%",
                    recommendation_trigger,
                    drift_percentage,
                )
            except Exception as rec_exc:
                logger.warning("[turn_v2] Recommendation generation failed: %s", rec_exc)
                personalized_recommendations = {}
    except Exception as friction_exc:
        logger.warning("[turn_v2] Friction state computation failed: %s", friction_exc)
        friction_state_computed = {}

    recommendation_guard = (
        "Recommendations are personalized based on Ayurvedic principles and personal patterns. "
        "Surface them naturally when relevant. For proactive triggers, weave them in gently. "
        "For reactive requests, be direct and helpful. Never force recommendations."
    )

    # ==========================================================================
    # Email & Signal Context Integration (OpenClaw approach — reactive only)
    # Email friction feeds internal state silently; email context only surfaces
    # when the user asks about email/inbox.
    # ==========================================================================

    # 1. Merge email friction into friction state (silent — enriches recommendations)
    try:
        email_friction = await get_email_friction_contribution(user_id)
        if email_friction and friction_state_computed:
            friction_state_computed["email_contribution"] = email_friction
    except Exception:
        pass

    # --- Tier 2 gating: causal reasoning (LLM call) ---
    causal_explanation = None
    has_friction_drift = drift_percentage > 15 and friction_state_computed.get("state", "Balanced") != "Balanced"
    if "causal" in active_modules or "body" in active_modules or has_friction_drift:
        try:
            if has_friction_drift:
                explanation = await explain_friction(
                    person_id=user_id,
                    friction_state=friction_state_computed.get("state", ""),
                )
                causal_explanation = {
                    "symptom": explanation.symptom,
                    "dosha_context": explanation.dosha_context,
                    "primary_causes": [c.model_dump() for c in explanation.primary_causes[:2]],
                    "contributing_factors": [c.model_dump() for c in explanation.contributing_factors[:2]],
                    "seasonal_influence": explanation.seasonal_influence,
                    "explanation_text": explanation.explanation_text,
                }
            elif "body" in active_modules:
                # Body module active but no friction drift — use symptom-based causal reasoning
                from sakhi.apps.api.services.ayurveda.causal_reasoning import (
                    map_symptom_to_dosha,
                    explain_symptom,
                )
                _symptom_keys = [
                    "headache", "migraine", "dizzy", "fever", "nausea", "pain",
                    "fatigue", "insomnia", "burning", "throbbing", "stiff",
                    "cramp", "ache", "exhausted", "tired", "anxiety", "restless",
                ]
                user_text_lower = (body.text or "").lower()
                matched_symptom = None
                for sk in _symptom_keys:
                    if sk in user_text_lower:
                        matched_symptom = sk
                        break
                if matched_symptom:
                    explanation = await explain_symptom(
                        person_id=user_id,
                        symptom=matched_symptom,
                    )
                    causal_explanation = {
                        "symptom": explanation.symptom,
                        "dosha_context": explanation.dosha_context,
                        "primary_causes": [c.model_dump() for c in explanation.primary_causes[:2]],
                        "contributing_factors": [c.model_dump() for c in explanation.contributing_factors[:2]],
                        "seasonal_influence": explanation.seasonal_influence,
                        "explanation_text": explanation.explanation_text,
                    }
        except Exception as causal_exc:
            logger.warning("[turn_v2] Causal reasoning failed: %s", causal_exc)

    # --- Always compute: body_state (cheap DB read from personal_model) ---
    body_state = {}
    try:
        from sakhi.apps.api.services.body.state_engine import get_body_state
        body_state = await get_body_state(user_id)
    except Exception:
        pass

    # --- Tier 2 gating: health trends (only when body module active) ---
    health_trends = {}
    if "body" in active_modules:
        try:
            from sakhi.apps.api.services.body.health_trends import compute_health_trends
            health_trends = await compute_health_trends(user_id, window_days=14)
        except Exception:
            pass

    # --- Tier 2 gating: email context (DB reads) ---
    email_context = None
    contact_prefs_context = None
    if "email" in active_modules:
        try:
            email_context = await get_email_context_for_conversation(
                user_id, include_details=True,
            )
        except Exception:
            pass
        try:
            prefs = await get_contact_preferences(user_id)
            if prefs:
                contact_prefs_context = format_preferences_for_llm(prefs)
        except Exception:
            pass

    # ==========================================================================
    # Scheduling Integration (gated by router)
    # Surfaces scheduling suggestions based on: explicit requests, journal hints,
    # relationship nudges, and calendar queries. User ALWAYS confirms before action.
    # ==========================================================================
    scheduling_context = {}
    scheduling_intent_detected = None
    relationship_nudges = []
    today_calendar = []
    week_summary = {}
    scheduling_confirmation_result = None  # Set if user confirmed a pending request

    try:
        if "scheduling" not in active_modules:
            raise _SkipModule("scheduling")
        text_lower = (body.text or "").lower()

        # 0. CHECK FOR CONFIRMATION: Did user confirm a pending scheduling request?
        confirmation_check = detect_confirmation(body.text)
        if confirmation_check:
            is_confirmation, option_number = confirmation_check
            pending_request = await get_pending_request(user_id)

            if pending_request:
                # User is confirming a pending scheduling request
                confirmation_result = await execute_pending_confirmation(
                    person_id=user_id,
                    request_id=str(pending_request["id"]),
                    option_number=option_number or 1,
                )
                scheduling_confirmation_result = confirmation_result
                scheduling_context["confirmation"] = {
                    "status": confirmation_result.status,
                    "message": confirmation_result.message,
                    "created_event": confirmation_result.created_event,
                }
                scheduling_intent_detected = "confirmed"
                logger.info(
                    "[turn_v2] Scheduling confirmation executed: status=%s",
                    confirmation_result.status,
                )

        # 1. EXPLICIT SCHEDULING: Detect scheduling intent in user message
        if not scheduling_confirmation_result:
            scheduling_intent_detected = detect_scheduling_intent(body.text)

        if (
            scheduling_intent_detected
            and scheduling_intent_detected != SchedulingIntent.QUERY
            and scheduling_intent_detected != "confirmed"
            and not scheduling_confirmation_result
        ):
            # Parse the scheduling request for details
            parsed_request = await parse_scheduling_request(user_id, body.text, scheduling_intent_detected)
            scheduling_context["intent"] = scheduling_intent_detected.value
            scheduling_context["parsed_request"] = {
                "event_type": parsed_request.event_type,
                "participants": parsed_request.participants,
                "timeframe": parsed_request.timeframe,
                "duration_minutes": parsed_request.duration_minutes,
                "location_hint": parsed_request.location_hint,
                "missing_slots": parsed_request.missing_slots,
            }

            # Find best times for the request
            if parsed_request.participants:
                # Look up relationship for participant context
                for participant in parsed_request.participants[:2]:  # Limit to 2
                    relationship = await get_relationship_for_scheduling(user_id, participant)
                    if relationship:
                        # usual_activities comes as JSON from the query
                        usual_activities = relationship.get("usual_activities") or []
                        if isinstance(usual_activities, str):
                            import json as json_mod
                            try:
                                usual_activities = json_mod.loads(usual_activities)
                            except Exception:
                                usual_activities = []
                        scheduling_context.setdefault("participant_context", []).append({
                            "name": participant,
                            "last_seen": str(relationship.get("last_seen_at")) if relationship.get("last_seen_at") else None,
                            "relationship_type": relationship.get("relationship_type"),
                            "usual_activities": usual_activities if isinstance(usual_activities, list) else [],
                        })

                    # ==========================================================
                    # SAKHI MESH CHECK: Does participant have Sakhi?
                    # ==========================================================
                    # Check if participant has a Sakhi profile (Sakhi-to-Sakhi coordination)
                    try:
                        # Try to find participant's Sakhi profile by name or handle
                        participant_handle = participant.lower().replace(" ", "_")
                        mesh_profile = await find_by_handle(participant_handle)

                        if mesh_profile:
                            # They have Sakhi! Check if connected
                            mesh_connected = await are_connected(user_id, mesh_profile.person_id)

                            if mesh_connected:
                                # Full Sakhi-to-Sakhi coordination available
                                trust = await get_trust_level(user_id, mesh_profile.person_id)
                                scheduling_context.setdefault("mesh_coordination", {})
                                scheduling_context["mesh_coordination"][participant] = {
                                    "has_sakhi": True,
                                    "connected": True,
                                    "trust_level": trust.value if trust else "friend",
                                    "sakhi_handle": mesh_profile.sakhi_handle,
                                    "shares_availability": mesh_profile.share_availability,
                                    "can_auto_coordinate": True,
                                    "message": f"@{mesh_profile.sakhi_handle} is on Sakhi! I can coordinate directly with their Sakhi.",
                                }
                                logger.info(
                                    "[turn_v2] Sakhi mesh detected: participant=%s handle=%s trust=%s",
                                    participant,
                                    mesh_profile.sakhi_handle,
                                    trust.value if trust else "friend",
                                )
                            else:
                                # Has Sakhi but not connected - suggest connecting
                                scheduling_context.setdefault("mesh_coordination", {})
                                scheduling_context["mesh_coordination"][participant] = {
                                    "has_sakhi": True,
                                    "connected": False,
                                    "can_auto_coordinate": False,
                                    "sakhi_handle": mesh_profile.sakhi_handle,
                                    "message": f"@{mesh_profile.sakhi_handle} is on Sakhi but you're not connected yet. Would you like to send a connection request?",
                                }
                    except Exception as mesh_exc:
                        logger.debug("[turn_v2] Mesh check failed for %s: %s", participant, mesh_exc)

            # Get availability suggestions
            try:
                best_times = await find_best_times(
                    person_id=user_id,
                    event_type=parsed_request.event_type or "meeting",
                    duration_minutes=parsed_request.duration_minutes or 60,
                    days_ahead=7,
                    max_suggestions=3,
                )
                scheduling_context["suggested_times"] = [
                    {
                        "start": str(t.get("start")),
                        "end": str(t.get("end")),
                        "quality": t.get("quality"),
                        "quality_reason": t.get("quality_reason"),
                    }
                    for t in best_times[:3]
                ]

                # Save pending request so we can confirm on next turn
                if best_times:
                    try:
                        pending_id = await save_pending_request(
                            person_id=user_id,
                            original_request=body.text,
                            parsed=parsed_request,
                            proposed_times=best_times[:3],
                        )
                        scheduling_context["pending_request_id"] = pending_id
                        logger.info("[turn_v2] Saved pending scheduling request: %s", pending_id)
                    except Exception as save_exc:
                        logger.warning("[turn_v2] Failed to save pending request: %s", save_exc)

            except Exception as avail_exc:
                logger.warning("[turn_v2] Availability lookup failed: %s", avail_exc)

        # 2. CALENDAR QUERY: "What's my week look like?"
        elif scheduling_intent_detected == SchedulingIntent.QUERY:
            scheduling_context["intent"] = "query"
            try:
                week_summary = await get_week_summary(user_id)
                scheduling_context["week_summary"] = week_summary
            except Exception:
                pass
            try:
                today_calendar = await get_events_for_day(user_id)
                scheduling_context["today_events"] = [
                    {
                        "title": e.title,
                        "start": str(e.start_time),
                        "end": str(e.end_time),
                        "event_type": e.event_type,
                        "relationship_note": e.relationship_note,
                    }
                    for e in today_calendar[:5]
                ]
            except Exception:
                pass

        # 3. PROACTIVE JOURNAL HINTS: Detect scheduling-related wishes in journal
        journal_scheduling_patterns = [
            "should visit", "should see", "need to catch up with",
            "want to meet", "thinking about visiting", "miss seeing",
            "haven't seen", "been a while since", "should call",
        ]
        detected_hints = [p for p in journal_scheduling_patterns if p in text_lower]
        if detected_hints and not scheduling_intent_detected:
            scheduling_context["journal_hint"] = {
                "detected_patterns": detected_hints,
                "suggestion_type": "proactive",
            }
            scheduling_intent_detected = "journal_hint"

        # 4. RELATIONSHIP NUDGES: People you haven't connected with recently
        # Only surface if no explicit scheduling intent (don't overwhelm)
        if not scheduling_context.get("intent"):
            try:
                nudge_relationships = await get_relationships_needing_attention(
                    user_id, limit=2
                )
                if nudge_relationships:
                    relationship_nudges = [
                        {
                            "name": r.get("name"),
                            "last_seen": str(r.get("last_seen_at")) if r.get("last_seen_at") else None,
                            "days_since": r.get("days_since_contact"),
                            "relationship_type": r.get("relationship_type"),
                            "frequency_target": r.get("frequency_target"),
                        }
                        for r in nudge_relationships
                    ]
                    scheduling_context["relationship_nudges"] = relationship_nudges
            except Exception as nudge_exc:
                logger.warning("[turn_v2] Relationship nudge lookup failed: %s", nudge_exc)

        if scheduling_context:
            logger.info(
                "[turn_v2] Scheduling context loaded: intent=%s nudges=%d",
                scheduling_intent_detected,
                len(relationship_nudges),
            )

    except _SkipModule:
        pass  # Router skipped this module
    except Exception as sched_exc:
        logger.warning("[turn_v2] Scheduling context loading failed: %s", sched_exc)
        scheduling_context = {}

    scheduling_guard = (
        "CRITICAL: User is the FINAL decision maker for all scheduling. "
        "Sakhi SUGGESTS and OFFERS options, never acts without explicit confirmation. "
        "For explicit scheduling requests: present 2-3 time options with quality context, "
        "then ask 'Would you like me to block one of these?' "
        "For journal hints: gently offer 'Would you like me to help schedule that?' "
        "For relationship nudges: only mention if natural, e.g., 'By the way, you mentioned wanting to see Alex...' "
        "For calendar queries: summarize with relationship/energy context. "
        "SAKHI MESH: If mesh_coordination shows has_sakhi=True and connected=True, mention "
        "'Their Sakhi can help find times that work for both of you' and offer to coordinate. "
        "If has_sakhi=True but connected=False, suggest 'They're on Sakhi - connect to coordinate easier.' "
        "NEVER create calendar events without explicit 'yes' or 'confirm' from user."
    )

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

    try:
        text_lower = (body.text or "").lower()

        # 1. CHECK FOR TASK CONFIRMATION: Did user confirm/reject a pending task?
        pending_agent_task = await get_pending_agent_task(user_id)

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

    agent_task_guard = (
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

    agentic_guard = (
        "When agentic_context contains web_search results: "
        "1. Use the search summary to inform your response naturally - don't just list sources. "
        "2. Cite specific facts from the search when relevant. "
        "3. If asked, mention you searched the web for current information. "
        "4. For factual questions, prioritize search results over general knowledge. "
        "5. If search results are empty or irrelevant, rely on your own knowledge. "
        "6. Never make up information that wasn't in search results or your training. "
        "7. For personal questions about the user, DON'T use web search - use their history."
    )

    metadata_payload = {
        "active_modules": sorted(active_modules),  # Context router — tells conversation_reasoner which tier 2 sections to build
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
        # Friction Framework context
        "operating_system": internal_state.get("operating_system"),
        "dosha_baseline": internal_state.get("dosha_baseline"),
        "life_context": internal_state.get("life_context"),
        "decision_profile": internal_state.get("decision_profile"),
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

    # background task routing refresh when new task intent might be present
    try:
        if stored_intents:
            from sakhi.apps.worker.tasks.task_routing_worker import enqueue_task_routing
            enqueue_task_routing(user_id)
    except Exception:
        pass

    try:
        reply_bundle = await generate_reply(
            person_id=user_id,
            user_text=body.text,
            metadata=metadata_payload,
            behavior_profile=behavior_profile,
            session_id=str(session_id) if session_id else "",
            return_debug=True,  # Enable debug info for adaptive response
        )
    except Exception as reply_exc:
        logger.error("[turn_v2] CRITICAL - generate_reply failed for user=%s: %s", user_id, reply_exc, exc_info=True)
        reply_bundle = {"reply": "I'm here. Could you say that again?", "tone_blueprint": {}, "journaling_ai": None}

    reply_text = reply_bundle.get("reply", "")
    tone_blueprint = reply_bundle.get("tone_blueprint") or {}
    journaling_ai = reply_bundle.get("journaling_ai")
    adaptive_response = reply_bundle.get("adaptive_response")  # Adaptive Response Framework output
    reply_debug = reply_bundle.get("debug") or {}  # Full debug from conversation engine

    # Persist conversation turns to database for continuity
    if session_id:
        try:
            # Store user turn
            await append_turn(
                user_id=user_id,
                session_id=str(session_id),
                role="user",
                text=body.text,
                source=body.source,
            )
            # Store assistant turn (use 'assistant' for DB constraint compatibility)
            if reply_text:
                await append_turn(
                    user_id=user_id,
                    session_id=str(session_id),
                    role="assistant",  # DB constraint requires 'user' or 'assistant'
                    text=reply_text,
                    tone=tone_blueprint.get("style"),
                    source=body.source,  # Inherit source from user turn
                )
        except Exception as exc:
            logger.error("[turn_v2] Turn persistence failed: %s", exc)

    result = {
        "reply": reply_text,
        "sessionId": str(session_id) if session_id else user_id,
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
        # Friction Framework context
        "operating_system": internal_state.get("operating_system"),
        "dosha_baseline": internal_state.get("dosha_baseline"),
        "life_context": internal_state.get("life_context"),
        "decision_profile": internal_state.get("decision_profile"),
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
        # Personalized Recommendations (Ayurvedic + personal patterns)
        "friction_state": friction_state_computed,
        "personalized_recommendations": personalized_recommendations,
        "recommendation_trigger": recommendation_trigger,
        # Scheduling & Calendar Context
        "scheduling_context": scheduling_context,
        "scheduling_intent": scheduling_intent_detected.value if hasattr(scheduling_intent_detected, 'value') else scheduling_intent_detected,
        "relationship_nudges": relationship_nudges,
        "mesh_coordination": scheduling_context.get("mesh_coordination") if scheduling_context else None,
        "vision_context": vision_context if vision_context else None,
        "agentic_context": agentic_context if agentic_context else None,
        "agentic_results": agentic_results if agentic_results else None,
        # Agent Task context
        "agent_task_context": agent_task_context if agent_task_context else None,
        "agent_task_detected": agent_task_detected,
        "agent_task_plan": agent_task_plan,
        "agent_task_execution": agent_task_execution,
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

    try:
        memory_write = await _write_turn_memory(
            person_id=user_id,
            dialog_state=dialog_state,
            reasoning=reasoning,
            entry_id=session_id,
            user_text=body.text,
        )
    except Exception as mem_exc:
        logger.error("[turn_v2] _write_turn_memory failed: %s", mem_exc)
        memory_write = {}

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
                "forecast_state": brain_state.get("forecast_state") or {},
            },
            memory_short_term=[],
            pattern_sense=brain_state.get("pattern_sense"),
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
        # Adaptive Response Framework debug
        "adaptive_response": adaptive_response,
        "conversation_engine_debug": reply_debug,
    }

    human_insights = None  # Debug panel disabled by default

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

    unified_narrative = None  # Debug narrative disabled by default

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

    # Unified ingest: queue heavy memory processing for background workers
    if entry_id and not minimal_mode:
        if not await _unified_ingest_schema_ok():
            logger.warning("[UnifiedIngest] Skipping: schema not ready")
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
    # Per-turn workers: Only essential memory capture + episodic consolidation
    # Other state workers run on daily schedule - context comes from:
    # conversation_history + memory_recall + memory_graph + personal_model (refreshed daily)
    queued_jobs = [
        "turn_memory_update",           # Essential: captures turn to memory
        "episodic_consolidation_v21",   # Essential: creates episodes + state vectors + feeds memory graph
        "preference_learning",          # Learn preferences from "I like..." statements
    ]
    # MOVED TO DAILY SCHEDULE (see scheduler.py):
    # - ayurvedic_pipeline (daily 6am)
    # - rhythm_forecast (daily 7am, also weekly)
    # - identity_momentum_deep (daily 6am)
    # - emotion_soul_rhythm_deep (daily 4am)
    # - esr (daily 4am)
    # - soul_refresh (daily 6am)
    # - longitudinal_update (weekly - already scheduled)
    # - rhythm_soul_deep (daily 6am, weekly 8am)
    # DISABLED: journal_enrich until reviewed
    # if entry_id:
    #     queued_jobs.append("journal_enrich")
    inferred_intent = stored_intents[0] if stored_intents else (topics_for_signals[0] if topics_for_signals else None)
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
        "text": body.text,
        "ts": datetime.datetime.utcnow().isoformat(),
        "entry_id": str(entry_id) if entry_id else None,
        "facets": facets_for_worker,
        "thread_id": user_id,
        "behavior_profile": behavior_profile,
        "mode": "today",
        "emotion_update": emotion_update,
        "persona_update": persona_update,
    }
    logger.error(
        "[turn_v2] dispatch mode=%s SAKHI_DISABLE_QUEUE=%s turn_id=%s jobs=%s",
        "inline" if disable_queue else "queue",
        "1" if disable_queue else "0",
        turn_id,
        queued_jobs,
    )
    if disable_queue:
        logger.error("[turn_v2] queue disabled via SAKHI_DISABLE_QUEUE, running inline turn_id=%s", turn_id)
        from sakhi.apps.worker.pipelines.turn_updates.runner import process_turn_job_async

        for job_type in queued_jobs:
            try:
                await process_turn_job_async(job_type=job_type, turn_id=turn_id, person_id=user_id, payload=payload)
            except Exception as exc:
                logger.warning("[turn_v2] inline job failed type=%s turn_id=%s err=%s", job_type, turn_id, exc)
    else:
        enqueue_turn_jobs(turn_id, user_id, queued_jobs, payload)

    logger.error(
        "[turn_v2] response snapshot entry_id=%s session_id=%s minimal_mode=%s queued_jobs=%s",
        entry_id,
        session_id,
        minimal_mode,
        queued_jobs,
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
        "adaptive_response": adaptive_response,  # Adaptive Response Framework output
    }
