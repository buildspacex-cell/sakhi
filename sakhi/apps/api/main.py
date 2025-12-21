"""FastAPI application entrypoint for Sakhi."""

from __future__ import annotations

import json
import os

if os.getenv("ENV", "development") in {"development", "dev", "local"}:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        # In production containers we should never depend on a local .env file.
        pass

REQUIRED_ENV_VARS = ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "OPENAI_API_KEY")
_missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if _missing:
    raise RuntimeError(f"Missing required env var(s): {', '.join(_missing)}")

DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID") or os.getenv("DEMO_USER_ID")

from sakhi.libs.logging_utils import configure_logging, colorize

configure_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics

app = FastAPI(title="Sakhi API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sakhi-web.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

import asyncio
from contextlib import asynccontextmanager
import logging
import uuid
import copy
from datetime import datetime, timedelta, timezone, date
from functools import lru_cache
from typing import Any, AsyncIterator, Dict, List, Literal, Optional

import asyncpg
import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue

from sakhi.apps.api.admin import admin
from sakhi.apps.api.diagnose import router_diag
from sakhi.apps.api.journal_analytics import jr
from sakhi.apps.api.routes.chat import router as chat_router
from sakhi.apps.api.routes.conversation import router as conversation_router
from sakhi.apps.api.routes.graph_debug import router as graph_debug_router
from sakhi.apps.api.routes.journal_turn import journal_turn_router
from sakhi.apps.api.routes.turn_v2 import router as turn_v2_router
from sakhi.apps.api.routes.narrative import router as narrative_router
from sakhi.apps.api.routes.rhythm_soul import router as rhythm_soul_router
from sakhi.apps.api.routes.emotion_soul_rhythm import router as esr_router
from sakhi.apps.api.routes.identity_momentum import router as identity_momentum_router
from sakhi.apps.api.routes.decision_graph import router as decision_graph_router
from sakhi.apps.api.routes.identity_timeline import router as identity_timeline_router
from sakhi.apps.api.routes.llm import router as llm_router
from sakhi.apps.api.routes.consolidator import router as consolidator_router
from sakhi.apps.api.routes.insights import router as insights_router
from sakhi.apps.api.routes.soul import router as soul_routes
from sakhi.apps.api.routes.soul_analytics import router as soul_analytics_router
from sakhi.apps.api.routes.presence import router as presence_router
from sakhi.apps.api.routes.persona import router as persona_router
from sakhi.apps.api.routes.planner import router as planner_router
from sakhi.apps.api.routes.rhythm import router as rhythm_router
from sakhi.apps.api.routes.breath import router as breath_router
from sakhi.apps.api.routes.events import router as events_router
from sakhi.apps.api.routes.memory_graph import router as memory_graph_router
from sakhi.apps.api.routes.memory import router as memory_recall_router
from sakhi.apps.api.routes.feedback import router as feedback_router
from sakhi.apps.api.routes.analytics import router as analytics_router
from sakhi.apps.api.routes.adjustments import router as adjustments_router
from sakhi.apps.api.routes.tone import router as tone_router
from sakhi.apps.api.routes.environment import router as environment_router
from sakhi.apps.api.routes.system_audit import router as system_audit_router
from sakhi.apps.api.routes.reflection_daily import router as reflection_daily_router
from sakhi.apps.api.routes.growth import router as growth_router
from sakhi.apps.api.routes.focus import router as focus_router
from sakhi.apps.api.routes.journey import router as journey_router
from sakhi.apps.api.routes.insight import router as insight_router
from sakhi.apps.api.routes.brain import router as brain_router
from sakhi.apps.api.routers import awareness as awareness_router
from sakhi.apps.api.routers import hands as hands_router
from sakhi.apps.api.routers import intel as intel_router
from sakhi.apps.api.routers import recall as recall_router
from sakhi.apps.api.routers import soul as soul_router
from sakhi.apps.api.routers import clarity as clarity_router
from sakhi.apps.api.routers import memory as memory_router
from sakhi.apps.api.routers import reflection_summary as reflection_summary_router
from sakhi.apps.api.routers import narratives as narratives_router
from sakhi.apps.api.routers import debug as debug_router
from sakhi.apps.api.routes.alignment import router as alignment_router
from sakhi.apps.api.routes.coherence import router as coherence_router
from sakhi.apps.api.routes.narrative_arcs import router as narrative_arcs_router
from sakhi.apps.api.routes.patterns import router as patterns_router
from sakhi.apps.api.routes.inner_dialogue import router as inner_dialogue_router
from sakhi.apps.api.routes.identity_state import router as identity_state_router
from sakhi.apps.api.routes.inner_conflict import router as inner_conflict_router
from sakhi.apps.api.routes.forecast import router as forecast_router
from sakhi.apps.api.routes.nudge import router as nudge_router
from sakhi.apps.api.routes.daily_reflection import router as daily_reflection_router
from sakhi.apps.api.routes.evening_closure import router as evening_closure_router
from sakhi.apps.api.routes.morning_ask import router as morning_ask_router
from sakhi.apps.api.routes.morning_preview import router as morning_preview_router
from sakhi.apps.api.routes.morning_momentum import router as morning_momentum_router
from sakhi.apps.api.routes.micro_momentum import router as micro_momentum_router
from sakhi.apps.api.routes.micro_recovery import router as micro_recovery_router
from sakhi.apps.api.routes.focus_path import router as focus_path_router
from sakhi.apps.api.routes.mini_flow import router as mini_flow_router
from sakhi.apps.api.routes.micro_journey import router as micro_journey_router
from sakhi.apps.api.routes.focus_path import router as focus_path_router
from sakhi.apps.api.routes.micro_momentum import router as micro_momentum_router
from sakhi.apps.api.routes.task_routing import router as task_routing_router
from sakhi.apps.api.routes.experience_journal import router as experience_journal_router
from sakhi.apps.api.routes.experience_weekly import router as experience_weekly_router
from sakhi.apps.api.routers import person as person_router
from sakhi.apps.api.routers import person_edit as person_edit_router
from sakhi.apps.api.core.llm import set_router as set_llm_router
from sakhi.apps.api.core.utils import EnhancedJSONEncoder
from sakhi.apps.api.middleware import ReplyPacingMiddleware, TelemetryMiddleware
from sakhi.apps.worker.jobs import enqueue_embedding_and_salience
from sakhi.apps.worker.jobs_alignment import compute_alignment
from sakhi.apps.api.deps.auth import get_current_user_id
from sakhi.libs.ayurveda.dosha_rules import rhythm_modifiers
from sakhi.libs.conversation.outer_inner import classify_outer_inner
from sakhi.libs.conversation.state import ConversationStateManager, mirror_outer_conversation_state
from sakhi.libs.actions.intents import create_intent_from_entry
from sakhi.libs.debug.narrative import build_narrative_debug
from sakhi.apps.worker.jobs_goal_actions import commit_plan
from sakhi.apps.api.services.memory.memory_ingest import ingest_journal_entry
from sakhi.libs.conversation.clarify_outer import permission_prompt as clarify_permission_prompt
from sakhi.libs.conversation.outer_flow import (
    ensure_flow as ensure_outer_flow,
    merge_classification as merge_outer_classification,
    apply_answer as apply_outer_answer,
    prepare_next_question as prepare_outer_question,
    record_user_message,
    build_classifier_context,
    is_active as outer_flow_is_active,
)
from sakhi.libs.llm_router import BaseProvider, BudgetExceededError, LLMResponse, LLMRouter, Task
from sakhi.libs.llm_router.openrouter import OpenRouterProvider
from sakhi.libs.llm_router.openai_provider import make_openai_provider_from_env
from sakhi.libs.llm_router.web_provider import WebProvider
from sakhi.libs.retrieval import HybridRetriever, RetrieverConfig, build_reflection_context, search_journals
from sakhi.libs.embeddings import embed_text
from sakhi.libs.retrieval.recall import recall
from sakhi.libs.rhythm.beat_calc import calc_daily_beats
from sakhi.libs.schemas import get_settings
from sakhi.libs.schemas.db import execute, get_async_pool
from sakhi.libs.security import encrypt_field, run_idempotent
from sakhi.libs.memory import capture_salient_memory, fetch_recent_memories

JSONResponse.render = lambda self, content: json.dumps(
    content, ensure_ascii=False, cls=EnhancedJSONEncoder
).encode("utf-8")

import os

ALLOW_WEB = os.getenv("SAKHI_ALLOW_WEB_SEARCH", "false").lower() == "true"
PILOT_AUTH = os.getenv("PILOT_AUTH", "0") == "1"

if PILOT_AUTH:
    from sakhi.apps.api.middleware.auth_pilot import PilotAuthAndRateLimit
    app.add_middleware(PilotAuthAndRateLimit, rpm=90)

app.add_middleware(TelemetryMiddleware)
app.add_middleware(ReplyPacingMiddleware)


@app.get("/health")
def health():
  return {"status": "ok"}


@app.middleware("http")
async def reject_demo_in_prod(request: Request, call_next):
    if os.getenv("NODE_ENV") == "production" and os.getenv("DEMO_MODE", "false").lower() == "true":
        return JSONResponse({"error": "Demo mode disabled in prod"}, status_code=status.HTTP_403_FORBIDDEN)
    return await call_next(request)

DEFAULT_USER_EMAIL = "anon@sakhi.local"
DEFAULT_USER_NAME = "Sakhi Companion"

_USER_ID_CACHE: str | None = None
_USER_LOCK = asyncio.Lock()
LOGGER = logging.getLogger(__name__)
_REFLECTION_CACHE: Dict[str, str] = {}
SETTINGS = get_settings()
EVENT_BRIDGE_URL = SETTINGS.event_bridge_url

core_router = APIRouter()


@lru_cache(maxsize=128)
def _cache_reflection_key(user_id: str, theme: str, day: str) -> str:
    """Return a stable cache key for reflection summaries."""

    return f"{user_id}:{theme}:{day}"


def _build_reflection_fallback(context: Dict[str, Any]) -> str:
    journals = context.get("journals", []) or []
    bullets = [f"- {entry.get('content', '')[:120]}..." for entry in journals[:4]]
    fallback_lines = bullets + [
        "",
        "Next Steps:",
        "- Revisit tomorrow",
        "- Pick 1 small action",
        "- Log one win",
    ]
    return "\n".join(fallback_lines)


def _infer_locale(request: Request) -> str:
    header = request.headers.get("accept-language")
    if not header:
        return "en-US"
    primary = header.split(",")[0].strip()
    return primary or "en-US"


def _infer_timezone(request: Request) -> str:
    for key in ("x-timezone", "time-zone", "timezone"):
        value = request.headers.get(key)
        if value:
            return value
    return "UTC"


def _build_message_payload(
    *,
    entry_id: str,
    user_id: str,
    text: str,
    locale: str,
    timezone_label: str,
    channel: str,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload_extras: Dict[str, Any] = {"entry_id": entry_id}
    if extras:
        payload_extras.update(extras)
    return {
        "schema_version": "0.1.0",
        "id": f"journal:{entry_id}",
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content": {"text": text, "modality": "text", "locale": locale or "en-US"},
        "source": {"channel": channel},
        "metadata": {"timezone": timezone_label, "extras": payload_extras},
    }


async def _publish_message_ingested(message: Dict[str, Any]) -> None:
    if not EVENT_BRIDGE_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(EVENT_BRIDGE_URL, json={"message": message})
    except httpx.HTTPError as exc:
        LOGGER.warning("Failed to publish message.ingested id=%s error=%s", message.get("id"), exc)


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    user_id: str | None = None


class RetrievalResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]


class PlanRequest(BaseModel):
    objective: str = Field(min_length=1)
    preferences: Dict[str, Any] | None = None
    constraints: Dict[str, Any] | None = None


class PlanTask(BaseModel):
    id: str
    title: str
    scheduled_for: datetime
    duration_minutes: int | None = None
    sequence: int | None = None


class PlanResponse(BaseModel):
    objective: str
    tasks: List[PlanTask]
    status: str = Field(default="scheduled")


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    due_at: datetime | None = None
    user_id: Optional[uuid.UUID] = None
    related_entry_id: Optional[uuid.UUID] = None


class TaskCreateResponse(BaseModel):
    id: str
    title: str
    status: str
    due_at: datetime | None = None


class MemoryItem(BaseModel):
    id: str
    kind: str
    summary: str
    importance: float
    source_conversation: str | None = None
    source_message_id: str | None = None
    created_at: datetime
    metadata: Dict[str, Any] | None = None


class BodySignalRequest(BaseModel):
    kind: Literal["sleep", "energy", "meal", "movement"]
    value: Dict[str, Any]
    at: datetime | None = None
    user_id: str | None = None


class BodySignalResponse(BaseModel):
    id: int
    user_id: str
    kind: Literal["sleep", "energy", "meal", "movement"]
    value: Dict[str, Any]
    at: datetime


def _clean_text(raw: str) -> str:
    return " ".join(raw.strip().split())


def _default_target_date(horizon: str) -> date | None:
    today = datetime.now(timezone.utc).date()
    horizon = (horizon or "").lower()

    if horizon in {"", "none"}:
        return None
    if horizon == "today":
        return today
    if horizon == "week":
        # end of the current week (Sunday)
        days_ahead = 6 - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    if horizon == "month":
        # last day of the month
        next_month = today.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)
    if horizon == "quarter":
        quarter = ((today.month - 1) // 3) + 1
        last_month = quarter * 3
        first_day_next_quarter = date(today.year + (1 if last_month == 12 else 0), ((last_month % 12) + 1), 1)
        return first_day_next_quarter - timedelta(days=1)
    if horizon == "year":
        return date(today.year, 12, 31)
    if horizon == "long_term":
        return today + timedelta(days=180)
    return None


async def _ensure_default_user_id() -> uuid.UUID:
    global _USER_ID_CACHE
    if _USER_ID_CACHE:
        return uuid.UUID(_USER_ID_CACHE)

    async with _USER_LOCK:
        if _USER_ID_CACHE:
            return uuid.UUID(_USER_ID_CACHE)

        await _ensure_user_record(user_uuid)
        pool = await get_async_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                DEFAULT_USER_EMAIL,
            )
            if row is None:
                row = await connection.fetchrow(
                    """
                    INSERT INTO users (email, full_name)
                    VALUES ($1, $2)
                    ON CONFLICT (email) DO UPDATE
                    SET updated_at = now()
                    RETURNING id
                    """,
                    DEFAULT_USER_EMAIL,
                    DEFAULT_USER_NAME,
                )

        _USER_ID_CACHE = str(row["id"])
        return uuid.UUID(_USER_ID_CACHE)


