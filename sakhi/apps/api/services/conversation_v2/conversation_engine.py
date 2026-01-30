from __future__ import annotations

import logging
import os
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.memory.recall import build_recall_context
from sakhi.apps.api.services.patterns.detector import build_patterns_context
from sakhi.apps.api.services.journaling.ai import generate_journaling_guidance
from sakhi.apps.api.services.response import (
    run_adaptive_pipeline,
    should_use_adaptive_pipeline,
)

from .conversation_context_builder import build_conversation_context
from .conversation_reasoner import build_prompt
from .conversation_tone import decide_tone

logger = logging.getLogger(__name__)


async def generate_reply(
    person_id: str,
    user_text: str,
    metadata: Dict[str, Any] | None = None,
    behavior_profile: Dict[str, Any] | None = None,
    *,
    session_id: str = "",
    return_debug: bool = False,
) -> Dict[str, Any]:
    """
    Main entry point for the conversation-v2 engine.

    Args:
        person_id: User ID
        user_text: User's message
        metadata: Additional context metadata
        behavior_profile: Behavior profile for personalization
        session_id: Session ID for loading session_summary in adaptive pipeline
        return_debug: Whether to include debug info in response
    """

    metadata_payload: Dict[str, Any] = dict(metadata or {})
    if behavior_profile:
        metadata_payload["behavior_profile"] = behavior_profile

    context = await build_conversation_context(person_id)
    tone = decide_tone(context, behavior_profile)
    rhythm_trigger = metadata_payload.get("rhythm_triggers") or {}
    meta_trigger = metadata_payload.get("meta_reflection_triggers") or {}
    emotion_hint = metadata_payload.get("emotion") or {}

    if rhythm_trigger.get("applied"):
        tone["style"] = "gentle, restorative, warm"
        tone["pace"] = "slow"
        tone["concise"] = False
    elif meta_trigger.get("applied"):
        tone["style"] = "reflective, spacious, thoughtful"
        tone["pace"] = "balanced"

    emotion_label = (emotion_hint.get("label") or "").lower()
    if emotion_label in {"tired", "sad", "anxious", "overwhelmed"}:
        tone["style"] = "gentle, steady, compassionate"
        tone["pace"] = "slow"

    journaling_ai = None
    try:
        summary_hint: str | None = None
        mind_state = context.get("mind") or {}
        if isinstance(mind_state, dict):
            summary_hint = mind_state.get("summary") or mind_state.get("focus")
        if not summary_hint:
            short_term = context.get("short_term") or {}
            texts = short_term.get("texts") if isinstance(short_term, dict) else None
            if isinstance(texts, list) and texts:
                summary_hint = texts[-1]
        mood_hint = emotion_label or tone.get("mirroring", {}).get("emotion") or "neutral"
        journaling_ai = generate_journaling_guidance(
            user_id=person_id,
            text=user_text,
            tone={"mood": mood_hint},
            context=context,
            summary=summary_hint,
        )
        context["journaling_ai"] = journaling_ai
        metadata_payload["journaling_ai"] = journaling_ai
    except Exception:
        journaling_ai = None

    # Check if adaptive pipeline should be used
    adaptive_context = None
    adaptive_prompt = None
    adaptive_error = None  # Track top-level errors
    use_adaptive = os.getenv("SAKHI_USE_ADAPTIVE_RESPONSE", "1") == "1"

    if use_adaptive and should_use_adaptive_pipeline(user_text):
        try:
            adaptive_context = await run_adaptive_pipeline(person_id, user_text, session_id=session_id)
            if adaptive_context.pipeline_stages.get("prompt"):
                adaptive_prompt = adaptive_context.adaptive_prompt
                logger.debug(
                    "[generate_reply] Using adaptive pipeline: mode=%s, symptom=%s",
                    adaptive_context.strategy.mode,
                    adaptive_context.sense.symptom,
                )
            elif adaptive_context.errors:
                # Pipeline ran but didn't complete - errors are already in context
                logger.warning(
                    "[generate_reply] Adaptive pipeline incomplete, errors: %s",
                    adaptive_context.errors,
                )
        except Exception as e:
            adaptive_error = f"Pipeline exception: {type(e).__name__}: {str(e)}"
            logger.warning("[generate_reply] Adaptive pipeline failed, falling back: %s", e)
            adaptive_prompt = None

    # Build prompts
    base_prompt = build_prompt(user_text, context, tone, metadata=metadata_payload)
    recall_ctx = await build_recall_context(person_id, user_text)
    pattern_ctx = await build_patterns_context(person_id)
    system_ctx = f"{recall_ctx}\n\nPatterns:\n{pattern_ctx}"

    # Build message history for LLM context continuity
    conversation_history = metadata_payload.get("conversation_history") or []
    session_summary = metadata_payload.get("session_summary") or ""

    # Use adaptive prompt if available, otherwise use base prompt
    if adaptive_prompt:
        messages = [
            {"role": "system", "content": system_ctx},
            {"role": "system", "content": adaptive_prompt},
        ]
    else:
        messages = [
            {"role": "system", "content": system_ctx},
            {"role": "system", "content": base_prompt},
        ]

    # Add session summary as compressed older context (if available)
    # This gives the LLM awareness of earlier parts of the conversation
    # The summary contains semantic markers for pronouns, topics, and entities
    if session_summary:
        context_instruction = """[Earlier Conversation Context]
Use this context to understand references in the recent conversation:
- When user says "she/he/they", refer to People & Relationships
- When user says "it/that/the project", refer to Topics & References
- Be aware of the Emotional Thread and Open Threads

"""
        messages.append({
            "role": "system",
            "content": context_instruction + session_summary,
        })

    # Add recent conversation history as alternating user/assistant messages
    # These are verbatim for immediate context and natural flow
    for turn in conversation_history:
        role = turn.get("role", "user")
        text = turn.get("text", "")
        if text:
            # Map sakhi/assistant role to 'assistant' for OpenAI API compatibility
            # DB stores 'assistant', but we also handle legacy 'sakhi' for backwards compat
            llm_role = "assistant" if role in ("sakhi", "assistant") else "user"
            messages.append({"role": llm_role, "content": text})

    # Add current user message
    messages.append({"role": "user", "content": user_text})

    model_name = os.getenv("MODEL_CONVERSATION", "gpt-4o-mini")
    response = await call_llm(
        messages=messages,
        person_id=person_id,
        model=model_name,
    )
    reply = response if isinstance(response, str) else (response.get("text") or "")
    reply = reply.strip()

    await dbexec(
        """
        UPDATE session_continuity
        SET last_interaction_ts = NOW()
        WHERE person_id = $1
        """,
        person_id,
    )

    if reply:
        await dbexec(
            """
            UPDATE personal_model
            SET short_term = jsonb_set(
                normalized_short_term,
                '{texts}',
                COALESCE(normalized_short_term->'texts','[]'::jsonb) || to_jsonb($2::text),
                true
            ),
            updated_at = NOW()
            FROM (
                SELECT
                    CASE
                        WHEN jsonb_typeof(COALESCE(short_term, '{}'::jsonb)) = 'object'
                            THEN COALESCE(short_term, '{}'::jsonb)
                        ELSE '{}'::jsonb
                    END AS normalized_short_term
                FROM personal_model
                WHERE person_id = $1
                FOR UPDATE
            ) AS st
            WHERE person_id = $1
            """,
            person_id,
            reply,
        )

    response_payload: Dict[str, Any] = {
        "reply": reply,
        "tone_blueprint": tone,
        "journaling_ai": journaling_ai,
        "behavior_profile": behavior_profile,
    }

    # Include adaptive context metadata if used
    if adaptive_context:
        response_payload["adaptive_response"] = adaptive_context.to_metadata()
    elif adaptive_error:
        # Pipeline failed completely - surface the error
        response_payload["adaptive_response"] = {
            "pipeline_stages": {},
            "errors": {"pipeline": adaptive_error},
            "warnings": [],
        }

    if return_debug:
        response_payload["debug"] = {
            "prompt": adaptive_prompt or base_prompt,
            "base_prompt": base_prompt,
            "adaptive_prompt": adaptive_prompt,
            "system_context": system_ctx,
            "messages": messages,
            "metadata": metadata_payload,
            "context_snapshot": context,
            "recall_context": recall_ctx,
            "pattern_context": pattern_ctx,
            "tone_blueprint": tone,
            "adaptive_context": adaptive_context.to_metadata() if adaptive_context else None,
            "adaptive_error": adaptive_error,  # Top-level pipeline error
            "used_fallback": adaptive_prompt is None and use_adaptive,  # Did we fall back?
        }
    return response_payload


__all__ = ["generate_reply"]
