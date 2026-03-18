from __future__ import annotations

import asyncio
import logging
import os
import time
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

# Per-user patterns context cache: {person_id: (cached_result, computed_at_monotonic)}
# TTL = 5 minutes — patterns change on long timescales, not per-turn.
_PATTERNS_CACHE: dict[str, tuple[str, float]] = {}
_PATTERNS_TTL_SECONDS = 300


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

    try:
        context = await build_conversation_context(person_id)
    except Exception as ctx_exc:
        logger.warning("[generate_reply] build_conversation_context failed for %s: %s", person_id, ctx_exc)
        context = {}
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

    emotion_label = (emotion_hint.get("label") or emotion_hint.get("emotion") or "").lower()
    if emotion_label in {"tired", "sad", "anxious", "overwhelmed", "scared", "confused", "frustrated"}:
        tone["style"] = "gentle, steady, compassionate"
        tone["pace"] = "slow"
        # Update mirroring to reflect the current emotion (overrides stored state)
        if tone.get("mirroring"):
            tone["mirroring"]["emotion"] = emotion_label
        if tone.get("empathy"):
            tone["empathy"]["mood"] = emotion_label

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
    # MVP: disabled — continuity-first prompt in build_prompt() is the primary path.
    # Adaptive pipeline was built for Ayurveda-first model; re-enable post-MVP.
    use_adaptive = os.getenv("SAKHI_USE_ADAPTIVE_RESPONSE", "0") == "1"

    # Run adaptive pipeline, recall, and patterns IN PARALLEL
    # These are independent operations that each involve embedding/DB calls.
    # When a continuity topic is active, recall and patterns are skipped entirely —
    # the continuity pack already covers topic memory and their results are discarded anyway.
    import asyncio

    _topic_active_early = bool(
        (metadata_payload.get("continuity_pack") or {}).get("topic_key")
    )

    async def _run_adaptive():
        if not (use_adaptive and should_use_adaptive_pipeline(user_text)):
            return None
        return await run_adaptive_pipeline(person_id, user_text, session_id=session_id)

    async def _run_recall():
        if _topic_active_early:
            return ""
        return await build_recall_context(person_id, user_text)

    async def _run_patterns() -> str:
        """Return cached patterns if fresh; refresh cache in background when stale."""
        if _topic_active_early:
            return ""
        cached_entry = _PATTERNS_CACHE.get(person_id)
        now = time.monotonic()
        if cached_entry is not None:
            cached_result, computed_at = cached_entry
            if now - computed_at < _PATTERNS_TTL_SECONDS:
                return cached_result  # Cache hit — no DB call this turn
            # Stale: serve cached value but kick off background refresh
            async def _bg_refresh() -> None:
                try:
                    fresh = await build_patterns_context(person_id)
                    _PATTERNS_CACHE[person_id] = (fresh or "", time.monotonic())
                except Exception:
                    pass
            asyncio.create_task(_bg_refresh())
            return cached_result
        # Cache miss — compute synchronously and populate cache
        result = await build_patterns_context(person_id)
        _PATTERNS_CACHE[person_id] = (result or "", now)
        return result or ""

    adaptive_result, recall_result, pattern_result = await asyncio.gather(
        _run_adaptive(),
        _run_recall(),
        _run_patterns(),
        return_exceptions=True,
    )

    # Process adaptive pipeline result
    if isinstance(adaptive_result, Exception):
        adaptive_error = f"Pipeline exception: {type(adaptive_result).__name__}: {str(adaptive_result)}"
        logger.warning("[generate_reply] Adaptive pipeline failed, falling back: %s", adaptive_result)
    elif adaptive_result is not None:
        adaptive_context = adaptive_result
        if adaptive_context.pipeline_stages.get("prompt"):
            adaptive_prompt = adaptive_context.adaptive_prompt
            logger.debug(
                "[generate_reply] Using adaptive pipeline: mode=%s, symptom=%s",
                adaptive_context.strategy.mode,
                adaptive_context.sense.symptom,
            )
        elif adaptive_context.errors:
            logger.warning(
                "[generate_reply] Adaptive pipeline incomplete, errors: %s",
                adaptive_context.errors,
            )

    # Process recall result
    if isinstance(recall_result, Exception):
        logger.warning("[generate_reply] build_recall_context failed for %s: %s", person_id, recall_result)
        recall_ctx = ""
    else:
        recall_ctx = recall_result or ""

    # Process patterns result
    if isinstance(pattern_result, Exception):
        logger.warning("[generate_reply] build_patterns_context failed for %s: %s", person_id, pattern_result)
        pattern_ctx = ""
    else:
        pattern_ctx = pattern_result or ""

    # Build prompts
    base_prompt = build_prompt(user_text, context, tone, metadata=metadata_payload)

    # When a continuity topic is active, the continuity pack evidence already covers
    # topic memory — skip the recall system message to avoid duplication and reduce
    # prompt noise. Only inject recall when no topic is detected.
    continuity_pack = metadata_payload.get("continuity_pack") or {}
    topic_active = bool(continuity_pack.get("topic_key"))
    if topic_active:
        system_ctx = ""
    else:
        system_ctx = recall_ctx or ""
        if pattern_ctx:
            system_ctx = f"{system_ctx}\n\nPatterns:\n{pattern_ctx}".strip()

    # Build message history for LLM context continuity
    conversation_history = metadata_payload.get("conversation_history") or []
    session_summary = metadata_payload.get("session_summary") or ""

    # Use adaptive prompt if available, otherwise use base prompt.
    # The adaptive prompt is the PRIMARY instruction set — it MUST come first
    # so the LLM treats it as the governing system prompt. The recall/pattern
    # context is supplementary data that enriches it.
    if adaptive_prompt:
        messages = [{"role": "system", "content": adaptive_prompt}]
        if system_ctx:
            messages.append({"role": "system", "content": f"[SUPPLEMENTARY MEMORY CONTEXT — use this data to personalize your response per the instructions above]\n{system_ctx}"})
    else:
        messages = [{"role": "system", "content": base_prompt}]
        if system_ctx:
            messages.append({"role": "system", "content": system_ctx})

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

    try:
        await dbexec(
            """
            UPDATE session_continuity
            SET last_interaction_ts = NOW()
            WHERE person_id = $1
            """,
            person_id,
        )
    except Exception:
        pass  # best effort — row may not exist for new users

    if reply:
        try:
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
        except Exception as st_exc:
            logger.warning("[generate_reply] short_term update failed for %s: %s", person_id, st_exc)

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