async def _ensure_user_record(user_uuid: uuid.UUID, *, email_hint: str | None = None) -> None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        existing = await connection.fetchrow("SELECT 1 FROM users WHERE id = $1", user_uuid)
        if existing:
            return
        placeholder_email = email_hint or f"{user_uuid}@sakhi.local"
        await connection.execute(
            """
            INSERT INTO users (id, email, full_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO NOTHING
            """,
            user_uuid,
            placeholder_email,
            DEFAULT_USER_NAME,
        )


def _enqueue_job(
    app: FastAPI,
    queue_key: str,
    task_path: str,
    *,
    args: tuple[Any, ...] = (),
    kwargs: Dict[str, Any] | None = None,
    job_id: str | None = None,
) -> None:
    queues = getattr(app.state, "job_queues", None)
    if not isinstance(queues, dict):
        return

    queue: Queue | None = queues.get(queue_key)
    if queue is None:
        return

    resolved_kwargs = kwargs or {}
    identifier = job_id
    if identifier is None:
        if args:
            first = args[0]
            if isinstance(first, str):
                identifier = first
            elif isinstance(first, dict):
                identifier = first.get("id") or first.get("entry_id")
        if identifier is None and resolved_kwargs:
            candidate = resolved_kwargs.get("id") or resolved_kwargs.get("entry_id")
            if isinstance(candidate, str):
                identifier = candidate
    if identifier is None:
        identifier = uuid.uuid4().hex

    try:
        queue.enqueue(
            task_path,
            *args,
            **resolved_kwargs,
            job_id=f"{queue_key}:{identifier}",
            at_front=False,
        )
    except Exception as exc:  # pragma: no cover - best-effort queueing
        LOGGER.warning("Failed to enqueue %s job: %s", queue_key, exc)


