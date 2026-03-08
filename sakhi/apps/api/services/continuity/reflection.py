from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.core.llm import get_router
from sakhi.apps.api.services.governance.service import log_turn_event
from sakhi.apps.api.services.continuity.service import (
    CONTINUITY_SCOPE,
    get_continuity_arc,
)

LOGGER = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"[a-z0-9']+")
_TOPIC_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "about",
    "around",
    "current",
    "phase",
    "thread",
    "started",
    "currently",
    "return",
}
_DEEP_REFLECTION_SYSTEM = """You are Sakhi - a friend who gets this person deeply.
Speak naturally, warm and direct. Keep it grounded in the packet evidence.
Do not use therapy-speak or Ayurvedic jargon.
Do not introduce themes that are not explicitly present in the packet.
Follow the response contract exactly."""


async def create_deep_reflection_job(
    person_id: str,
    topic_key: str,
    *,
    window: str = "3650d",
    mode: str = "topic_reflection",
    user_query: str | None = None,
) -> dict[str, Any]:
    normalized_mode = "deep_answer" if str(mode).strip().lower() == "deep_answer" else "topic_reflection"
    cleaned_query = str(user_query or "").strip() or None
    reflection_id = str(uuid4())
    await dbexec(
        """
        INSERT INTO deep_reflections (
            id, person_id, topic_key, status, inputs_hash, created_at, updated_at
        )
        VALUES ($1::uuid, $2::uuid, $3, 'queued', '', now(), now())
        """,
        reflection_id,
        person_id,
        topic_key,
    )
    asyncio.create_task(
        _run_deep_reflection_job(
            reflection_id=reflection_id,
            person_id=person_id,
            topic_key=topic_key,
            window=window,
            mode=normalized_mode,
            user_query=cleaned_query,
        )
    )
    await log_turn_event(
        person_id=person_id,
        action="deep_reflection_run",
        event_type="observed",
        actor="system",
        data={
            "reflection_id": reflection_id,
            "topic_key": topic_key,
            "window": window,
            "mode": normalized_mode,
            "user_query_present": bool(cleaned_query),
        },
        reason="deep reflection queued",
    )
    return {
        "reflection_id": reflection_id,
        "status": "queued",
        "topic_key": topic_key,
        "window": window,
        "mode": normalized_mode,
        "user_query_present": bool(cleaned_query),
    }


