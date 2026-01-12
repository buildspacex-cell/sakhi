from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.reflection_inquiry.context import assemble_inquiry_context
from sakhi.apps.api.services.reflection_inquiry.dao import (
    embed_and_store_all,
    insert_inquiry_turn,
)
from sakhi.apps.api.services.reflection_inquiry.router import classify_inquiry_mode

BANNED_TAXONOMY = [
    "soul",
    "identity momentum",
    "rhythm state",
    "emotion state",
    "longitudinal state",
    "suppression",
]

BANNED_VOCABULARY = [
    "indicates",
    "indicate",
    "suggests",
    "suggest",
    "reflects",
    "reflect",
    "underlying",
    "distribution",
    "allocation",
    "management of strain",
    "alignment",
    "coherence",
    "grounding",
    "trajectory",
    "momentum",
    "pattern recognition",
    "therefore",
    "as a result",
]

BANNED_REFERENCES = [r"\bdata\b", r"\bsignals?\b", r"\bstates?\b"]
BANNED_BULLETS = ["\n- ", "\n* ", "\n•"]
MAX_WORDS_PER_SENTENCE = 20


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def validate_answer(text: str) -> Dict[str, Any]:
    """
    Ensure inquiry answers follow plain-language constraints.
    """
    fail_reasons: List[str] = []
    if not text or not text.strip():
        return {"passed": False, "fail_reasons": ["empty answer"]}

    sentences = _split_sentences(text)
    if len(sentences) < 3:
        fail_reasons.append("requires at least three sentences (acknowledge, restate, agency)")
    for sentence in sentences:
        if len(sentence.split()) > MAX_WORDS_PER_SENTENCE:
            fail_reasons.append("sentence length above 20 words")
            break

    lower = text.lower()
    for term in BANNED_TAXONOMY:
        if term in lower:
            fail_reasons.append("internal taxonomy leaked")
            break
    for term in BANNED_VOCABULARY:
        if term in lower:
            fail_reasons.append("banned vocabulary present")
            break
    for pattern in BANNED_REFERENCES:
        if re.search(pattern, lower):
            fail_reasons.append("referenced data/signals/states")
            break
    for bullet in BANNED_BULLETS:
        if bullet in text:
            fail_reasons.append("bullets are not allowed")
            break

    return {"passed": not fail_reasons, "fail_reasons": fail_reasons}


async def _render_answer(context: Dict[str, Any], mode: str, question_text: str) -> str:
    reflection = context.get("reflection") or {}
    states = context.get("states") or {}
    evidence = context.get("evidence") or {}
    recent_questions = context.get("recent_questions") or []

    system_prompt = (
        "You are responding to a user's question about an internal reflection.\n"
        "Sound like a thoughtful friend explaining what they noticed, in simple everyday language.\n"
        "You may use internal signals to ground your answer, but you must NOT reference system concepts, state names, or analytical terms in your response. Speak in everyday language only.\n"
        "Ignore internal taxonomy. Do not mention soul, identity momentum, rhythm state, emotion state, longitudinal state, suppression logic, or scores.\n"
        "Language: short sentences (max 18-20 words), one idea per sentence, concrete words only, no academic phrasing, no metaphors, no motivational language, no future predictions.\n"
        "Banned words/phrases: indicates, suggests, reflects, underlying, distribution, allocation, management of strain, alignment, coherence, grounding, trajectory, momentum, pattern recognition, therefore, as a result.\n"
        "Do not reference data, signals, or states. Do not use bullets or labels. Plain paragraphs only.\n"
        "Required flow: acknowledge the question; restate the observation in simpler words; return agency to the user.\n"
        "Question handling:\n"
        "- If asked 'why did you say this?': point to repetition across days and time, no causes, no psychology.\n"
        "- If asked 'can you explain more?': describe what showed up (like when activity happened), never why.\n"
        "- If asked 'what does this mean?': say it does not mean anything by itself and the user decides meaning.\n"
        "- If asked 'what should I do?': say you did not offer advice; if they want suggestions, they can ask explicitly. Do not give advice unless explicitly permitted.\n"
        "Example tone:\n"
        "Most days felt busy.\n"
        "A lot happened in the evenings.\n"
        "This showed up more than once.\n"
        "That’s why it was mentioned.\n"
        "Keep the answer brief and human."
    )

    mode_instructions = {
        "explain": (
            "Acknowledge the question. Restate that the point was mentioned because it kept showing up across days and time slots. "
            "Avoid causes or psychology. No advice."
        ),
        "meaning": (
            "Acknowledge the question. Say it does not mean anything by itself; it just stayed consistent. "
            "Return agency to the user."
        ),
        "advice": (
            "Do not provide advice. Say you did not offer advice in the reflection. "
            "Invite the user to ask explicitly if they want suggestions. Keep the boundary firm."
        ),
    }

    user_content = {
        "question": question_text,
        "mode": mode,
        "reflection": reflection,
        "states": states,
        "evidence": {
            "journals": evidence.get("journals", []),
            "episodic": evidence.get("episodic", []),
        },
        "recent_questions": recent_questions,
    }

    response = await call_llm(
        messages=[
            {"role": "system", "content": f"{system_prompt} {mode_instructions.get(mode, '')}"},
            {"role": "user", "content": json.dumps(user_content, default=str)},
        ]
    )
    return (response or "").strip()


async def answer_reflection_inquiry(
    *,
    person_id: str,
    reflection_id: str,
    question_text: str,
    window_days: int = 7,
    reflection_kind: str = "foundation_narration",
) -> Dict[str, Any]:
    # Build context and classify mode
    context = await assemble_inquiry_context(
        person_id=person_id,
        reflection_id=reflection_id,
        window_days=window_days,
        question_text=question_text,
    )
    mode = classify_inquiry_mode(question_text)

    # Render answer
    answer_text = await _render_answer(context, mode, question_text)
    validation = validate_answer(answer_text)
    if not validation["passed"]:
        raise RuntimeError(f"Answer failed validation: {', '.join(validation['fail_reasons'])}")

    sources_json = {
        "states_present": [k for k, v in (context.get("states") or {}).items() if v],
        "evidence_counts": {
            "journals": len(context.get("evidence", {}).get("journals") or []),
            "episodic": len(context.get("evidence", {}).get("episodic") or []),
        },
        "recent_questions": len(context.get("recent_questions") or []),
        "reflection_anchor": context.get("reflection", {}).get("timeframe"),
    }

    # Persist turn + embeddings (best-effort)
    turn_id = await insert_inquiry_turn(
        person_id=person_id,
        reflection_id=reflection_id,
        reflection_kind=reflection_kind,
        window_days=window_days,
        question_text=question_text,
        answer_text=answer_text,
        answer_mode=mode,
        sources_json=sources_json,
    )
    await embed_and_store_all(
        turn_id=turn_id,
        person_id=person_id,
        question_text=question_text,
        answer_text=answer_text,
    )

    return {
        "turn_id": turn_id,
        "answer_text": answer_text,
        "answer_mode": mode,
        "sources_json": sources_json,
    }