def _build_stub_plan(now: datetime, request: PlanRequest) -> List[Dict[str, Any]]:
    base_time = now.replace(second=0, microsecond=0)
    phases = [
        ("Clarify intent", 0),
        ("Outline steps", 30),
        ("Deep work block", 120),
        ("Reflection", 240),
    ]
    focus_window = int(request.preferences.get("focus_block_minutes", 45)) if request.preferences else 45

    tasks: List[Dict[str, Any]] = []
    for idx, (title, offset) in enumerate(phases):
        scheduled = base_time + timedelta(minutes=offset)
        tasks.append(
            {
                "id": str(uuid.uuid4()),
                "title": f"{title} for {request.objective}",
                "scheduled_for": scheduled.isoformat(),
                "duration_minutes": focus_window if "Deep work" in title else 30,
                "sequence": idx + 1,
            }
        )
    return tasks


async def _resolve_user_id(user_id: str | None) -> uuid.UUID:
    if user_id:
        try:
            return uuid.UUID(user_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid user_id") from exc
    return await _ensure_default_user_id()


@core_router.post(
    "/body-signals",
    response_model=BodySignalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["body"],
)
async def record_body_signal(payload: BodySignalRequest, request: Request) -> BodySignalResponse:
    """Persist a body signal measurement for the current or provided user."""

    user_uuid = await _resolve_user_id(payload.user_id)
    timestamp = payload.at or datetime.now(timezone.utc)

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            INSERT INTO body_signals (user_id, kind, value, at)
            VALUES ($1, $2, $3, $4)
            RETURNING id, user_id, kind, value, at
            """,
            user_uuid,
            payload.kind,
            payload.value,
            timestamp,
        )

    if row is None:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="failed to store body signal")

    asyncio.create_task(
        _publish_message_ingested(
            _build_message_payload(
                entry_id=f"body-signal:{row['id']}",
                user_id=str(row["user_id"]),
                text=f"Body signal {payload.kind}: {payload.value}",
                locale=_infer_locale(request),
                timezone_label=_infer_timezone(request),
                channel="body-signal",
                extras={"value": payload.value, "kind": payload.kind},
            )
        )
    )

    return BodySignalResponse(
        id=row["id"],
        user_id=str(row["user_id"]),
        kind=row["kind"],
        value=row["value"],
        at=row["at"],
    )


@core_router.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return a simple health payload."""

    return {"status": "ok"}


@app.get("/presence/preview")
async def presence_preview(user_id: str):
    from sakhi.apps.worker.jobs_presence import outreach

    return await outreach(user_id)


@app.post("/journal/v2", tags=["journal"])
async def journal_v2(
    request: Request,
    raw: Optional[str] = Form(default=None),
    mood: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
    voice: UploadFile | None = File(default=None),
    current_user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Capture a journal entry with optional metadata and voice transcription."""

    debug_mode = request.query_params.get("debug") == "1"

    text_content = raw or ""
    if voice and not text_content.strip():
        try:
            from sakhi.libs.ingest.stt import transcribe_file
        except ImportError as exc:  # pragma: no cover - adapter provided separately
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="transcriber unavailable"
            ) from exc
        text_content = await transcribe_file(voice)

    if not text_content or not text_content.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="empty_entry")

    cleaned = text_content.strip()
    tag_items = [item.strip() for item in (tags or "").split(",") if item.strip()]
    facets_hint: Dict[str, Any] = {}
    if mood:
        facets_hint["mood"] = mood
    if tag_items:
        facets_hint["tags"] = tag_items

    try:
        user_uuid = uuid.UUID(current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid user") from exc
    await _ensure_user_record(user_uuid)
    user_id_value = str(user_uuid)

    fallback_conversation_id = f"journal:{user_id_value}"
    conversation_id = request.headers.get("X-Conversation-Id") or fallback_conversation_id
    state_manager = ConversationStateManager(conversation_id, user_id=user_id_value)
    conversation_state = await state_manager.load()
    active_outer_frame = next(
        (frame for frame in conversation_state.frames if frame.name == "outer_intent" and frame.status == "active"),
        None,
    )
    outer_metadata = active_outer_frame.metadata if active_outer_frame else None
    outer_flow = ensure_outer_flow(outer_metadata) if active_outer_frame else None
    awaiting_outer_step = outer_flow.get("awaiting_step") if outer_flow else None

    if outer_flow is None and conversation_id != fallback_conversation_id:
        fallback_manager = ConversationStateManager(fallback_conversation_id, user_id=user_id_value)
        fallback_state = await fallback_manager.load()
        fallback_outer_frame = next(
            (frame for frame in fallback_state.frames if frame.name == "outer_intent" and frame.status == "active"),
            None,
        )
        if fallback_outer_frame is not None:
            state_manager = fallback_manager
            conversation_state = fallback_state
            conversation_id = fallback_conversation_id
            active_outer_frame = fallback_outer_frame
            outer_metadata = active_outer_frame.metadata
            outer_flow = ensure_outer_flow(outer_metadata)
            awaiting_outer_step = outer_flow.get("awaiting_step") if outer_flow else None

    router_instance = getattr(request.app.state, "llm_router", None)
    def _clamp_unit(value: Any, default: float = 0.0) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default

    raw_classifier: Dict[str, Any] = {}
    features: Dict[str, Any] = {}
    user_message_recorded = False

    if awaiting_outer_step and outer_flow is not None:
        apply_outer_answer(outer_flow, cleaned)
        features = _normalize_classification(dict(outer_flow.get("features", {})))
        raw_track = "outer"
        user_message_recorded = True
    else:
        try:
            classifier_context = None
            if outer_flow is not None:
                classifier_context = build_classifier_context(
                    outer_flow,
                    base_prompt="You are continuing an outer intent clarification.",
                )
            query_text = cleaned if classifier_context is None else f"{classifier_context}\n\nUser: {cleaned}"
            raw_classifier = await classify_outer_inner(query_text, router=router_instance)
            raw_classifier = _normalize_classification(raw_classifier)
            LOGGER.info(
                colorize("LLM classify response", "red"),
                extra={
                    "event": "journal_classification",
                    "conversation_id": conversation_id,
                    "user_id": user_id_value,
                    "text": cleaned,
                    "context": classifier_context,
                    "result": raw_classifier,
                },
            )
        except Exception:
            raw_classifier = {}

        features = dict(raw_classifier or {})
        features = _normalize_classification(features)
        raw_track = str(features.get("track", "inner"))

        if outer_flow is not None:
            merge_outer_classification(outer_flow, features)
            features = dict(outer_flow.get("features", features))
            if outer_flow_is_active(outer_flow):
                raw_track = "outer"

        if raw_track == "outer" and outer_flow is None:
            outer_metadata = {}
            outer_flow = ensure_outer_flow(outer_metadata)
            merge_outer_classification(outer_flow, features)
            features = dict(outer_flow.get("features", features))
            awaiting_outer_step = outer_flow.get("awaiting_step")
            raw_track = "outer"

    features = _force_outer_if_action(cleaned, features)
    raw_track = str(features.get("track", raw_track))
    classifier_payload = features
    track = "outer" if (awaiting_outer_step and outer_flow is not None) else (
        raw_track if raw_classifier else "inner"
    )
    if outer_flow is not None and outer_flow_is_active(outer_flow):
        track = "outer"
    LOGGER.info(
        colorize("Outer track decision", "magenta"),
        extra={
            "event": "journal_track_decision",
            "conversation_id": conversation_id,
            "user_id": user_id_value,
            "track": track,
            "awaiting_step": awaiting_outer_step,
        },
    )

    share_type = str(classifier_payload.get("share_type", "thought"))
    if share_type not in {"thought", "feeling", "story", "goal", "question"}:
        share_type = "thought"
    actionability = _clamp_unit(classifier_payload.get("actionability"), 0.2)
    readiness = _clamp_unit(classifier_payload.get("readiness"), 0.5)

    timeline_payload = classifier_payload.get("timeline") or {}
    if not isinstance(timeline_payload, dict):
        timeline_payload = {}
    horizon = str(timeline_payload.get("horizon", "none"))
    if horizon not in {"none", "today", "week", "month", "quarter", "year", "long_term", "custom_date"}:
        horizon = "none"
    target_date_str = timeline_payload.get("target_date") if isinstance(timeline_payload.get("target_date"), str) else None
    if not target_date_str:
        auto_date = _default_target_date(horizon)
        if auto_date:
            target_date_str = auto_date.isoformat()

    g_mvs_payload = classifier_payload.get("g_mvs") or {}
    if not isinstance(g_mvs_payload, dict):
        g_mvs_payload = {}
    g_mvs = {
        "target_horizon": bool(g_mvs_payload.get("target_horizon")),
        "current_position": bool(g_mvs_payload.get("current_position")),
        "constraints": bool(g_mvs_payload.get("constraints")),
        "criteria": bool(g_mvs_payload.get("criteria")),
        "assets_blockers": bool(g_mvs_payload.get("assets_blockers")),
    }

    emotion = str(classifier_payload.get("emotion", "calm"))
    if emotion not in {"calm", "joy", "hope", "anger", "sad", "anxious", "stressed"}:
        emotion = "calm"
    try:
        sentiment_val = float(classifier_payload.get("sentiment", 0.0) or 0.0)
    except (TypeError, ValueError):
        sentiment_val = 0.0
    sentiment_val = max(-1.0, min(1.0, sentiment_val))

    classifier_tags = classifier_payload.get("tags") or []
    if not isinstance(classifier_tags, (list, tuple)):
        classifier_tags = []
    merged_tags = set(tag for tag in classifier_tags if isinstance(tag, str))
    merged_tags.update(tag_items)

    intent_type = str(classifier_payload.get("intent_type", "question"))
    if intent_type not in {"decision", "goal", "activity", "habit", "question", "micro_task"}:
        intent_type = "question"
    domain = classifier_payload.get("domain")
    if domain is not None and not isinstance(domain, str):
        domain = None

    facets_v2_payload: Dict[str, Any] = {
        "track": track,
        "share_type": share_type,
        "actionability": actionability,
        "readiness": readiness,
        "timeline": {
            "horizon": horizon,
            "target_date": target_date_str,
        },
        "g_mvs": g_mvs,
        "emotion": emotion,
        "sentiment": sentiment_val,
        "tags": sorted(merged_tags),
        "intent_type": intent_type,
        "domain": domain,
    }

    follow_up_question: Optional[str] = None
    if track == "outer":
        if outer_flow is None:
            outer_metadata = outer_metadata or {}
            outer_flow = ensure_outer_flow(outer_metadata)
            merge_outer_classification(outer_flow, classifier_payload)
        if not user_message_recorded and outer_flow is not None:
            record_user_message(outer_flow, cleaned)
        question, awaiting_outer_step = prepare_outer_question(outer_flow)
        if not question:
            if not outer_flow.get("permission_offered"):
                question = clarify_permission_prompt()
                outer_flow["permission_offered"] = True
                outer_flow["awaiting_step"] = "permission"
            else:
                outer_flow["ready_for_plan"] = True
        else:
            outer_flow["permission_offered"] = False
        follow_up_question = question or None
    else:
        follow_up_question = "If you’d like to keep exploring this, I’m right here."

    try:
        encrypted_snapshot = encrypt_field(cleaned)
    except Exception:  # pragma: no cover - encryption optional in local dev
        encrypted_snapshot = None
    if encrypted_snapshot:
        meta = facets_hint.setdefault("meta", {})
        meta["encrypted_snapshot"] = encrypted_snapshot
    facets_hint.setdefault("preview", cleaned[:160])
    locale = _infer_locale(request)
    timezone_label = _infer_timezone(request)
    source_channel = request.headers.get("x-client-channel", "journal-api-v2")

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        facets_dict = dict(facets_hint)
        facets_v2_dict = dict(facets_v2_payload)
        narrative_dict: Dict[str, Any] = {}
        debug_payload_dict: Dict[str, Any] = {
            "facets_hint": facets_dict,
            "classifier": classifier_payload,
        }
        cleaned_text = cleaned
        facets_json = json.dumps(facets_v2_dict)
        narrative_json = json.dumps(narrative_dict)
        debug_json = json.dumps(debug_payload_dict)
        legacy_facets_json = json.dumps(facets_dict)
        fallback_facets_json = json.dumps(facets_dict)
        fallback_facets_v2_json = json.dumps(facets_v2_dict)
        print("DEBUG user_id used:", user_id_value)
        try:
            await connection.execute(
                "select set_config('request.jwt.claims', $1, true)",
                json.dumps({"sub": user_id_value}),
            )
            row = await connection.fetchrow(
                """
                INSERT INTO public.journal_entries (user_id, content)
                VALUES ($1::uuid, $2::text)
                RETURNING id
                """,
                user_uuid,
                cleaned,
            )
        except asyncpg.PostgresError as error:
            print("PG ERROR:", error.__class__.__name__, str(error))
            try:
                row = await connection.fetchrow(
                    """
                    INSERT INTO public.journal_entries (user_id, content)
                    VALUES ($1::uuid, $2::text)
                    RETURNING id
                    """,
                    user_uuid,
                    cleaned,
                )
            except asyncpg.PostgresError as exc:
                print("PG ERROR:", exc.__class__.__name__, str(exc))
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="database constraint error") from exc

    entry_id = str(row["id"])
    asyncio.create_task(
        ingest_journal_entry(
            {
                "id": entry_id,
                "user_id": user_id_value,
                "content": cleaned,
                "cleaned": cleaned_text,
                "facets": facets_dict,
                "facets_v2": facets_v2_payload,
                "mood": mood,
                "tags": tag_items,
                "layer": track,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    intent_id: Optional[int] = None
    if track == "outer" and intent_type in {"decision", "goal", "activity", "habit", "micro_task"}:
        try:
            intent_id = await create_intent_from_entry(
                user_id_value,
                entry_id,
                cleaned[:64],
                cleaned,
                facets_v2_payload,
            )
        except Exception:  # pragma: no cover - intent creation best-effort
            intent_id = None

    extras_payload: Dict[str, Any] = {"entry_id": entry_id}
    if mood:
        extras_payload["mood"] = mood
    if tag_items:
        extras_payload["tags"] = tag_items
    if facets_hint:
        extras_payload["facets_hint"] = facets_hint
    extras_payload["facets_v2"] = facets_v2_payload
    if intent_id is not None:
        extras_payload["intent_id"] = intent_id
    if follow_up_question:
        extras_payload["follow_up"] = follow_up_question
    message_payload = _build_message_payload(
        entry_id=entry_id,
        user_id=user_id_value,
        text=cleaned,
        locale=locale,
        timezone_label=timezone_label,
        channel=source_channel,
        extras=extras_payload,
    )
    asyncio.create_task(_publish_message_ingested(message_payload))
    await enqueue_embedding_and_salience(entry_id)
    response_payload: Dict[str, Any] = {"id": entry_id, "status": "queued"}
    if follow_up_question:
        response_payload["follow_up"] = follow_up_question
    if intent_id is not None:
        response_payload.setdefault("actions", {})["intent_id"] = intent_id
    if debug_mode:
        response_payload.setdefault("debug", {})["narrative"] = build_narrative_debug(
            cleaned,
            facets_v2_payload,
            "journal",
            asked=follow_up_question,
            intent_id=intent_id,
        )
        response_payload["facets_v2"] = facets_v2_payload
    LOGGER.info(
        "journal_v2 saved entry track=%s intent_id=%s follow_up=%s",
        track,
        intent_id,
        follow_up_question,
    )

    journaling_metadata = {
        "track": track,
        "emotion": emotion,
        "tags": sorted(merged_tags),
        "classifier": classifier_payload,
    }
    journaling_metadata.setdefault("conversation_id", conversation_id)
    await state_manager.ensure_frame(
        "journaling",
        slots={
            "entry_id": entry_id,
            "intent_id": intent_id,
            "horizon": facets_v2_payload.get("timeline", {}).get("horizon"),
        },
        metadata=journaling_metadata,
    )

    outer_metadata_payload = copy.deepcopy(outer_metadata) if isinstance(outer_metadata, dict) else {}
    outer_metadata_payload.setdefault("conversation_id", outer_metadata_payload.get("conversation_id") or conversation_id)
    if track == "outer" and outer_flow is not None:
        outer_metadata_payload.setdefault("outer_flow", outer_flow)
        outer_metadata_payload["features"] = classifier_payload
        outer_metadata_payload["answers"] = outer_flow.get("answers", {})
        outer_metadata_payload["notes"] = outer_flow.get("notes", {})
        outer_metadata_payload["awaiting_step"] = outer_flow.get("awaiting_step")
        outer_metadata_payload["ready_for_plan"] = outer_flow.get("ready_for_plan")
        outer_metadata_payload["permission_offered"] = outer_flow.get("permission_offered")

        await state_manager.ensure_frame(
            "outer_intent",
            slots={
                "timeline": classifier_payload.get("timeline"),
                "g_mvs": classifier_payload.get("g_mvs"),
                "intent_type": classifier_payload.get("intent_type"),
            },
            metadata=outer_metadata_payload,
        )

    turn_metadata = {
        "kind": "journal_entry_v2",
        "entry_id": entry_id,
        "intent_id": intent_id,
        "follow_up": follow_up_question,
        "outer_flow": outer_flow,
        "conversation_id": conversation_id,
    }
    await state_manager.record_turn(
        user_message=cleaned,
        assistant_message=follow_up_question,
        metadata=turn_metadata,
    )
    root_conversation_id = outer_metadata_payload.get("conversation_id")
    if root_conversation_id and root_conversation_id != conversation_id:
        await mirror_outer_conversation_state(
            user_id=user_id_value,
            source_conversation_id=conversation_id,
            target_conversation_id=root_conversation_id,
            slots={
                "timeline": classifier_payload.get("timeline"),
                "g_mvs": classifier_payload.get("g_mvs"),
                "intent_type": classifier_payload.get("intent_type"),
            },
            metadata=dict(outer_metadata_payload),
            user_message=cleaned,
            assistant_message=follow_up_question,
        )
    asyncio.create_task(
        capture_salient_memory(
            router=router_instance,
            user_id=user_id_value,
            conversation_id=conversation_id,
            user_text=cleaned,
            assistant_text=follow_up_question or "Journal entry saved.",
            outer_features=classifier_payload,
        )
    )

    return response_payload


@core_router.post(
    "/retrieval",
    response_model=RetrievalResponse,
    tags=["retrieval"],
)
async def retrieval_search(payload: RetrievalRequest, request: Request) -> RetrievalResponse:
    """Search journal entries using the configured retriever."""

    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="query is required")

    try:
        query_embedding = await embed_text(query)
    except Exception:
        query_embedding = None

    try:
        recall_results = await recall(user_id or str(await _ensure_default_user_id()), query, embedding=query_embedding)
    except Exception:
        retriever: HybridRetriever | None = getattr(request.app.state, "retriever", None)
        fallback_results = await search_journals(retriever, query, embedding=query_embedding)
        return RetrievalResponse(query=query, results=fallback_results)

    return RetrievalResponse(query=query, results=recall_results)


@core_router.get(
    "/memories",
    response_model=List[MemoryItem],
    tags=["memory"],
)
async def list_memories(
    limit: int = 10,
    current_user_id: str = Depends(get_current_user_id),
) -> List[MemoryItem]:
    """Return recent user memories for inspection or downstream tooling."""

    try:
        user_uuid = uuid.UUID(current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid user") from exc

    clamped_limit = max(1, min(limit, 50))
    items = await fetch_recent_memories(str(user_uuid), limit=clamped_limit)
    response: List[MemoryItem] = []
    for item in items:
        response.append(
            MemoryItem(
                id=str(item.get("id")),
                kind=str(item.get("kind")),
                summary=str(item.get("summary")),
                importance=float(item.get("importance") or 0.0),
                source_conversation=item.get("source_conversation"),
                source_message_id=item.get("source_message_id"),
                created_at=item.get("created_at") or datetime.now(timezone.utc),
                metadata=item.get("metadata") or {},
            )
        )
    return response


@core_router.post(
    "/plan",
    response_model=PlanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["planning"],
)
async def create_plan(
    payload: PlanRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PlanResponse:
    """Draft a stubbed plan and schedule background computation."""

    if not idempotency_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key header is required")

    handler_context: Dict[str, Any] = {}

    async def handler() -> Dict[str, Any]:
        now = datetime.now()
        tasks = _build_stub_plan(now, payload)
        user_uuid = await _ensure_default_user_id()
        handler_context["user_id"] = str(user_uuid)
        plan_payload: Dict[str, Any] = {
            "objective": payload.objective,
            "tasks": tasks,
            "status": "scheduled",
        }
        _enqueue_job(
            request.app,
            "salience",
            "sakhi.apps.worker.tasks.compute_salience",
            args=(
                {
                    "objective": payload.objective,
                    "preferences": payload.preferences or {},
                    "constraints": payload.constraints or {},
                    "tasks": tasks,
                },
            ),
        )
        _enqueue_job(
            request.app,
            "reflection",
            "sakhi.apps.worker.jobs_reflection_hooks.on_plan_created",
            args=(str(user_uuid),),
        )
        return plan_payload

    result = await run_idempotent(
        headers={"idempotency-key": idempotency_key},
        handler=handler,
        event_type="plan.create",
        payload={
            "objective": payload.objective,
            "preferences": payload.preferences,
            "constraints": payload.constraints,
        },
    )
    plan_response = PlanResponse.model_validate(result)

    user_id_for_plan = handler_context.get("user_id", str(await _ensure_default_user_id()))
    plan_entry_id = uuid.uuid4().hex
    asyncio.create_task(
        _publish_message_ingested(
            _build_message_payload(
                entry_id=f"plan:{plan_entry_id}",
                user_id=user_id_for_plan,
                text=f"Plan request: {payload.objective}",
                locale=_infer_locale(request),
                timezone_label=_infer_timezone(request),
                channel="plan-api",
                extras={
                    "plan": plan_response.model_dump(),
                    "preferences": payload.preferences,
                    "constraints": payload.constraints,
                },
            )
        )
    )

    conversation_id = request.headers.get("X-Conversation-Id") or f"plan:{user_id_for_plan}"
    router_instance = getattr(request.app.state, "llm_router", None)
    plan_features = await classify_outer_inner(payload.objective, router=router_instance)
    state_manager = ConversationStateManager(conversation_id, user_id=user_id_for_plan)
    await state_manager.ensure_frame(
        "planning",
        slots={
            "objective": payload.objective,
            "task_count": len(plan_response.tasks),
        },
        metadata={
            "preferences": payload.preferences or {},
            "constraints": payload.constraints or {},
            "features": plan_features,
        },
    )
    await state_manager.record_turn(
        user_message=payload.objective,
        assistant_message=f"Scheduled {len(plan_response.tasks)} tasks.",
        metadata={
            "kind": "plan_create",
            "tasks": [task.model_dump() for task in plan_response.tasks],
        },
    )
    asyncio.create_task(
        capture_salient_memory(
            router=router_instance,
            user_id=user_id_for_plan,
            conversation_id=conversation_id,
            user_text=payload.objective,
            assistant_text=f"Plan drafted with {len(plan_response.tasks)} steps.",
            outer_features=plan_features,
        )
    )

    return plan_response


@app.post("/intents/{intent_id}/commit", tags=["intents"])
async def commit_intent(intent_id: int) -> Dict[str, Any]:
    result = await commit_plan(intent_id)
    if not result.get("planned"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error", "not_found"))
    return result


@core_router.post("/actions/task", response_model=TaskCreateResponse, tags=["actions"])
async def create_action_task(payload: TaskCreateRequest) -> TaskCreateResponse:
    """Create a task row when the action router requests it."""

    user_uuid = payload.user_id or await _ensure_default_user_id()
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            INSERT INTO tasks (user_id, related_entry_id, title, description, due_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, title, status, due_at
            """,
            user_uuid,
            payload.related_entry_id,
            payload.title,
            payload.description,
            payload.due_at,
        )

    if row is None:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="failed to create task")

    return TaskCreateResponse(
        id=str(row["id"]),
        title=row["title"],
        status=row["status"],
        due_at=row["due_at"],
    )


