"""Chat endpoints leveraging the shared LLM router."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from sakhi.libs.llm_router import LLMRouter
from sakhi.libs.llm_router.tool_runner import run_tool
from sakhi.libs.retrieval.recall import recall
from sakhi.libs.safety.guard import guard_messages
from sakhi.libs.schemas import ChatRequest, ChatResponse, Message, get_settings
from sakhi.libs.schemas.db import get_async_pool
from sakhi.libs.schemas.tools import CREATE_PLAN_TOOL
from sakhi.libs.security import extract_idempotency_key, run_idempotent, verify_api_key
from sakhi.libs.rhythm.beat_calc import calc_daily_beats
from sakhi.libs.conversation.classify import classify
from sakhi.libs.conversation.outer_inner import classify_outer_inner
from sakhi.libs.conversation.ack import compose_ack, AckContext, EMOTION_ALIASES
from sakhi.libs.llm.rephrase import rephrase_ack_llm
from sakhi.libs.policy import load_policy
from sakhi.libs.conversation.should_ask import score_ask
from sakhi.libs.conversation.clarify_outer import permission_prompt
from sakhi.libs.conversation.state import ConversationStateManager, mirror_outer_conversation_state
from sakhi.libs.conversation.outer_flow import (
    ensure_flow as ensure_outer_flow,
    merge_classification as merge_outer_classification,
    apply_answer as apply_outer_answer,
    prepare_next_question as prepare_outer_question,
    record_user_message,
    build_classifier_context,
    is_active as outer_flow_is_active,
)
from sakhi.libs.memory import capture_salient_memory, fetch_recent_memories
from sakhi.libs.logging_utils import colorize
from sakhi.libs.debug.narrative import build_narrative_debug
from sakhi.apps.api.services.persona import select_archetype_from_context
from sakhi.apps.worker.tasks.update_conversation_state import (
    update_conversation_state,
)
from sakhi.libs.embeddings import embed_text

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)
TOOLS = [CREATE_PLAN_TOOL]
POLICY = load_policy()
RECALL_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"what did i (?:say|write)", re.IGNORECASE),
    re.compile(r"remind me", re.IGNORECASE),
    re.compile(r"last week", re.IGNORECASE),
]


def _get_router(request: Request) -> LLMRouter:
    router = getattr(request.app.state, "llm_router", None)
    if router is None:  # pragma: no cover - guard for misconfiguration
        raise RuntimeError("LLM router is not configured")
    return router


async def _load_person_model(person_id: str | None) -> Dict[str, Any]:
    if not person_id:
        return {}
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT COALESCE(long_term, '{}'::jsonb) AS long_term
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
        )
    if not row:
        return {}
    long_term = row.get("long_term")
    if isinstance(long_term, dict):
        return dict(long_term)
    if isinstance(long_term, str):
        try:
            parsed = json.loads(long_term)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    verify_api_key(x_api_key)


async def _publish_chat_message(request: Request, user_id: str | None, content: str, conversation_id: str) -> None:
    settings = get_settings()
    if not settings.event_bridge_url:
        return
    message = {
        "schema_version": "0.1.0",
        "id": f"chat:{uuid.uuid4().hex}",
        "user_id": user_id or "anonymous",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content": {"text": content[:500], "modality": "text", "locale": _infer_locale(request)},
        "source": {"channel": "chat-api"},
        "metadata": {
            "timezone": request.headers.get("x-timezone", "UTC"),
            "extras": {"conversation_id": conversation_id},
        },
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(settings.event_bridge_url, json={"message": message})
    except httpx.HTTPError:
        logger.warning("Failed to publish chat message to pipeline", exc_info=True)


def _infer_locale(request: Request) -> str:
    header = request.headers.get("accept-language")
    if not header:
        return "en-US"
    primary = header.split(",")[0].strip()
    return primary or "en-US"


def _minutes_from_str(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _current_beat_label(request: Request) -> str:
    tz_name = request.headers.get("x-timezone", "UTC")
    try:
        now = datetime.now(ZoneInfo(tz_name))
    except (ZoneInfoNotFoundError, ValueError):
        now = datetime.now(timezone.utc)
    now_minutes = now.hour * 60 + now.minute
    windows = calc_daily_beats()
    for window in windows:
        start = _minutes_from_str(window["start"])
        end = _minutes_from_str(window["end"])
        label = window["label"]
        if start <= end:
            if start <= now_minutes < end:
                return label
        else:  # crosses midnight
            if now_minutes >= start or now_minutes < end:
                return label
    return windows[-1]["label"] if windows else "evening-calm"


_POSITIVE_WORDS = {
    "calm",
    "content",
    "excited",
    "glad",
    "grateful",
    "happy",
    "hopeful",
    "optimistic",
    "proud",
    "relieved",
}
_NEGATIVE_WORDS = {
    "anxious",
    "angry",
    "drained",
    "frustrated",
    "overwhelmed",
    "sad",
    "stressed",
    "tired",
    "upset",
    "worried",
}


def _estimate_sentiment(text: str) -> float:
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return 0.0
    pos = sum(token in _POSITIVE_WORDS for token in tokens)
    neg = sum(token in _NEGATIVE_WORDS for token in tokens)
    total = pos + neg
    if total == 0:
        return 0.0
    score = (pos - neg) / total
    return max(-1.0, min(1.0, score))


def _is_affirmative(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return False
    affirmatives = {
        "yes",
        "y",
        "yeah",
        "yup",
        "sure",
        "absolutely",
        "please do",
        "go ahead",
        "sounds good",
        "let's do it",
        "lets do it",
        "please",
    }
    if normalized in affirmatives:
        return True
    if normalized.startswith("yes ") or normalized.startswith("sure "):
        return True
    if normalized.endswith(" yes"):
        return True
    return False


def _force_outer_if_action(text: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """Heuristic to treat clearly actionable statements as outer intents."""

    track = str(features.get("track", "inner"))
    if track == "outer":
        return features

    lowered = text.lower()
    action_markers = [
        "need to",
        "need a",
        "have to",
        "got to",
        "gotta",
        "must ",
        "should ",
        "plan to",
        "going to",
        "sign up",
        "join",
        "schedule",
        "book ",
        "register",
    ]
    if any(marker in lowered for marker in action_markers):
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


@router.post("", response_model=ChatResponse, dependencies=[Depends(_require_api_key)])
async def chat(
    payload: ChatRequest,
    request: Request,
    router: LLMRouter = Depends(_get_router),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> ChatResponse:
    """Route chat requests through the shared LLM router."""

    settings = get_settings()
    provider_header = request.headers.get("X-LLM-Provider")
    provider = provider_header.lower() if provider_header else None

    async def _invoke() -> dict[str, Any]:
        raw_messages = [message.model_dump() for message in payload.messages]
        user_identifier = getattr(request.state, "user_id", None)
        user_id_str = str(user_identifier) if user_identifier is not None else None
        state_manager = ConversationStateManager(
            payload.conversation_id,
            user_id=user_id_str,
        )
        conversation_state = await state_manager.load()
        active_outer_frame = next(
            (frame for frame in conversation_state.frames if frame.name == "outer_intent" and frame.status == "active"),
            None,
        )
        outer_flow = ensure_outer_flow(active_outer_frame.metadata) if active_outer_frame else None
        awaiting_outer_step = outer_flow.get("awaiting_step") if outer_flow else None

        async def _log_decision(decision_payload_local: Dict[str, Any]) -> None:
            if not decision_payload_local:
                return
            try:
                pool = await get_async_pool()
                async with pool.acquire() as connection:
                    await connection.execute(
                        """
                        INSERT INTO request_logs(user_id, method, path, status, duration_ms, ip, headers, body)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        user_id_str,
                        "CHAT_DECISION",
                        "/chat",
                        200,
                        0,
                        None,
                        {},
                        {"conversation_id": payload.conversation_id, "extra": decision_payload_local},
                    )
            except Exception:
                logger.warning("Failed to log chat decision telemetry", exc_info=True)

        recall_system: Dict[str, str] | None = None
        memory_system: Dict[str, str] | None = None
        memory_records: List[Dict[str, Any]] = []
        person_model_context: Dict[str, Any] = {}
        last_user_text: str | None = None
        decision_payload: Dict[str, Any] | None = None
        turn_features: Dict[str, Any] | None = None
        previous_assistant = next((msg for msg in reversed(raw_messages[:-1]) if msg.get("role") == "assistant"), None)
        last_user = next((msg for msg in reversed(raw_messages) if msg.get("role") == "user"), None)
        if user_id_str:
            memory_records = await fetch_recent_memories(user_id_str, limit=3)
            if memory_records:
                formatted_memories = "\n".join(
                    f"- {item.get('summary', '')[:160]} (importance {float(item.get('importance') or 0.0):.2f})"
                    for item in memory_records
                )
                memory_system = {
                    "role": "system",
                    "content": f"Personal insights:\n{formatted_memories}",
                }
            person_model_context = await _load_person_model(user_id_str)

        previous_meta: Dict[str, Any] = {}
        if previous_assistant and isinstance(previous_assistant.get("metadata"), dict):
            previous_meta = previous_assistant.get("metadata") or {}

        base_prompt = None
        if outer_flow is not None:
            base_prompt = "You are continuing an outer intent clarification. Respond with consistent classification."
        if last_user and last_user.get("content"):
            last_user_text = last_user["content"]
            asyncio.create_task(
                _publish_chat_message(
                    request=request,
                    user_id=user_id_str,
                    content=last_user["content"],
                    conversation_id=payload.conversation_id,
                )
            )
            if user_id_str:
                asyncio.create_task(update_conversation_state(user_id_str, last_user_text))
            user_message_recorded = False
            if awaiting_outer_step and outer_flow is not None:
                apply_outer_answer(outer_flow, last_user_text)
                outer_features = _normalize_classification(dict(outer_flow.get("features", {})))
                raw_outer_features = dict(outer_features)
                track_value = "outer"
                user_message_recorded = True
            else:
                classifier_context = None
                if outer_flow is not None:
                    classifier_context = build_classifier_context(outer_flow, base_prompt=base_prompt)
                query_text = last_user_text if classifier_context is None else f"{classifier_context}\n\nUser: {last_user_text}"
                raw_outer_features = await classify_outer_inner(query_text, router=router)
                raw_outer_features = _normalize_classification(raw_outer_features)
                logger.info(
                    colorize("LLM classify response", "red"),
                    extra={
                        "event": "outer_classification",
                        "conversation_id": payload.conversation_id,
                        "user_id": user_id_str,
                        "text": last_user_text,
                        "context": classifier_context,
                        "result": raw_outer_features,
                    },
                )
                outer_features = _force_outer_if_action(last_user_text, raw_outer_features)
                if outer_flow is not None:
                    merged_features = merge_outer_classification(outer_flow, raw_outer_features)
                    outer_features = dict(merged_features)
                else:
                    outer_features = dict(raw_outer_features)

            turn_features = dict(outer_features)
            if memory_records:
                turn_features["memory_ids"] = [item.get("id") for item in memory_records if item.get("id")]

            if not (awaiting_outer_step and outer_flow is not None):
                track_value = str(outer_features.get("track", raw_outer_features.get("track", "inner")))
            else:
                track_value = "outer"

            if outer_flow is not None and outer_flow_is_active(outer_flow):
                track_value = "outer"
                outer_features = dict(outer_flow.get("features", outer_features))
                turn_features = dict(outer_features)
                if memory_records:
                    turn_features["memory_ids"] = [item.get("id") for item in memory_records if item.get("id")]
            elif previous_meta.get("flow") == "outer_clarify" and track_value == "inner":
                track_value = "outer"
            logger.info(
                colorize("Outer track decision", "magenta"),
                extra={
                    "event": "outer_track_decision",
                    "conversation_id": payload.conversation_id,
                    "user_id": user_id_str,
                    "track": track_value,
                    "awaiting_step": awaiting_outer_step,
                },
            )
            beat_label_outer = _current_beat_label(request)
            if track_value == "outer":
                emotion_value = outer_features.get("emotion")
                if isinstance(emotion_value, str) and emotion_value.strip():
                    raw_emotion = emotion_value.lower().strip()
                else:
                    sentiment_value = outer_features.get("sentiment")
                    if isinstance(sentiment_value, (int, float)):
                        if sentiment_value > 0.3:
                            raw_emotion = "positive"
                        elif sentiment_value < -0.3:
                            raw_emotion = "heavy"
                        else:
                            raw_emotion = "neutral"
                    else:
                        raw_emotion = "neutral"
                normalized_emotion = EMOTION_ALIASES.get(raw_emotion, raw_emotion)

                outer_frame = await state_manager.ensure_frame(
                    "outer_intent",
                    slots={
                        "timeline": outer_features.get("timeline"),
                        "g_mvs": outer_features.get("g_mvs"),
                        "intent_type": outer_features.get("intent_type"),
                    },
                    metadata={
                        "features": outer_features,
                        "memories": [item.get("id") for item in memory_records if item.get("id")],
                        "conversation_id": payload.conversation_id,
                    },
                )
                outer_flow = ensure_outer_flow(outer_frame.metadata)
                merge_outer_classification(outer_flow, outer_features)
                if not user_message_recorded:
                    record_user_message(outer_flow, last_user_text)

                followup_question, awaiting_outer_step = prepare_outer_question(outer_flow)
                if not followup_question:
                    if not outer_flow.get("permission_offered"):
                        followup_question = permission_prompt()
                        outer_flow["permission_offered"] = True
                        outer_flow["awaiting_step"] = "permission"
                    else:
                        outer_flow["ready_for_plan"] = True
                else:
                    outer_flow["permission_offered"] = False

                outer_features = dict(outer_flow.get("features", outer_features))
                turn_features = dict(outer_features)
                if memory_records:
                    turn_features["memory_ids"] = [item.get("id") for item in memory_records if item.get("id")]

                user_style = getattr(payload, "user_style", None)

                ack_text = compose_ack(
                    POLICY,
                    AckContext(
                        sentiment=normalized_emotion,
                        user_style=user_style,
                        allow_llm=True,
                    ),
                    llm_rephrase_fn=rephrase_ack_llm,
                )

                assistant_message = Message(
                    role="assistant",
                    content=f"{ack_text} {followup_question}".strip() if followup_question else ack_text,
                    metadata={
                        "flow": "outer_clarify",
                        "outer_features": outer_features,
                        "emotion_raw": raw_emotion,
                        "emotion_norm": normalized_emotion,
                        "ack_text": ack_text,
                        "asked": followup_question,
                        "outer_flow": outer_flow,
                    },
                )

                await _log_decision(
                    {
                        "dialog_act": "OUTER_ACK_AND_CLARIFY",
                        "decision": "ASK",
                        "emotion_raw": raw_emotion,
                        "emotion_norm": normalized_emotion,
                        "ack": ack_text,
                        "beat": beat_label_outer,
                    }
                )

                turn_metadata = {
                    "kind": "outer_clarify",
                    "emotion": normalized_emotion,
                    "question": followup_question,
                    "answer": last_user_text,
                    "outer_flow": outer_flow,
                    "memories": [item.get("id") for item in memory_records if item.get("id")],
                    "conversation_id": payload.conversation_id,
                }
                await state_manager.record_turn(
                    user_message=last_user_text,
                    assistant_message=assistant_message.content,
                    metadata=turn_metadata,
                )
                if user_id_str:
                    fallback_conv_id = f"journal:{user_id_str}"
                    await mirror_outer_conversation_state(
                        user_id=user_id_str,
                        source_conversation_id=payload.conversation_id,
                        target_conversation_id=fallback_conv_id,
                        slots=dict(outer_frame.slots),
                        metadata=dict(outer_frame.metadata),
                        user_message=last_user_text,
                        assistant_message=assistant_message.content,
                    )
                asyncio.create_task(
                    capture_salient_memory(
                        router=router,
                        user_id=user_id_str,
                        conversation_id=payload.conversation_id,
                        user_text=last_user_text,
                        assistant_text=assistant_message.content,
                        outer_features=outer_features,
                    )
                )

                return ChatResponse(
                    conversation_id=payload.conversation_id,
                    message=assistant_message,
                    usage={"provider": "outer-flow", "mode": "emotion-aware-clarify"},
                ).model_dump()
            elif track_value == "inner":
                emotion_label = outer_features.get("emotion") or "present"
                inner_question = "If you’d like to keep exploring this, just say the word."
                inner_text = f"Noted. Feels {emotion_label}. {inner_question}".strip()
                narrative_payload_inner = build_narrative_debug(
                    last_user_text,
                    outer_features,
                    "ACK",
                    asked=inner_question,
                )
                assistant_message = Message(
                    role="assistant",
                    content=inner_text,
                    metadata={
                        "mode": "inner_ack",
                        "narrative": narrative_payload_inner,
                    },
                )
                await _log_decision(
                    {
                        "dialog_act": "INNER_ACK",
                        "ask_score": 0.0,
                        "decision": "ACK",
                        "beat": beat_label_outer,
                    }
                )
                await state_manager.ensure_frame(
                    "inner_reflection",
                    metadata={
                        "emotion": emotion_label,
                        "features": outer_features,
                        "memories": [item.get("id") for item in memory_records if item.get("id")],
                    },
                )
                await state_manager.record_turn(
                    user_message=last_user_text,
                    assistant_message=inner_text,
                    metadata={
                        "kind": "inner_ack",
                        "emotion": emotion_label,
                        "memories": [item.get("id") for item in memory_records if item.get("id")],
                    },
                )
                asyncio.create_task(
                    capture_salient_memory(
                        router=router,
                        user_id=user_id_str,
                        conversation_id=payload.conversation_id,
                        user_text=last_user_text,
                        assistant_text=inner_text,
                        outer_features=outer_features,
                    )
                )
                response_model = ChatResponse(
                    conversation_id=payload.conversation_id,
                    message=assistant_message,
                    usage={"provider": "inner-flow", "mode": "ack"},
                )
                return response_model.model_dump()

            content = last_user["content"]
            if any(pattern.search(content) for pattern in RECALL_PATTERNS):
                embedding_vec: List[float] | None = None
                try:
                    embedding_vec = await embed_text(content)
                except Exception:  # pragma: no cover - embedding optional
                    logger.warning("chat recall embedding failed", exc_info=True)
                    embedding_vec = None

                try:
                    recall_items = await recall(user_id_str, content, k=5, embedding=embedding_vec)
                    if recall_items:
                        formatted = "\n".join(f"- {item.get('snippet', '')}" for item in recall_items)
                        recall_system = {
                            "role": "system",
                            "content": f"Relevant past notes:\n{formatted}",
                        }
                except Exception:  # pragma: no cover - recall fallback
                    recall_system = None

        messages = await guard_messages(user_id_str, raw_messages)
        if recall_system and any(msg.get("role") == "user" for msg in messages):
            insert_at = 1 if messages and messages[0].get("role") == "system" else 0
            messages.insert(insert_at, recall_system)
        if memory_system and any(msg.get("role") == "user" for msg in messages):
            insert_at = 1 if messages and messages[0].get("role") == "system" else 0
            messages.insert(insert_at, memory_system)
        if not any(msg.get("role") == "user" for msg in messages):
            assistant_fallback = next((msg for msg in messages if msg.get("role") == "assistant"), None)
            assistant_message = Message(
                role="assistant",
                content=(assistant_fallback or {}).get("content", "I can't help with that request."),
            )
            response_model = ChatResponse(
                conversation_id=payload.conversation_id,
                message=assistant_message,
                usage={"provider": "guard", "mode": "refusal"},
            )
            return response_model.model_dump()

        tools: list[dict[str, Any]] = list(TOOLS)
        if payload.tools:
            tools.extend(tool for tool in payload.tools if isinstance(tool, dict))  # type: ignore[list-item]

        persona = select_archetype_from_context(person_model_context)
        response = await router.chat(
            messages=messages,
            model=settings.model_chat,
            provider=provider,
            tools=tools,
            persona=persona,
        )
        logger.info(
            colorize("LLM chat response", "red"),
            extra={
                "event": "llm_chat_response",
                "conversation_id": payload.conversation_id,
                "user_id": user_id_str,
                "text": response.text or "",
                "messages": messages,
                "raw_response": getattr(response, "raw", None),
                "provider": response.provider,
            },
        )

        tool_payloads: list[dict[str, Any]] = []
        initial_tool_calls = response.tool_calls or []
        if initial_tool_calls:
            for call in initial_tool_calls:
                function = call.get("function")
                name = call.get("name")
                if not name and isinstance(function, dict):
                    name = function.get("name")

                raw_arguments: Any = call.get("arguments")
                if raw_arguments is None and isinstance(function, dict):
                    raw_arguments = function.get("arguments")

                if isinstance(raw_arguments, str):
                    try:
                        arguments = json.loads(raw_arguments)
                    except json.JSONDecodeError as exc:
                        logger.warning(
                            colorize("Tool argument parse error", "yellow"),
                            extra={
                                "event": "tool_arguments_error",
                                "conversation_id": payload.conversation_id,
                                "user_id": user_id_str,
                                "raw_arguments": raw_arguments,
                                "error": str(exc),
                            },
                        )
                        arguments = {}
                elif isinstance(raw_arguments, dict):
                    arguments = raw_arguments
                else:
                    arguments = {}

                tool_name = name or "unknown"
                try:
                    result = run_tool(tool_name, arguments)
                except Exception as exc:  # pragma: no cover - defensive guard
                    result = {"error": f"Tool execution failed: {exc}"}
                tool_payloads.append({"name": tool_name, "result": result})

            messages = messages + [
                {"role": "assistant", "content": f"TOOL_RESULTS: {tool_payloads}"},
            ]
            response = await router.chat(
                messages=messages,
                model=settings.model_chat,
                provider=provider,
                persona=persona,
            )
            logger.info(
                colorize("LLM chat follow-up response", "red"),
                extra={
                    "event": "llm_chat_response",
                    "conversation_id": payload.conversation_id,
                    "user_id": user_id_str,
                    "text": response.text or "",
                    "messages": messages,
                    "raw_response": getattr(response, "raw", None),
                    "provider": response.provider,
                },
            )

        usage = dict(response.usage or {})
        usage["provider"] = response.provider or provider or "unknown"
        if response.cost is not None:
            usage["cost"] = response.cost

        metadata = None
        if initial_tool_calls or tool_payloads:
            metadata = {}
            if initial_tool_calls:
                metadata["tool_calls"] = initial_tool_calls
            if tool_payloads:
                metadata["tool_results"] = tool_payloads

        assistant_message = Message(role="assistant", content=response.text or "", metadata=metadata)

        if last_user_text and decision_payload is None:
            classification = await classify(last_user_text, router=router)
            dialog_act = str(classification.get("dialog_act", "SHARE"))
            raw_gaps = classification.get("info_gaps") or []
            info_gaps = [gap for gap in raw_gaps if isinstance(gap, str)]
            sentiment = _estimate_sentiment(last_user_text)
            beat_label = _current_beat_label(request)
            ask_score = score_ask(
                dialog_act,
                info_gaps,
                sentiment,
                beat_label,
                len(last_user_text),
            )
            ask_threshold = POLICY.get("ask_threshold", 0.5)
            decision = "ASK" if ask_score >= ask_threshold else "ACK"
            if decision != "ASK" and (
                classification.get("goal_detected")
                or dialog_act in {"PLAN", "DECIDE"}
            ):
                decision = "DO"
            decision_payload = {
                "dialog_act": dialog_act,
                "ask_score": round(float(ask_score), 4),
                "decision": decision,
                "beat": beat_label,
            }

        metadata_payload = assistant_message.metadata or {}
        if narrative_debug is not None:
            metadata_payload.setdefault("narrative", narrative_debug)
            assistant_message.metadata = metadata_payload

        if last_user_text:
            await state_manager.ensure_frame(
                "adaptive_chat",
                metadata={
                    "decision": decision_payload,
                    "features": turn_features,
                    "memories": [item.get("id") for item in memory_records if item.get("id")],
                },
            )
            await state_manager.record_turn(
                user_message=last_user_text,
                assistant_message=assistant_message.content,
                metadata={
                    "kind": "adaptive_response",
                    "decision": (decision_payload or {}).get("decision"),
                    "memories": [item.get("id") for item in memory_records if item.get("id")],
                },
            )
            asyncio.create_task(
                capture_salient_memory(
                    router=router,
                    user_id=user_id_str,
                    conversation_id=payload.conversation_id,
                    user_text=last_user_text,
                    assistant_text=assistant_message.content,
                    outer_features=turn_features,
                )
            )

        response_model = ChatResponse(
            conversation_id=payload.conversation_id,
            message=assistant_message,
            usage=usage,
        )

        if decision_payload:
            await _log_decision(decision_payload)

        return response_model.model_dump()

    headers = {k: v for k, v in request.headers.items() if isinstance(v, str)}
    key = idempotency_key or extract_idempotency_key(headers)
    if not key:
        try:
            payload_dict = await _invoke()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return ChatResponse.model_validate(payload_dict)

    try:
        payload_dict = await run_idempotent(
            headers={"idempotency-key": key},
            handler=_invoke,
            event_type="chat_request",
            payload={"conversation_id": payload.conversation_id},
        )
        return ChatResponse.model_validate(payload_dict)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - optional infrastructure
        logger.warning("Idempotent execution failed, falling back to direct call: %s", exc)
        try:
            payload_dict = await _invoke()
        except ValueError as inner_exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(inner_exc)) from inner_exc
        return ChatResponse.model_validate(payload_dict)
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
