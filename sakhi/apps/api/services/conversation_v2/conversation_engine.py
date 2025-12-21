from __future__ import annotations

import os
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.memory.recall import build_recall_context
from sakhi.apps.api.services.patterns.detector import build_patterns_context
from sakhi.apps.api.services.journaling.ai import generate_journaling_guidance

from .conversation_context_builder import build_conversation_context
from .conversation_reasoner import build_prompt
from .conversation_tone import decide_tone


async def generate_reply(person_id: str, user_text: str, metadata: Dict[str, Any] | None = None, behavior_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Main entry point for the conversation-v2 engine.
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

    prompt = build_prompt(user_text, context, tone, metadata=metadata_payload)
    recall_ctx = await build_recall_context(person_id, user_text)
    pattern_ctx = await build_patterns_context(person_id)
    system_ctx = f"{recall_ctx}\n\nPatterns:\n{pattern_ctx}"
    messages = [
        {"role": "system", "content": system_ctx},
        {"role": "system", "content": prompt},
    ]

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

    return {
        "reply": reply,
        "tone_blueprint": tone,
        "journaling_ai": journaling_ai,
        "behavior_profile": behavior_profile,
    }


__all__ = ["generate_reply"]