class _StubProvider(BaseProvider):
    """Fallback provider that echoes the last user message."""

    def __init__(self) -> None:
        super().__init__(name="stub")

    async def chat(
        self,
        *,
        messages,
        model: str,
        tools=None,
        **kwargs,
    ) -> LLMResponse:
        last = messages[-1] if messages else {"role": "assistant", "content": "Sakhi is online."}
        content = last.get("content", "Sakhi is online.")
        return LLMResponse(
            model=model,
            task=Task.CHAT,
            text=content,
            provider=self.name,
            usage={"provider": "stub"},
        )

    async def embed(self, *, inputs, model: str, **kwargs) -> LLMResponse:
        raise NotImplementedError("Stub provider does not support embeddings")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # Configure the LLM router with a default stub handler.
    default_provider = (settings.llm_router or "stub").lower()
    router = LLMRouter()
    router.register_provider("stub", _StubProvider())
    chat_providers: list[str] = []
    tool_providers: list[str] = []

    # OpenAI provider (direct)
    openai_provider = make_openai_provider_from_env()
    if openai_provider:
        router.register_provider("openai", openai_provider, daily_budget=None)
        chat_providers.append("openai")
        tool_providers.append("openai")

    # OpenRouter provider
    api_key = settings.openrouter_api_key or os.getenv("LLM_API_KEY")
    if api_key:
        base_url = os.getenv("OPENROUTER_BASE_URL")
        tenant = os.getenv("OPENROUTER_TENANT")
        try:
            openrouter_provider = OpenRouterProvider(
                api_key=api_key,
                base_url=base_url,
                tenant=tenant,
            )
            router.register_provider("openrouter", openrouter_provider)
            chat_providers.append("openrouter")
            tool_providers.append("openrouter")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to initialize OpenRouter provider: %s", exc)

    if ALLOW_WEB:
        try:
            web_provider = WebProvider()
            router.register_provider("web", web_provider)
            chat_providers.append("web")
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to initialize web provider: %s", exc)

    chat_providers.append("stub")
    tool_providers.append("stub")

    router.set_policy(Task.CHAT, chat_providers)
    router.set_policy(Task.TOOL, tool_providers)
    LOGGER.info(
        colorize("Router configured", "cyan"),
        extra={
            "event": "router_config",
            "providers": list(router._providers.keys()),
            "chat_policy": router._config.policy.get(Task.CHAT),
            "model_chat": os.getenv("MODEL_CHAT"),
            "model_tool": os.getenv("MODEL_TOOL"),
            "model_reflect": os.getenv("MODEL_REFLECT"),
            "openai_model_chat": os.getenv("OPENAI_MODEL_CHAT"),
        },
    )

    app.state.llm_router = router
    set_llm_router(router)

    # Configure job queues (best-effort; fall back to no-op without Redis).
    job_queues: Dict[str, Queue] = {}
    redis_client: Redis | None = None
    try:
        redis_client = Redis.from_url(settings.redis_url)
        redis_client.ping()
        job_queues["embeddings"] = Queue("embeddings", connection=redis_client)
        job_queues["salience"] = Queue("salience", connection=redis_client)
        job_queues["reflection"] = Queue("reflection", connection=redis_client)
    except Exception:  # pragma: no cover - optional infrastructure
        redis_client = None

    app.state.redis = redis_client
    app.state.job_queues = job_queues

    # Configure retrieval; allow failure when Postgres is absent.
    retriever_config = RetrieverConfig(
        table_name="journal_documents",
        text_column="content",
        embedding_column="embedding",
        match_count=10,
    )
    try:
        retriever = await HybridRetriever.create(settings.postgres_dsn, config=retriever_config)
    except Exception:  # pragma: no cover - optional infrastructure
        retriever = HybridRetriever(pool=None, config=retriever_config)
    app.state.retriever = retriever

    try:
        yield
    finally:
        if getattr(app.state, "retriever", None) and app.state.retriever._pool is not None:
            await app.state.retriever._pool.close()
        redis_conn: Redis | None = getattr(app.state, "redis", None)
        if redis_conn is not None:
            redis_conn.close()