async def get_deep_reflection_status(reflection_id: str, person_id: str) -> dict[str, Any]:
    row = await dbfetch(
        """
        SELECT id, person_id, topic_key, status, error, created_at, updated_at
        FROM deep_reflections
        WHERE id = $1::uuid
          AND person_id = $2::uuid
        """,
        reflection_id,
        person_id,
        one=True,
    )
    if not row:
        raise LookupError("Deep reflection not found")
    return {
        "reflection_id": str(row.get("id")),
        "person_id": str(row.get("person_id")),
        "topic_key": str(row.get("topic_key") or ""),
        "status": str(row.get("status") or "queued"),
        "error": row.get("error"),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


async def get_deep_reflection_result(reflection_id: str, person_id: str) -> dict[str, Any]:
    row = await dbfetch(
        """
        SELECT id, person_id, topic_key, status, result_json, error
        FROM deep_reflections
        WHERE id = $1::uuid
          AND person_id = $2::uuid
        """,
        reflection_id,
        person_id,
        one=True,
    )
    if not row:
        raise LookupError("Deep reflection not found")
    status = str(row.get("status") or "queued")
    if status != "done":
        return {
            "reflection_id": str(row.get("id")),
            "topic_key": str(row.get("topic_key") or ""),
            "status": status,
            "error": row.get("error"),
        }

    result = _parse_json_object(row.get("result_json"))
    await log_turn_event(
        person_id=str(row.get("person_id")),
        action="deep_reflection_viewed",
        event_type="observed",
        actor="system",
        data={"reflection_id": reflection_id, "topic_key": str(row.get("topic_key") or "")},
        reason="deep reflection viewed",
    )
    return {
        "reflection_id": str(row.get("id")),
        "topic_key": str(row.get("topic_key") or ""),
        "status": status,
        "result": result,
    }


async def _run_deep_reflection_job(
    *,
    reflection_id: str,
    person_id: str,
    topic_key: str,
    window: str,
    mode: str,
    user_query: str | None,
) -> None:
    try:
        await dbexec(
            """
            UPDATE deep_reflections
            SET status = 'running', updated_at = now()
            WHERE id = $1::uuid
            """,
            reflection_id,
        )
        arc_payload = await get_continuity_arc(
            person_id,
            topic_key,
            window=window,
            debug=True,
            log_access=False,
            scope=CONTINUITY_SCOPE,
        )
        deterministic = _build_reflection_result(
            arc_payload,
            mode=mode,
            user_query=user_query,
        )
        result = await _enrich_reflection_with_llm(
            person_id=person_id,
            topic_key=topic_key,
            arc_payload=arc_payload,
            deterministic=deterministic,
            mode=mode,
            user_query=user_query,
        )
        await _persist_deep_reflection_done(reflection_id, result)
    except Exception as exc:
        await dbexec(
            """
            UPDATE deep_reflections
            SET status = 'failed',
                error = $2,
                updated_at = now()
            WHERE id = $1::uuid
            """,
            reflection_id,
            str(exc),
        )


async def _persist_deep_reflection_done(reflection_id: str, result: dict[str, Any]) -> None:
    inputs_hash = str((result.get("versions") or {}).get("inputs_hash") or "")
    result_json = json.dumps(result, ensure_ascii=False)
    window = result.get("window") or {}
    window_start = _coerce_ts(window.get("from"))
    window_end = _coerce_ts(window.get("to"))

    if window_start and window_end:
        try:
            await dbexec(
                """
                UPDATE deep_reflections
                SET status = 'done',
                    window_start = $2::timestamptz,
                    window_end = $3::timestamptz,
                    inputs_hash = $4,
                    result_json = $5::jsonb,
                    error = NULL,
                    updated_at = now()
                WHERE id = $1::uuid
                """,
                reflection_id,
                window_start.isoformat(),
                window_end.isoformat(),
                inputs_hash,
                result_json,
            )
            return
        except Exception as exc:
            LOGGER.warning(
                "Deep reflection window write failed for %s; falling back to payload-only update: %s",
                reflection_id,
                exc,
            )

    await dbexec(
        """
        UPDATE deep_reflections
        SET status = 'done',
            inputs_hash = $2,
            result_json = $3::jsonb,
            error = NULL,
            updated_at = now()
        WHERE id = $1::uuid
        """,
        reflection_id,
        inputs_hash,
        result_json,
    )


def _build_reflection_result(
    arc_payload: dict[str, Any],
    *,
    mode: str,
    user_query: str | None,
) -> dict[str, Any]:
    arc = arc_payload.get("arc") or {}
    included = arc_payload.get("included_moments") or []
    phase_packets = _build_phase_packets(arc, included)
    recurring = _recurring_threads(included)
    start_signal = _phase_signal(phase_packets[0]) if phase_packets else "Started as one continuous thread."
    current_signal = _current_signal(phase_packets[-1]) if phase_packets else "Current thread remains active."
    pivot_summaries = _pivot_summaries(phase_packets)
    open_questions = _open_questions(phase_packets[-1] if phase_packets else None)

    return {
        "topic_key": arc_payload.get("anchor"),
        "topic_label": arc_payload.get("label"),
        "reflection_mode": mode,
        "query_context": {
            "active_query": user_query or "",
            "active_query_source": "provided" if user_query else "derived_or_none",
        },
        "window": arc_payload.get("window") or {},
        "versions": arc_payload.get("versions") or {},
        "surface": arc_payload.get("surface") or {},
        "arc_summary": {
            "span_days": arc.get("span_days"),
            "element_count": arc.get("element_count"),
            "phase_count": arc.get("phase_count"),
            "direction": ((arc.get("features") or {}).get("direction")),
            "coherence": ((arc_payload.get("surface") or {}).get("coherence_score")),
        },
        "origin_story": start_signal,
        "key_pivots": pivot_summaries,
        "recurring_tensions": recurring,
        "current_stage": current_signal,
        "open_questions": open_questions,
        "chat_response": _compose_chat_response(
            origin_story=start_signal,
            key_pivots=pivot_summaries,
            current_stage=current_signal,
            recurring_tensions=recurring,
            open_questions=open_questions,
            mode=mode,
            user_query=user_query,
        ),
        "phase_packets": phase_packets,
    }


async def _enrich_reflection_with_llm(
    *,
    person_id: str,
    topic_key: str,
    arc_payload: dict[str, Any],
    deterministic: dict[str, Any],
    mode: str,
    user_query: str | None,
) -> dict[str, Any]:
    result = dict(deterministic)
    deterministic_chat_response = str(result.get("chat_response") or "").strip()
    result["deterministic_chat_response"] = deterministic_chat_response
    result["chat_response_source"] = "deterministic"

    router = _get_deep_reflection_router()
    if router is None:
        result["llm_reflection"] = {
            "enabled": False,
            "reason": "llm_router_unavailable",
        }
        return result

    try:
        packet = await _build_reflection_llm_packet(
            person_id=person_id,
            topic_key=topic_key,
            arc_payload=arc_payload,
            deterministic=deterministic,
            mode=mode,
            user_query=user_query,
        )
        prompt_messages = _build_deep_reflection_prompt_messages(packet)
        model = os.getenv("MODEL_DEEP_REFLECTION_CHAT", os.getenv("MODEL_CHAT", "gpt-4o-mini"))
        max_tokens = 520 if mode == "deep_answer" else 260
        max_chars = 2800 if mode == "deep_answer" else 700
        llm_response = await router.chat(
            messages=prompt_messages,
            model=model,
            temperature=0.35,
            max_tokens=max_tokens,
        )
        llm_text = _normalize_llm_text(llm_response.text or "", max_chars=max_chars)
        quality_gate: dict[str, Any] | None = None
        generation_attempts: list[dict[str, Any]] = []
        generation_attempts.append(
            {
                "attempt": 1,
                "model": llm_response.model or model,
                "usage": dict(llm_response.usage or {}),
                "response_text": llm_text,
            }
        )

        if mode == "deep_answer":
            contract = packet.get("response_contract") or {}
            passed, reasons = _passes_deep_answer_quality_gate(llm_text, contract)
            quality_gate = {
                "applied": True,
                "initial_passed": passed,
                "initial_issues": reasons,
                "regenerated": False,
            }
            if not passed:
                revision_prompt = _build_deep_answer_revision_prompt(contract, reasons)
                revision_messages = prompt_messages + [
                    {"role": "assistant", "content": llm_text or "(empty response)"},
                    {"role": "user", "content": revision_prompt},
                ]
                revised = await router.chat(
                    messages=revision_messages,
                    model=model,
                    temperature=0.25,
                    max_tokens=max_tokens,
                )
                revised_text = _normalize_llm_text(revised.text or "", max_chars=max_chars)
                revised_passed, revised_reasons = _passes_deep_answer_quality_gate(revised_text, contract)
                generation_attempts.append(
                    {
                        "attempt": 2,
                        "model": revised.model or model,
                        "usage": dict(revised.usage or {}),
                        "response_text": revised_text,
                    }
                )
                quality_gate.update(
                    {
                        "regenerated": True,
                        "regenerated_passed": revised_passed,
                        "regenerated_issues": revised_reasons,
                    }
                )
                if revised_text:
                    llm_text = revised_text

        if llm_text:
            result["chat_response"] = llm_text
            result["chat_response_source"] = "llm"

        result["llm_reflection"] = {
            "enabled": True,
            "router_source": "global_router",
            "model": llm_response.model or model,
            "provider": llm_response.provider,
            "usage": dict(llm_response.usage or {}),
            "prompt_messages": prompt_messages,
            "input_packet": packet,
            "response_text": llm_text,
            "quality_gate": quality_gate,
            "generation_attempts": generation_attempts,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        LOGGER.warning("Deep reflection LLM synthesis failed for %s: %s", person_id, exc)
        result["llm_reflection"] = {
            "enabled": True,
            "error": str(exc),
        }
    return result


def _get_deep_reflection_router() -> Any | None:
    try:
        return get_router()
    except Exception as exc:
        LOGGER.info("Deep reflection router unavailable; deterministic fallback: %s", exc)
        return None


async def _build_reflection_llm_packet(
    *,
    person_id: str,
    topic_key: str,
    arc_payload: dict[str, Any],
    deterministic: dict[str, Any],
    mode: str,
    user_query: str | None,
) -> dict[str, Any]:
    evidence = _build_evidence_anchors(arc_payload.get("included_moments") or [], limit=8)
    topic_keywords = _topic_keywords(topic_key, deterministic, evidence)
    surface = deterministic.get("surface") or {}
    detail_allowed = bool(surface.get("detail_allowed"))
    mirror_allowed = bool(surface.get("mirror_allowed", True))
    recent_episodes = await _load_recent_topic_episodes(
        person_id=person_id,
        topic_keywords=topic_keywords,
    )
    delta_since_last = await _build_delta_since_last_reflection(
        person_id=person_id,
        topic_key=topic_key,
        deterministic=deterministic,
    )
    latest_turn_context = await _load_latest_turn_context(
        person_id=person_id,
        topic_keywords=topic_keywords,
    )
    provided_query = str(user_query or "").strip()
    recovered_query = str(latest_turn_context.get("latest_topic_user_message") or "").strip()
    if provided_query:
        effective_query = provided_query
        effective_source = "provided"
    elif recovered_query:
        effective_query = recovered_query
        effective_source = "topic_turn_recovery"
    else:
        effective_query = ""
        effective_source = "none"
    latest_turn_context["effective_user_query"] = effective_query
    latest_turn_context["effective_user_query_source"] = effective_source
    latest_turn_context["provided_user_query"] = provided_query or None

    response_contract: dict[str, Any]
    if mode == "deep_answer":
        response_contract = {
            "voice": "friend, warm, direct",
            "length_words": "180-280",
            "min_words": 180,
            "max_words": 280,
            "max_questions": 1,
            "avoid": ["ayurvedic jargon", "therapy-speak", "generic motivation"],
            "format": (
                "five short labeled sections: Direct answer, History anchors, "
                "Recommended path, Alternative path, Risk + next 7-day action"
            ),
            "required_sections": [
                "Direct answer",
                "History anchors",
                "Recommended path",
                "Alternative path",
                "Risk + next 7-day action",
            ],
            "anchor_count": "2-3",
            "priority": "current_query_first",
        }
    else:
        response_contract = {
            "voice": "friend, warm, direct",
            "length_words": "80-140",
            "min_words": 80,
            "max_words": 140,
            "max_questions": 1,
            "avoid": ["ayurvedic jargon", "therapy-speak", "generic motivation"],
            "format": "single short paragraph",
            "priority": "longitudinal_reflection",
        }
    response_contract["detail_allowed"] = detail_allowed
    response_contract["mirror_allowed"] = mirror_allowed
    response_contract["nudge_policy"] = "grounded_next_step" if detail_allowed else "mirror_only"

    return {
        "topic_key": topic_key,
        "topic_label": deterministic.get("topic_label"),
        "request_mode": mode,
        "window": deterministic.get("window") or {},
        "surface": surface,
        "arc_compact_global": _build_arc_compact_global(deterministic),
        "recent_episode_compact": recent_episodes,
        "evidence_anchors": evidence,
        "delta_since_last_reflection": delta_since_last,
        "latest_turn_context": latest_turn_context,
        "current_query": {
            "text": effective_query,
            "source": effective_source,
        },
        "response_contract": response_contract,
    }


def _build_arc_compact_global(deterministic: dict[str, Any]) -> dict[str, Any]:
    phase_packets = deterministic.get("phase_packets") or []
    return {
        "origin_story": deterministic.get("origin_story"),
        "key_pivots": list(deterministic.get("key_pivots") or [])[:3],
        "current_stage": deterministic.get("current_stage"),
        "recurring_tensions": list(deterministic.get("recurring_tensions") or [])[:3],
        "open_questions": list(deterministic.get("open_questions") or [])[:2],
        "arc_summary": deterministic.get("arc_summary") or {},
        "phase_compaction": [
            {
                "index": int(phase.get("index") or 0),
                "summary": phase.get("summary"),
                "dominant_tag": phase.get("dominant_tag"),
                "element_count": int(phase.get("element_count") or 0),
                "window": {
                    "start": phase.get("start_ts"),
                    "end": phase.get("end_ts"),
                },
            }
            for phase in phase_packets
        ],
    }


def _build_evidence_anchors(included_moments: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if not included_moments:
        return []
    ordered = sorted(
        included_moments,
        key=lambda item: (
            str(item.get("ts") or ""),
            str(item.get("source_ref") or ""),
        ),
    )
    total = len(ordered)
    early = ordered[: min(3, total)]
    middle = ordered[max(0, (total // 2) - 1): max(0, (total // 2) + 2)]
    late = ordered[max(0, total - 6):]

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in early + middle + late:
        key = f"{item.get('ts')}|{item.get('source_ref')}"
        if key in seen:
            continue
        seen.add(key)
        snippet = str(item.get("short_snippet") or item.get("snippet") or "").strip()
        selected.append(
            {
                "ts": item.get("ts"),
                "source_ref": item.get("source_ref"),
                "facet": item.get("facet"),
                "decision_state": item.get("decision_state"),
                "stance": item.get("stance"),
                "snippet": _truncate(snippet, 220),
            }
        )
        if len(selected) >= limit:
            break
    return selected


async def _load_recent_topic_episodes(
    *,
    person_id: str,
    topic_keywords: set[str],
) -> list[dict[str, Any]]:
    try:
        rows = await dbfetch(
            """
            SELECT id, COALESCE(record->>'summary', text, '') AS summary, ts
            FROM memory_episodic
            WHERE (person_id = $1::uuid OR user_id = $2)
            ORDER BY ts DESC
            LIMIT 80
            """,
            person_id,
            person_id,
        )
    except Exception as exc:
        LOGGER.info("Recent episodic compaction unavailable for %s: %s", person_id, exc)
        return []

    ranked: list[tuple[int, float, dict[str, Any]]] = []
    for row in rows or []:
        summary = str(row.get("summary") or "").strip()
        if not summary:
            continue
        matched = _matched_keywords(summary, topic_keywords)
        overlap = len(matched)
        ts_iso = _iso(row.get("ts"))
        recency = _recency_score(row.get("ts"))
        ranked.append(
            (
                overlap,
                recency,
                {
                    "id": str(row.get("id") or ""),
                    "ts": ts_iso,
                    "summary": _truncate(summary, 260),
                    "topic_overlap": overlap,
                    "matched_keywords": matched[:5],
                },
            )
        )

    overlap_rows = [item for item in ranked if item[0] > 0]
    if overlap_rows:
        overlap_rows.sort(key=lambda item: (-item[0], -item[1]))
        return [item[2] for item in overlap_rows[:5]]

    ranked.sort(key=lambda item: item[1], reverse=True)
    return [item[2] for item in ranked[:3]]


async def _build_delta_since_last_reflection(
    *,
    person_id: str,
    topic_key: str,
    deterministic: dict[str, Any],
) -> dict[str, Any]:
    try:
        row = await dbfetch(
            """
            SELECT result_json, created_at
            FROM deep_reflections
            WHERE person_id = $1::uuid
              AND topic_key = $2
              AND status = 'done'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
            topic_key,
            one=True,
        )
    except Exception as exc:
        LOGGER.info("Delta lookup unavailable for deep reflection %s/%s: %s", person_id, topic_key, exc)
        return {"has_previous": False, "error": str(exc)}

    if not row:
        return {"has_previous": False}

    previous = _parse_json_object(row.get("result_json"))
    prev_current = str(previous.get("current_stage") or "").strip()
    prev_recurring = [str(x).strip() for x in (previous.get("recurring_tensions") or []) if str(x).strip()]
    prev_pivots = [str(x).strip() for x in (previous.get("key_pivots") or []) if str(x).strip()]

    curr_current = str(deterministic.get("current_stage") or "").strip()
    curr_recurring = [str(x).strip() for x in (deterministic.get("recurring_tensions") or []) if str(x).strip()]
    curr_pivots = [str(x).strip() for x in (deterministic.get("key_pivots") or []) if str(x).strip()]

    return {
        "has_previous": True,
        "previous_reflection_at": _iso(row.get("created_at")),
        "current_stage_changed": bool(prev_current and curr_current and prev_current != curr_current),
        "previous_current_stage": prev_current or None,
        "current_current_stage": curr_current or None,
        "new_recurring_tensions": [item for item in curr_recurring if item not in prev_recurring][:3],
        "persisting_recurring_tensions": [item for item in curr_recurring if item in prev_recurring][:3],
        "pivot_count_delta": len(curr_pivots) - len(prev_pivots),
    }


async def _load_latest_turn_context(
    person_id: str,
    *,
    topic_keywords: set[str],
) -> dict[str, Any]:
    topic_user_turns: list[dict[str, Any]] = []
    try:
        rows = await dbfetch(
            """
            SELECT role, text, created_at
            FROM conversation_turns
            WHERE user_id = $1::uuid OR person_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT 6
            """,
            person_id,
        )
        for row in rows or []:
            role = str(row.get("role") or "").lower()
            text = str(row.get("text") or "").strip()
            if role != "user" or not text:
                continue
            matched = _matched_keywords(text, topic_keywords)
            if not matched:
                continue
            topic_user_turns.append(
                {
                    "role": "user",
                    "ts": _iso(row.get("created_at")),
                    "text": _truncate(text, 220),
                    "matched_keywords": matched[:5],
                }
            )
        topic_user_turns.reverse()
    except Exception as exc:
        LOGGER.info("Latest turn context unavailable for %s: %s", person_id, exc)

    state_hints: dict[str, Any] = {}
    try:
        state_row = await dbfetch(
            """
            SELECT emotion_state, rhythm_state, longitudinal_state, identity_momentum_state
            FROM personal_model
            WHERE person_id = $1::uuid
            """,
            person_id,
            one=True,
        )
        if state_row:
            emotion_state = _parse_json_object(state_row.get("emotion_state"))
            rhythm_state = _parse_json_object(state_row.get("rhythm_state"))
            longitudinal_state = _parse_json_object(state_row.get("longitudinal_state"))
            identity_state = _parse_json_object(state_row.get("identity_momentum_state"))
            state_hints = {
                "emotion_hint": _extract_signal(emotion_state, ("emotion", "mood", "state", "dominant_emotion")),
                "companion_mode": _extract_signal(longitudinal_state, ("mode", "companion_mode", "state")),
                "load_hint": _extract_signal(longitudinal_state, ("load", "load_level", "cognitive_load")),
                "energy_hint": _extract_signal(rhythm_state, ("energy", "energy_level", "energy_mode")),
                "identity_phase": _extract_signal(identity_state, ("phase", "momentum", "direction")),
            }
    except Exception as exc:
        LOGGER.info("State hints unavailable for %s: %s", person_id, exc)

    latest_user_message = next(
        (item["text"] for item in reversed(topic_user_turns) if item.get("text")),
        "",
    )

    return {
        "latest_topic_user_message": latest_user_message,
        "recent_topic_user_turns": topic_user_turns[-3:],
        "state_hints": state_hints,
    }


def _build_deep_reflection_prompt_messages(packet: dict[str, Any]) -> list[dict[str, str]]:
    arc = packet.get("arc_compact_global") or {}
    latest = packet.get("latest_turn_context") or {}
    query_info = packet.get("current_query") or {}
    request_mode = str(packet.get("request_mode") or "topic_reflection").strip() or "topic_reflection"
    delta = packet.get("delta_since_last_reflection") or {}
    contract = packet.get("response_contract") or {}
    surface = packet.get("surface") or {}

    key_pivots = _clean_text_list(arc.get("key_pivots"), limit=3)
    recurring = _clean_text_list(arc.get("recurring_tensions"), limit=3)
    open_questions = _clean_text_list(arc.get("open_questions"), limit=2)
    phase_compaction = [
        phase
        for phase in (arc.get("phase_compaction") or [])
        if isinstance(phase, dict) and str(phase.get("summary") or "").strip()
    ][:3]
    evidence = [
        item
        for item in (packet.get("evidence_anchors") or [])
        if isinstance(item, dict) and str(item.get("snippet") or "").strip()
    ][:3]
    episodes = [
        item
        for item in (packet.get("recent_episode_compact") or [])
        if isinstance(item, dict) and str(item.get("summary") or "").strip()
    ][:3]

    history_lines: list[str] = [
        f"- Topic: {str(packet.get('topic_label') or packet.get('topic_key') or 'unknown').strip()}",
        f"- Where it began: {str(arc.get('origin_story') or 'unknown').strip()}",
        f"- Where it is now: {str(arc.get('current_stage') or 'unknown').strip()}",
    ]
    if key_pivots:
        history_lines.append(f"- Key shifts: {'; '.join(key_pivots)}")
    if phase_compaction:
        phase_story = []
        for idx, phase in enumerate(phase_compaction):
            marker = _timeline_marker(idx, len(phase_compaction))
            phase_story.append(f"{marker} {str(phase.get('summary') or '').strip()}")
        history_lines.append(f"- Story flow: {' | '.join(phase_story)}")
    if recurring:
        history_lines.append(f"- Recurring tensions: {'; '.join(recurring)}")
    if open_questions:
        history_lines.append(f"- Open question: {open_questions[0]}")
    if episodes:
        history_lines.append(
            "- Recent episodes: "
            + " | ".join(str(item.get("summary") or "").strip() for item in episodes)
        )
    if evidence:
        history_lines.append(
            "- Evidence anchors: "
            + " | ".join(str(item.get("snippet") or "").strip() for item in evidence)
        )

    state_hints = latest.get("state_hints") or {}
    person_lines: list[str] = []
    if recurring:
        person_lines.append(f"- Stable pattern: {recurring[0]}")
    if open_questions:
        person_lines.append(f"- Ongoing tension to hold: {open_questions[0]}")
    hint_parts = []
    for key, label in (
        ("emotion_hint", "emotion"),
        ("load_hint", "load"),
        ("energy_hint", "energy"),
        ("identity_phase", "identity phase"),
    ):
        value = state_hints.get(key)
        if value in (None, "", [], {}):
            continue
        hint_parts.append(f"{label}={value}")
    if hint_parts:
        person_lines.append(f"- Current state hints: {', '.join(hint_parts)}")
    if delta.get("has_previous"):
        if delta.get("current_stage_changed"):
            person_lines.append(
                "- Since the last reflection, the current stage has changed."
            )
        else:
            person_lines.append(
                "- Since the last reflection, the current stage is stable."
            )
        new_tensions = _clean_text_list(delta.get("new_recurring_tensions"), limit=2)
        if new_tensions:
            person_lines.append(f"- New recurring tensions: {'; '.join(new_tensions)}")
    if not person_lines:
        person_lines.append("- No extra person-level signals beyond the topic history.")

    current_query = str(query_info.get("text") or latest.get("effective_user_query") or "").strip()
    query_source = str(query_info.get("source") or latest.get("effective_user_query_source") or "none").strip()
    if not current_query:
        if request_mode == "deep_answer":
            current_query = "(No active question was provided; answer as a concise decision reflection grounded in topic history.)"
        else:
            current_query = "(No active user query; provide a concise longitudinal reflection.)"

    avoid = _clean_text_list(contract.get("avoid"), limit=5)
    response_lines = [
        f"- Voice: {str(contract.get('voice') or 'friend, warm, direct')}",
        f"- Length: {str(contract.get('length_words') or '80-140 words')}",
        f"- Format: {str(contract.get('format') or 'single short paragraph')}",
        f"- Max questions: {str(contract.get('max_questions') or 1)}",
    ]
    if avoid:
        response_lines.append(f"- Avoid: {', '.join(avoid)}")
    detail_allowed = bool(contract.get("detail_allowed", surface.get("detail_allowed")))
    mirror_allowed = bool(contract.get("mirror_allowed", surface.get("mirror_allowed", True)))
    if detail_allowed:
        response_lines.append("- Detail policy: detail is allowed; keep guidance grounded.")
    else:
        response_lines.append("- Detail policy: mirror-only; do not prescribe next steps.")
    response_lines.append(
        f"- Mirror allowed: {'yes' if mirror_allowed else 'no'}"
    )
    if request_mode == "deep_answer":
        section_labels = _clean_text_list(contract.get("required_sections"), limit=8)
        if section_labels:
            response_lines.append(f"- Required section labels: {', '.join(section_labels)}")
        response_lines.append("- Use exactly 2-3 history anchors in the History anchors section.")
        response_lines.append("- Value add: answer current query first, then recommendation, alternative, and one risk-aware 7-day checkpoint.")
    else:
        response_lines.append("- Value add: highlight what changed, what repeats, and one question to carry forward.")

    user_prompt = (
        "Write one deep reflection reply for the user.\n"
        "Stay strictly within the topic context below.\n"
        "Prioritize answering the current query directly.\n"
        "Use history and person context as grounding, not as a detour.\n"
        "Do not import concerns from unrelated topics or turns.\n\n"
        f"Mode: {request_mode}\n"
        f"Current query source: {query_source or 'none'}\n\n"
        "History on this topic:\n"
        + "\n".join(history_lines)
        + "\n\nWhat we know about this person on this topic:\n"
        + "\n".join(person_lines)
        + "\n\nCurrent query now:\n"
        + current_query
        + "\n\nResponse contract:\n"
        + "\n".join(response_lines)
        + "\n\nReturn plain text only."
    )
    return [
        {"role": "system", "content": _DEEP_REFLECTION_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]


def _clean_text_list(values: Any, *, limit: int) -> list[str]:
    out: list[str] = []
    for item in values or []:
        text = str(item or "").strip()
        if not text:
            continue
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _timeline_marker(index: int, total: int) -> str:
    if total <= 1:
        return "Now:"
    if index == 0:
        return "First:"
    if index == total - 1:
        return "Now:"
    return "Then:"


def _topic_keywords(
    topic_key: str,
    deterministic: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> set[str]:
    raw_parts: list[str] = [topic_key, str(deterministic.get("topic_label") or "")]
    raw_parts.extend(str(item.get("facet") or "") for item in evidence if item.get("facet"))
    raw_parts.extend(str(item) for item in (deterministic.get("recurring_tensions") or []))
    tokens = {
        token
        for token in _tokenize(" ".join(raw_parts))
        if len(token) > 2 and token not in _TOPIC_STOPWORDS
    }
    return tokens


def _matched_keywords(text: str, keywords: set[str]) -> list[str]:
    if not keywords:
        return []
    present = set(_tokenize(text))
    return sorted(present.intersection(keywords))


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _normalize_llm_text(text: str, *, max_chars: int = 700) -> str:
    value = " ".join((text or "").strip().split())
    if not value:
        return ""
    return _truncate(value, max_chars)


def _passes_deep_answer_quality_gate(text: str, contract: dict[str, Any]) -> tuple[bool, list[str]]:
    output = str(text or "").strip()
    issues: list[str] = []
    if not output:
        return False, ["empty_response"]

    words = len(re.findall(r"\b[\w']+\b", output))
    min_words = int(contract.get("min_words") or 180)
    max_words = int(contract.get("max_words") or 280)
    if words < min_words:
        issues.append(f"too_short:{words}<{min_words}")
    if words > max_words:
        issues.append(f"too_long:{words}>{max_words}")

    required_sections = _clean_text_list(contract.get("required_sections"), limit=12)
    lower_output = output.lower()
    for section in required_sections:
        if not _has_required_section(lower_output, section):
            issues.append(f"missing_section:{section}")

    return (len(issues) == 0), issues


def _build_deep_answer_revision_prompt(contract: dict[str, Any], issues: list[str]) -> str:
    required_sections = _clean_text_list(contract.get("required_sections"), limit=12)
    section_line = ", ".join(required_sections) if required_sections else (
        "Direct answer, History anchors, Recommended path, Alternative path, Risk + next 7-day action"
    )
    issue_line = "; ".join(issues) if issues else "quality contract mismatch"
    return (
        "Revise the previous answer to satisfy the response contract exactly.\n"
        f"Detected issues: {issue_line}\n"
        f"Word range: {int(contract.get('min_words') or 180)}-{int(contract.get('max_words') or 280)}.\n"
        f"Use these exact section labels with colons: {section_line}.\n"
        "Keep it warm, direct, and grounded in the provided history/query.\n"
        "Return plain text only."
    )


def _has_required_section(output_lower: str, section_label: str) -> bool:
    label = str(section_label or "").lower().strip()
    if not label:
        return True
    variants = {
        label,
        label.replace("+", "and"),
        label.replace("+", "&"),
        label.replace("+", "/"),
        label.replace("7-day", "7 day"),
    }
    for variant in variants:
        if f"{variant}:" in output_lower:
            return True
    if label == "risk + next 7-day action":
        return bool(
            re.search(
                r"risk\s*(\+|and|&|/)\s*next\s*7[- ]day\s*action\s*:",
                output_lower,
            )
        )
    return False


def _truncate(text: str, max_chars: int) -> str:
    value = (text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def _recency_score(value: Any) -> float:
    if isinstance(value, datetime):
        ts = value if value.tzinfo else value.replace(tzinfo=UTC)
    elif isinstance(value, str):
        ts = _coerce_ts(value)
        if ts is None:
            return 0.0
    else:
        return 0.0
    return ts.timestamp()


def _extract_signal(state: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = state.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _build_phase_packets(arc: dict[str, Any], included_moments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for phase in arc.get("phases") or []:
        start_ts = _coerce_ts(phase.get("start_ts"))
        end_ts = _coerce_ts(phase.get("end_ts"))
        phase_moments = []
        for item in included_moments:
            ts = _coerce_ts(item.get("ts"))
            if ts is None or start_ts is None or end_ts is None:
                continue
            if start_ts <= ts <= end_ts:
                phase_moments.append(item)
        stats = phase.get("stats") or {}
        dominant = stats.get("dominant_tag") or {}
        label = str((dominant or {}).get("label") or "")
        packets.append(
            {
                "index": int(phase.get("index") or 0),
                "start_ts": phase.get("start_ts"),
                "end_ts": phase.get("end_ts"),
                "element_count": int(phase.get("element_count") or 0),
                "dominant_tag": label or None,
                "summary": _phase_signal(
                    {
                        "label": label,
                        "element_count": int(phase.get("element_count") or 0),
                        "start_ts": phase.get("start_ts"),
                        "end_ts": phase.get("end_ts"),
                    }
                ),
                "evidence": [
                    {
                        "source_ref": item.get("source_ref"),
                        "ts": item.get("ts"),
                        "snippet": str(item.get("short_snippet") or "")[:200],
                    }
                    for item in phase_moments[:3]
                ],
            }
        )
    return packets


def _phase_signal(phase: dict[str, Any]) -> str:
    label = str(phase.get("label") or phase.get("dominant_tag") or "").strip()
    if label:
        return f"Started around {label}." if int(phase.get("index") or 0) == 0 else f"Centered on {label}."
    density = _phase_density(phase)
    if density >= 0.12:
        descriptor = "dense"
    elif density <= 0.04:
        descriptor = "sparse"
    else:
        descriptor = "steady"
    return f"This phase was {descriptor} and exploratory."


def _current_signal(phase: dict[str, Any]) -> str:
    label = str(phase.get("dominant_tag") or "").strip()
    if label:
        return f"Currently centered on {label}."
    density = _phase_density(phase)
    if density >= 0.12:
        return "Currently dense and sustained."
    if density <= 0.04:
        return "Currently quieter and lighter."
    return "Currently holding a steady thread."


def _pivot_summaries(phase_packets: list[dict[str, Any]]) -> list[str]:
    summaries: list[str] = []
    for prev, current in zip(phase_packets, phase_packets[1:]):
        prev_label = str(prev.get("dominant_tag") or "").strip()
        current_label = str(current.get("dominant_tag") or "").strip()
        if prev_label and current_label and prev_label != current_label:
            summaries.append(f"Phase {current['index'] + 1} shifted from {prev_label} toward {current_label}.")
        else:
            summaries.append(f"Phase {current['index'] + 1} reorganized the thread.")
    return summaries


def _recurring_threads(included_moments: list[dict[str, Any]]) -> list[str]:
    facets = [
        str(item.get("facet") or "").strip()
        for item in included_moments
        if str(item.get("facet") or "").strip()
    ]
    counts = Counter(facets)
    recurring = [facet for facet, count in counts.items() if count >= 2]
    if not recurring:
        return ["No recurring sub-thread cleared the current threshold."]
    return [f"Recurring return to {facet.replace('_', ' ')}." for facet in recurring[:3]]


def _open_questions(phase: dict[str, Any] | None) -> list[str]:
    if not phase:
        return ["Whether this thread stays coherent in the next window."]
    label = str(phase.get("dominant_tag") or "").strip()
    if label:
        return [f"Whether the current thread stays centered on {label}."]
    return ["Whether the current thread holds or reorganizes again."]


def _compose_chat_response(
    *,
    origin_story: str,
    key_pivots: list[str],
    current_stage: str,
    recurring_tensions: list[str],
    open_questions: list[str],
    mode: str,
    user_query: str | None,
) -> str:
    if mode == "deep_answer" and str(user_query or "").strip():
        query = str(user_query or "").strip()
        fallback_lines = [
            f"Direct answer: On your question, yes, prioritize the current decision around this thread and move with one explicit operating choice.",
            (
                "History anchors: "
                + " ".join(
                    part
                    for part in [
                        origin_story.strip(),
                        key_pivots[0].strip() if key_pivots else "",
                        current_stage.strip(),
                    ]
                    if part
                )
            ),
            "Recommended path: Commit to one path for the next week and define a measurable checkpoint tied to this question.",
            "Alternative path: Keep options open for one short validation sprint, but cap scope so it does not dilute focus.",
            (
                "Risk + next 7-day action: The biggest risk is drift through over-analysis. "
                + (open_questions[0].strip() if open_questions else "Set one check-in question for day seven.")
            ),
        ]
        return " ".join(line for line in fallback_lines if line.strip())

    parts = [
        origin_story.strip(),
        key_pivots[0].strip() if key_pivots else "",
        current_stage.strip(),
        recurring_tensions[0].strip() if recurring_tensions else "",
        f"One question to sit with: {open_questions[0].strip()}" if open_questions else "",
    ]
    return " ".join(part for part in parts if part)


def _phase_density(phase: dict[str, Any] | None) -> float:
    if not phase:
        return 0.0
    element_count = max(int(phase.get("element_count") or 0), 0)
    start = _coerce_ts(phase.get("start_ts"))
    end = _coerce_ts(phase.get("end_ts"))
    if not start or not end:
        return 0.0
    duration_days = max(1.0, (end - start).total_seconds() / 86400.0)
    return element_count / duration_days


def _coerce_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC).isoformat()
        return value.astimezone(UTC).isoformat()
    if isinstance(value, str):
        return value
    return None


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


__all__ = [
    "create_deep_reflection_job",
    "get_deep_reflection_result",
    "get_deep_reflection_status",
]
