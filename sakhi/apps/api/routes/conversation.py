from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from sakhi.apps.api.core import cache as cache_backend
from sakhi.apps.api.core.cache import cache_get, cache_set
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.tasks.generate_clarity_actions import generate_clarity_actions
from sakhi.apps.worker.tasks.progressive_task_structuring import (
    create_draft_task,
    update_task_fields,
)
from sakhi.apps.worker.utils.db import db_find, db_insert
from sakhi.apps.worker.utils.response_composer import compose_response
from sakhi.apps.worker.tasks.update_emotional_context import update_emotional_context

router = APIRouter(prefix="/conversation", tags=["conversation"])
LOGGER = logging.getLogger(__name__)
CACHE_TTL = int(os.getenv("CONVERSATION_CACHE_TTL", "1800"))


class ConversationIn(BaseModel):
    person_id: str
    message: str


class ActionIntent(BaseModel):
    is_action: bool
    action_title: Optional[str] = None
    timeline_hint: Optional[str] = None


@router.post("/message")
async def conversation_message_endpoint(payload: ConversationIn) -> Dict[str, str]:
    await handle_user_message(payload.person_id, payload.message)
    return {"status": "ok"}


async def handle_user_message(person_id: str, message: str) -> None:
    """
    Entry point: capture message, detect actions, confirm progressively.
    """
    await update_emotional_context(person_id, message)
    pending_key = _pending_action_key(person_id)
    draft_key = _draft_task_key(person_id)

    if await _maybe_record_feedback(person_id, message):
        return

    intent = await _detect_action_intent(message)

    if intent.is_action:
        reply = await compose_response(
            person_id,
            intent="confirm_task_creation",
            context={"action": intent.action_title},
        )
        await send_message(person_id, reply)
        await _cache_store(pending_key, intent.model_dump())
        return

    if _is_confirmation(message) and await _cache_exists(pending_key):
        pending_intent = await _cache_pop(pending_key) or {}
        task_id = await create_draft_task(person_id, pending_intent)
        reply = await compose_response(
            person_id,
            intent="ask_due_date",
            context={"task": pending_intent.get("action_title")},
        )
        await send_message(person_id, reply)
        await _cache_store(draft_key, {"task_id": task_id})
        await generate_clarity_actions(person_id, pending_intent.get("action_title") or "")
        return

    draft_task = await _cache_get(draft_key)
    if draft_task:
        task_id = draft_task.get("task_id")
        updated = await update_task_fields(person_id, task_id, message)
        if updated:
            reply = await compose_response(
                person_id,
                intent="task_enrichment_updated",
                context={"task_id": task_id},
            )
            await send_message(person_id, reply)
        else:
            reply = await compose_response(
                person_id,
                intent="task_enrichment_skipped",
                context={"task_id": task_id},
            )
            await send_message(person_id, reply)


async def _detect_action_intent(message: str) -> ActionIntent:
    prompt = f"""
From this user message, check if it includes a plan or action.
Return JSON: {{
  "is_action": bool,
  "action_title": str,
  "timeline_hint": str | null
}}
Text: {message}
"""
    try:
        result = await call_llm(prompt=prompt, schema=ActionIntent)
        return result
    except Exception as exc:  # pragma: no cover - LLM fallback
        LOGGER.warning("Action intent extraction failed: %s", exc)
        return ActionIntent(is_action=False)


async def send_message(person_id: str, text: str) -> None:
    """Placeholder transport hook."""
    LOGGER.info("conversation.message person_id=%s text=%s", person_id, text)


def _pending_action_key(person_id: str) -> str:
    return f"conversation:{person_id}:pending_action"


def _draft_task_key(person_id: str) -> str:
    return f"conversation:{person_id}:draft_task"


async def _cache_store(key: str, value: Dict[str, Any]) -> None:
    await cache_set(key, json.dumps(value, ensure_ascii=False), ttl=CACHE_TTL)


async def _cache_get(key: str) -> Dict[str, Any] | None:
    payload = await cache_get(key)
    if payload is None:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


async def _cache_exists(key: str) -> bool:
    return await cache_get(key) is not None


async def _cache_pop(key: str) -> Dict[str, Any] | None:
    data = await _cache_get(key)
    if data is not None:
        redis = await cache_backend._get_redis()  # type: ignore[attr-defined]
        await redis.delete(key)
    return data


def _is_confirmation(message: str) -> bool:
    normalized = (message or "").strip().lower()
    if not normalized:
        return False
    confirmations = {"yes", "yep", "sure", "sounds good", "ok", "okay", "aye", "please do", "go ahead"}
    return normalized in confirmations or normalized.startswith("yes ") or normalized.endswith(" yes")


async def _maybe_record_feedback(person_id: str, message: str) -> bool:
    lowered = (message or "").lower()
    if "helpful" not in lowered and "not helpful" not in lowered:
        return False

    reflections = db_find("reflections", {"user_id": person_id})
    reflection_id = reflections[-1].get("id") if reflections else None
    db_insert(
        "reflection_feedback",
        {
            "person_id": person_id,
            "reflection_id": reflection_id,
            "helpful": "not helpful" not in lowered,
            "comment": message,
        },
    )
    reply = await compose_response(
        person_id,
        intent="reflection_feedback_ack",
        context={"comment": message},
    )
    await send_message(person_id, reply)
    return True


__all__ = ["router", "handle_user_message"]