app.title = f"{SETTINGS.app_name} API"
app.router.lifespan_context = lifespan

app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(insights_router)
app.include_router(soul_routes)
app.include_router(soul_analytics_router)
app.include_router(presence_router)
app.include_router(persona_router)
app.include_router(planner_router)
app.include_router(rhythm_router)
app.include_router(breath_router)
app.include_router(events_router)
app.include_router(memory_graph_router)
app.include_router(memory_recall_router)
app.include_router(feedback_router)
app.include_router(analytics_router)
app.include_router(adjustments_router)
app.include_router(tone_router)
app.include_router(environment_router)
app.include_router(system_audit_router)
app.include_router(reflection_daily_router)
app.include_router(growth_router)
app.include_router(focus_router)
app.include_router(journey_router)
app.include_router(brain_router)
app.include_router(insight_router)
app.include_router(llm_router)
app.include_router(consolidator_router)
app.include_router(core_router)
app.include_router(router_diag, tags=["ayurveda"])
app.include_router(jr, tags=["journal"])
app.include_router(journal_turn_router)
app.include_router(admin, tags=["admin"])
app.include_router(graph_debug_router)
app.include_router(turn_v2_router)
app.include_router(narrative_router)
app.include_router(rhythm_soul_router)
app.include_router(esr_router)
app.include_router(identity_momentum_router)
app.include_router(decision_graph_router)
app.include_router(identity_timeline_router)
app.include_router(awareness_router.router)
app.include_router(intel_router.router)
app.include_router(recall_router.router)
app.include_router(soul_router.router)
app.include_router(hands_router.router)
app.include_router(memory_router.router)
app.include_router(reflection_summary_router.router)
app.include_router(narratives_router.router)
app.include_router(clarity_router.router)
app.include_router(debug_router.router)
app.include_router(alignment_router)
app.include_router(coherence_router)
app.include_router(narrative_arcs_router)
app.include_router(patterns_router)
app.include_router(inner_dialogue_router)
app.include_router(identity_state_router)
app.include_router(inner_conflict_router)
app.include_router(forecast_router)
app.include_router(nudge_router)
app.include_router(daily_reflection_router)
app.include_router(evening_closure_router)
app.include_router(morning_preview_router)
app.include_router(morning_ask_router)
app.include_router(morning_momentum_router)
app.include_router(micro_momentum_router)
app.include_router(micro_recovery_router)
app.include_router(focus_path_router)
app.include_router(mini_flow_router)
app.include_router(micro_journey_router)
app.include_router(micro_momentum_router)
app.include_router(experience_journal_router)
app.include_router(experience_weekly_router)
app.include_router(task_routing_router)
app.include_router(person_router.router)
app.include_router(person_edit_router.router)
app.include_router(person_router.router)

LOGGER.info("Printing registered routes (startup debug)")
for r in app.routes:
    LOGGER.info("route %s %s", r.methods, r.path)
    # Also print directly to stdout so Railway captures it even if logger config filters JSON logs
    print(f"{r.methods} {r.path}")


@app.get("/beats", tags=["rhythm"])
async def beats(user_id: str | None = None) -> Dict[str, Any]:
    """Return simple daily rhythm windows."""

    # TODO: read latest sleep times from body_signals; for now default 22:30–06:00
    return {"windows": calc_daily_beats()}


@app.get("/alignment", tags=["alignment"])
async def alignment(user_id: str | None = None) -> Dict[str, Any]:
    """Return an alignment score comparing intentions and actions."""

    user_uuid = await _resolve_user_id(user_id)
    score = await compute_alignment(str(user_uuid))
    drift = score < 0.70
    prompt = None
    if drift:
        prompt = (
            "Looks like you're doing a lot, but it's drifting from what you set as intention. "
            "Want to pick one micro-step that realigns today?"
        )
    return {"alignment": round(score, 3), "drift": drift, "prompt": prompt}


@app.post("/routines/today", tags=["rhythm"])
async def routines_today(body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return daily routines modulated by optional dosha vector."""

    dosha_vec = (body or {}).get("dosha_vector") if isinstance(body, dict) else None
    if not isinstance(dosha_vec, dict):
        dosha_vec = {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

    modifiers = rhythm_modifiers(dosha_vec)

    routines: Dict[str, Any] = {
        "sleep": {
            "target": "22:30–06:00",
            "wind_down_add_min": modifiers.get("wind_down_delta_min", 0),
        },
        "meals": ["08:30", "13:00", "19:30"],
        "movement": ["07:30 walk 20m", "17:30 stretch 10m"],
        "breath": ["11:30 box-breath 4x4", "16:00 4-7-8 x3"],
    }

    if modifiers.get("morning_activation") == "walk-10m":
        routines["movement"].insert(0, "06:45 brisk walk 10m")
    midday_break = modifiers.get("midday_break_min", 0)
    if isinstance(midday_break, (int, float)) and midday_break > 0:
        routines["breath"].append(f"14:30 nasal-breath {int(midday_break)}m")

    routines["dosha_vector"] = dosha_vec
    routines["modifiers"] = modifiers
    return routines


@app.post("/reflect", tags=["reflection"])
async def reflect(body: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a reflective summary backed by journal context."""

    user_id = body.get("user_id") or DEFAULT_USER_ID
    theme = (body.get("theme") or "general").strip() or "general"
    ctx = await build_reflection_context(user_id=user_id, theme=theme, limit=5)
    day_stamp = datetime.utcnow().strftime("%Y-%m-%d")
    cache_key = _cache_reflection_key(user_id, theme, day_stamp)

    system_prompt = (
        "You are Sakhi. Synthesize a kind, pragmatic reflection.\n"
        "Return 5–8 bullets, then 'Next Steps' with 3 items."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Theme: {theme}\nContext:\n{ctx}"},
    ]

    try:
        router: LLMRouter | None = getattr(app.state, "llm_router", None)
        if router is None:
            raise RuntimeError("LLM router unavailable")
        settings = get_settings()
        response = await router.chat(messages=messages, model=settings.model_reflect)
        text = (response.text or "").strip()
        if text:
            _REFLECTION_CACHE[cache_key] = text
        return {"text": text, "mode": "full"}
    except BudgetExceededError:
        cached_text = _REFLECTION_CACHE.get(cache_key)
        if cached_text:
            return {"text": cached_text, "mode": "cached"}
    except Exception:
        return {"text": _build_reflection_fallback(ctx), "mode": "lite"}

    cached_text = _REFLECTION_CACHE.get(cache_key)
    if cached_text:
        return {"text": cached_text, "mode": "cached"}

    return {"text": _build_reflection_fallback(ctx), "mode": "lite"}


@app.get("/reflect/latest", tags=["reflection"])
async def reflect_latest(kind: str = "daily", limit: int = 1, user_id: str | None = None) -> Dict[str, Any]:
    """Return the most recent stored reflections for a user."""

    if limit <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be positive")

    uid = user_id or DEFAULT_USER_ID
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, kind, theme, content, created_at
            FROM reflections
            WHERE user_id = $1 AND kind = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            uid,
            kind,
            limit,
        )

    return {"items": [dict(row) for row in rows]}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("sakhi.apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
def _force_outer_if_action(text: str, features: Dict[str, Any]) -> Dict[str, Any]:
    track = str(features.get("track", "inner"))
    if track == "outer":
        return features
    lowered = text.lower()
    markers = [
        "need to",
        "have to",
        "got to",
        "gotta",
        "must ",
        "should ",
        "plan to",
        "going to",
        "sign up",
        "join",
        "register",
        "schedule",
        "book ",
    ]
    if any(marker in lowered for marker in markers):
        features = dict(features)
        features["track"] = "outer"
        features.setdefault("intent_type", "activity")
        g_mvs = features.setdefault(
            "g_mvs",
            {
                "target_horizon": False,
                "current_position": False,
                "constraints": False,
                "criteria": False,
                "assets_blockers": False,
            },
        )
        g_mvs.setdefault("target_horizon", False)
        features.setdefault("timeline", {"horizon": "none"})
        return features
    return features
def _normalize_classification(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    def _first(value: Any) -> Any:
        if isinstance(value, list) and value:
            return value[0]
        return value

    for key in ("track", "share_type", "intent_type", "emotion", "domain"):
        if key in payload:
            payload[key] = _first(payload[key])

    timeline = payload.get("timeline")
    if isinstance(timeline, dict) and "horizon" in timeline:
        timeline["horizon"] = _first(timeline.get("horizon"))

    g_mvs = payload.get("g_mvs")
    if isinstance(g_mvs, dict):
        for g_key, g_val in list(g_mvs.items()):
            g_mvs[g_key] = bool(g_val)

    return payload
