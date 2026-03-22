from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.core.llm import get_router
from sakhi.apps.api.services.continuity.adapters import (
    canonicalize_anchor,
    get_continuity_policy,
    load_journal_entries_for_continuity,
)
from sakhi.apps.api.services.continuity.compiler import (
    build_compiled_topics_index,
    compile_journal_continuity,
)
from sakhi.apps.api.services.continuity.cross_topic import get_life_dimensions
from sakhi.apps.api.services.continuity.service import (
    CONTINUITY_SCOPE,
    get_continuity_arc,
)
from sakhi.apps.api.services.continuity.thresholds import (
    CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE,
)
from sakhi.apps.api.services.governance.service import log_turn_event

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
_REFLECTION_ALLOWED_MODES = {
    "topic_reflection",  # Soul screen: <Topic> Story — no query, single arc trace
    "whole_story",       # Chat: Deep Reflect — query-driven deep reflection with optional linked-thread synthesis
    "cross_context",     # Soul screen: My Story — no query, all-topic interplay
}
_REFLECTION_MAX_TOPIC_KEYS = CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.max_topic_keys
_PRIORITY_CONNECTOR_RE = re.compile(
    r"\b(vs|versus|while|without|between|balance|juggle|trade[- ]?off|conflict|compete)\b"
)
_RESOURCE_PRESSURE_RE = re.compile(
    r"\b(time|deadline|schedule|overcommit|overload|stretched|bandwidth|money|budget|cost|debt|runway|load|energy)\b"
)
_STRONG_PRIORITY_CONFLICT_RE = re.compile(
    r"\b(without dropping|at the same time|can[' ]?t do both|pick one|choose between)\b"
)
_PRIORITY_DOMAIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "work": re.compile(r"\b(work|career|boss|job|meetings?|deadlines?)\b"),
    "family": re.compile(r"\b(family|dad|mom|parent|daughter|son|kids?|caregiv)\b"),
    "health": re.compile(r"\b(health|sleep|rest|exercise|body|wellness)\b"),
    "money": re.compile(r"\b(money|budget|cost|debt|runway|funding|salary)\b"),
    "product": re.compile(r"\b(sakhi|product|founder|mvp|build|launch)\b"),
}
_DEEP_REFLECTION_SYSTEM = """You are Sakhi - a friend who gets this person deeply.

Speak naturally, warm and direct. Keep it grounded in the packet evidence.
Do not use therapy-speak or Ayurvedic jargon.
Do not introduce themes that are not explicitly present in the packet.

Your role is to:
- trace what has unfolded over time
- surface what is actually happening beneath it
- help the person see clearly what matters now

Do not just describe the past.
Use the past to clarify the present.

Every reflection should feel like:
- things connecting over time
- patterns becoming visible
- clarity emerging

Follow the response contract exactly."""

_MONEY_TERMS = {
    "money",
    "budget",
    "cost",
    "debt",
    "expense",
    "salary",
    "runway",
    "funding",
    "afford",
}


def _normalize_reflection_mode(mode: str) -> str:
    token = str(mode or "").strip().lower()
    if token in _REFLECTION_ALLOWED_MODES:
        return token
    return "topic_reflection"


def _normalize_topic_key(value: str | None) -> str:
    token = canonicalize_anchor(value)
    if token and token != "unknown":
        return token
    raw = str(value or "").strip().lower().replace(" ", "_")
    return raw or "unknown"


def _normalize_topic_keys(topic_key: str, topic_keys: list[str] | None) -> list[str]:
    primary = _normalize_topic_key(topic_key)
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in [primary, *(topic_keys or [])]:
        token = _normalize_topic_key(raw)
        if not token or token == "unknown" or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
        if len(ordered) >= _REFLECTION_MAX_TOPIC_KEYS:
            break
    if not ordered:
        return [primary]
    return ordered


def _limit_topic_keys(topic_keys: list[str]) -> list[str]:
    return list(topic_keys[:_REFLECTION_MAX_TOPIC_KEYS])


async def _load_related_topic_arcs(
    *,
    person_id: str,
    primary_topic_key: str,
    topic_keys: list[str],
    window: str,
) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    for key in topic_keys:
        normalized = _normalize_topic_key(key)
        if not normalized or normalized in {"unknown", primary_topic_key}:
            continue
        try:
            arc_payload = await get_continuity_arc(
                person_id,
                normalized,
                window=window,
                debug=True,
                log_access=False,
                scope=CONTINUITY_SCOPE,
            )
        except Exception as exc:
            LOGGER.info(
                "Skipping related arc %s for %s: %s", normalized, person_id, exc
            )
            continue
        related.append(arc_payload)
        if len(related) >= (_REFLECTION_MAX_TOPIC_KEYS - 1):
            break
    return related


async def create_deep_reflection_job(
    person_id: str,
    topic_key: str,
    *,
    window: str = "3650d",
    mode: str = "topic_reflection",
    topic_keys: list[str] | None = None,
    user_query: str | None = None,
) -> dict[str, Any]:
    normalized_mode = _normalize_reflection_mode(mode)
    cleaned_query = str(user_query or "").strip() or None
    normalized_topic_key = _normalize_topic_key(topic_key)
    cleaned_topic_keys = _normalize_topic_keys(normalized_topic_key, topic_keys)
    if normalized_mode == "topic_reflection":
        cleaned_topic_keys = cleaned_topic_keys[:1]
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
        normalized_topic_key,
    )
    asyncio.create_task(
        _run_deep_reflection_job(
            reflection_id=reflection_id,
            person_id=person_id,
            topic_key=normalized_topic_key,
            window=window,
            mode=normalized_mode,
            topic_keys=cleaned_topic_keys,
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
            "topic_key": normalized_topic_key,
            "window": window,
            "mode": normalized_mode,
            "user_query_present": bool(cleaned_query),
            "topic_keys": _limit_topic_keys(cleaned_topic_keys),
        },
        reason="deep reflection queued",
    )
    return {
        "reflection_id": reflection_id,
        "status": "queued",
        "topic_key": normalized_topic_key,
        "window": window,
        "mode": normalized_mode,
        "user_query_present": bool(cleaned_query),
        "topic_keys": _limit_topic_keys(cleaned_topic_keys),
    }


async def get_deep_reflection_status(
    reflection_id: str, person_id: str
) -> dict[str, Any]:
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


async def get_deep_reflection_result(
    reflection_id: str, person_id: str
) -> dict[str, Any]:
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
        data={
            "reflection_id": reflection_id,
            "topic_key": str(row.get("topic_key") or ""),
        },
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
    topic_keys: list[str] | None = None,
    user_query: str | None = None,
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
        normalized_topic_keys = _normalize_topic_keys(topic_key, topic_keys)
        if mode == "topic_reflection":
            normalized_topic_keys = normalized_topic_keys[:1]
        related_arc_payloads = (
            await _load_related_topic_arcs(
                person_id=person_id,
                primary_topic_key=topic_key,
                topic_keys=normalized_topic_keys,
                window=window,
            )
            if mode in {"whole_story", "cross_context"}
            else []
        )
        related_arc_payloads = _dedupe_related_arc_payloads(
            primary_arc_payload=arc_payload,
            related_arc_payloads=related_arc_payloads,
        )
        deterministic = _build_reflection_result(
            arc_payload,
            mode=mode,
            topic_keys=normalized_topic_keys,
            related_arc_payloads=related_arc_payloads,
            user_query=user_query,
        )
        result = await _enrich_reflection_with_llm(
            person_id=person_id,
            topic_key=topic_key,
            arc_payload=arc_payload,
            deterministic=deterministic,
            mode=mode,
            topic_keys=normalized_topic_keys,
            related_arc_payloads=related_arc_payloads,
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


async def _persist_deep_reflection_done(
    reflection_id: str, result: dict[str, Any]
) -> None:
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
                window_start,
                window_end,
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
    topic_keys: list[str],
    related_arc_payloads: list[dict[str, Any]],
    user_query: str | None,
) -> dict[str, Any]:
    arc = arc_payload.get("arc") or {}
    included = arc_payload.get("included_moments") or []
    phase_packets = _build_phase_packets(arc, included)
    recurring = _recurring_threads(included)
    start_signal = (
        _phase_signal(phase_packets[0])
        if phase_packets
        else "Started as one continuous thread."
    )
    current_signal = (
        _current_signal(phase_packets[-1])
        if phase_packets
        else "Current thread remains active."
    )
    pivot_summaries = _pivot_summaries(phase_packets)
    open_questions = _open_questions(phase_packets[-1] if phase_packets else None)
    related_topics_compact = [
        _build_topic_compact(related_arc) for related_arc in related_arc_payloads
    ][:3]
    related_topic_labels = [
        str(item.get("topic_label") or item.get("topic_key") or "").strip()
        for item in related_topics_compact
        if str(item.get("topic_label") or item.get("topic_key") or "").strip()
    ]

    return {
        "topic_key": arc_payload.get("anchor"),
        "topic_label": arc_payload.get("label"),
        "reflection_mode": mode,
        "query_context": {
            "active_query": user_query or "",
            "active_query_source": "provided" if user_query else "derived_or_none",
            "requested_topics": _limit_topic_keys(topic_keys),
        },
        "window": arc_payload.get("window") or {},
        "versions": arc_payload.get("versions") or {},
        "surface": arc_payload.get("surface") or {},
        "topic_keys": _limit_topic_keys(topic_keys),
        "related_topics_compact": related_topics_compact,
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
            related_topics=related_topic_labels[:3],
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
    topic_keys: list[str],
    related_arc_payloads: list[dict[str, Any]],
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
            topic_keys=_limit_topic_keys(topic_keys),
            related_arc_payloads=related_arc_payloads[:3],
            user_query=user_query,
        )
        prompt_messages = _build_deep_reflection_prompt_messages(packet)
        model = os.getenv(
            "MODEL_DEEP_REFLECTION_CHAT", os.getenv("MODEL_CHAT", "gpt-4o-mini")
        )
        max_tokens = 520
        max_chars = 2800
        llm_response = await router.chat(
            messages=prompt_messages,
            model=model,
            temperature=0.35,
            max_tokens=max_tokens,
        )
        llm_text = _normalize_llm_text(llm_response.text or "", max_chars=max_chars)
        generation_attempts: list[dict[str, Any]] = []
        generation_attempts.append(
            {
                "attempt": 1,
                "model": llm_response.model or model,
                "usage": dict(llm_response.usage or {}),
                "response_text": llm_text,
            }
        )

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
            "generation_attempts": generation_attempts,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        LOGGER.warning(
            "Deep reflection LLM synthesis failed for %s: %s", person_id, exc
        )
        result["llm_reflection"] = {
            "enabled": True,
            "error": str(exc),
        }
    return result


def _get_deep_reflection_router() -> Any | None:
    try:
        return get_router()
    except Exception as exc:
        LOGGER.info(
            "Deep reflection router unavailable; deterministic fallback: %s", exc
        )
        return None


async def _build_reflection_llm_packet(
    *,
    person_id: str,
    topic_key: str,
    arc_payload: dict[str, Any],
    deterministic: dict[str, Any],
    mode: str,
    topic_keys: list[str] | None = None,
    related_arc_payloads: list[dict[str, Any]] | None = None,
    user_query: str | None,
) -> dict[str, Any]:
    topic_keys_clean = _normalize_topic_keys(topic_key, topic_keys)
    related_arc_payloads = list(related_arc_payloads or [])
    surface = deterministic.get("surface") or {}
    evidence = _build_evidence_anchors(
        arc_payload.get("included_moments") or [], limit=8
    )
    topic_keywords = _topic_keywords(topic_key, deterministic, evidence)
    recent_episodes = await _load_recent_topic_episodes(
        person_id=person_id,
        topic_keywords=topic_keywords,
    )
    delta_since_last = await _build_delta_since_last_reflection(
        person_id=person_id,
        topic_key=topic_key,
        deterministic=deterministic,
    )
    # Topic reflection is purely longitudinal — no conversation context needed
    if mode == "topic_reflection":
        latest_turn_context: dict[str, Any] = {
            "latest_topic_user_message": "",
            "recent_topic_user_turns": [],
            "state_hints": {},
            "effective_user_query": "",
            "effective_user_query_source": "none",
            "provided_user_query": None,
        }
        recent_verbatim_turns: list[dict[str, Any]] = []
    else:
        latest_turn_context = await _load_latest_turn_context(
            person_id=person_id,
            topic_keywords=topic_keywords,
        )
        # whole_story only: load last 4 verbatim turns (user + assistant) so
        # the synthesis is grounded in the immediate conversation that prompted the query.
        recent_verbatim_turns = (
            await _load_recent_verbatim_turns(person_id=person_id, limit=4)
            if mode == "whole_story"
            else []
        )

    provided_query = str(user_query or "").strip()
    recovered_query = str(
        latest_turn_context.get("latest_topic_user_message") or ""
    ).strip()
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

    priority_conflict = _assess_priority_conflict(
        current_query=effective_query,
        recurring_tensions=_clean_text_list(
            deterministic.get("recurring_tensions"), limit=3
        ),
        open_questions=_clean_text_list(deterministic.get("open_questions"), limit=2),
        evidence_anchors=evidence,
        recent_episodes=recent_episodes,
    )

    related_topics_compact = [
        _build_topic_compact(item) for item in related_arc_payloads
    ][:3]
    life_dimensions = await _load_life_dimensions_context(
        person_id=person_id,
        window=deterministic.get("window") or {},
        fallback_primary_topic_key=topic_key,
        fallback_primary_moments=arc_payload.get("included_moments") or [],
        fallback_related_arc_payloads=related_arc_payloads,
    )

    response_contract: dict[str, Any]
    if mode == "whole_story":
        response_contract = {
            "voice": "friend, warm, direct",
            "length_words": "220-360",
            "min_words": 220,
            "max_words": 360,
            "max_questions": 1,
            "avoid": ["ayurvedic jargon", "therapy-speak", "generic motivation"],
            "format": (
                "natural prose, answer the current query first, use linked threads and concrete evidence anchors "
                "when they genuinely add clarity, and clarify what this means for the person now"
            ),
            "priority": "current_query_with_optional_linked_context",
            "emotion_policy": {
                "mention_only_with_priority_conflict": True,
                "priority_conflict_detected": priority_conflict.get("detected", False),
                "max_emotion_sentences": 1,
                "priority_conflict_signals": priority_conflict.get("signals") or [],
                "rule": (
                    "Only mention emotion when a clear priority conflict is evidenced; "
                    "otherwise keep the response grounded in decisions and constraints."
                ),
            },
        }
    elif mode == "cross_context":
        response_contract = {
            "voice": "friend, warm, direct",
            "length_words": "160-260",
            "min_words": 160,
            "max_words": 260,
            "max_questions": 1,
            "avoid": ["ayurvedic jargon", "therapy-speak", "generic motivation"],
            "format": (
                "natural prose, explain how the main thread and linked threads influence each other, "
                "explicitly reference at least two linked threads when available, "
                "name one recurring tradeoff, end with one grounding question"
            ),
            "priority": "cross_context_relationship",
            "emotion_policy": {
                "mention_only_with_priority_conflict": True,
                "priority_conflict_detected": priority_conflict.get("detected", False),
                "max_emotion_sentences": 1,
                "priority_conflict_signals": priority_conflict.get("signals") or [],
                "rule": (
                    "Only mention emotion when a clear priority conflict is evidenced; "
                    "otherwise keep the reflection tied to observable cross-thread patterns."
                ),
            },
        }
    else:
        response_contract = {
            "voice": "friend, warm, direct",
            "length_words": "150-250",
            "min_words": 150,
            "max_words": 250,
            "max_questions": 1,
            "avoid": ["ayurvedic jargon", "therapy-speak", "generic motivation"],
            "format": (
                "natural prose, highlight what changed, what keeps returning, "
                "what remains unresolved, and what this reveals about the person's current situation"
            ),
            "priority": "longitudinal_reflection",
            "emotion_policy": {
                "mention_only_with_priority_conflict": True,
                "priority_conflict_detected": priority_conflict.get("detected", False),
                "max_emotion_sentences": 1,
                "priority_conflict_signals": priority_conflict.get("signals") or [],
                "rule": (
                    "Only mention emotion when a clear priority conflict is evidenced; "
                    "otherwise keep the reflection grounded in observable thread shifts."
                ),
            },
        }

    return {
        "topic_key": topic_key,
        "topic_label": deterministic.get("topic_label"),
        "request_mode": mode,
        "topic_keys": _limit_topic_keys(topic_keys_clean),
        "window": deterministic.get("window") or {},
        "surface": surface,
        "arc_compact_global": _build_arc_compact_global(deterministic),
        "related_topics_compact": related_topics_compact,
        "life_dimensions": life_dimensions,
        "recent_episode_compact": recent_episodes,
        "evidence_anchors": evidence,
        "delta_since_last_reflection": delta_since_last,
        "latest_turn_context": latest_turn_context,
        "recent_verbatim_turns": recent_verbatim_turns,
        "current_query": {
            "text": effective_query,
            "source": effective_source,
        },
        "priority_conflict": priority_conflict,
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


def _build_topic_compact(arc_payload: dict[str, Any]) -> dict[str, Any]:
    arc = arc_payload.get("arc") or {}
    phases = arc.get("phases") or []
    last_phase = phases[-1] if phases else {}
    dominant = (
        ((last_phase.get("stats") or {}).get("dominant_tag") or {})
        if isinstance(last_phase, dict)
        else {}
    )
    dominant_label = str((dominant or {}).get("label") or "").strip()
    return {
        "topic_key": _normalize_topic_key(str(arc_payload.get("anchor") or "")),
        "topic_label": str(
            arc_payload.get("label") or arc_payload.get("anchor") or ""
        ).strip(),
        "selected_count": int(
            arc.get("element_count") or len(arc_payload.get("included_moments") or [])
        ),
        "span_days": float(arc.get("span_days") or 0.0),
        "direction": str(((arc.get("features") or {}).get("direction")) or "").strip()
        or "steady",
        "current_signal": (
            f"Currently centered on {dominant_label}."
            if dominant_label
            else "Current thread remains active."
        ),
    }


def _dedupe_related_arc_payloads(
    *,
    primary_arc_payload: dict[str, Any],
    related_arc_payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for moment in primary_arc_payload.get("included_moments") or []:
        seen.add(_moment_identity(moment))

    deduped: list[dict[str, Any]] = []
    for payload in related_arc_payloads:
        kept_moments: list[dict[str, Any]] = []
        for moment in payload.get("included_moments") or []:
            identity = _moment_identity(moment)
            if identity in seen:
                continue
            seen.add(identity)
            kept_moments.append(moment)
        if not kept_moments:
            continue
        merged = dict(payload)
        merged["included_moments"] = kept_moments
        deduped.append(merged)
    return deduped


async def _load_life_dimensions_context(
    *,
    person_id: str,
    window: dict[str, Any],
    fallback_primary_topic_key: str,
    fallback_primary_moments: list[dict[str, Any]],
    fallback_related_arc_payloads: list[dict[str, Any]],
) -> dict[str, dict[str, Any]] | None:
    now = datetime.now(UTC)
    topics_index = await _load_topics_for_window(
        person_id=person_id,
        window=window,
        now=now,
    )
    if topics_index:
        try:
            dimensions = await get_life_dimensions(
                person_id=person_id,
                topics=topics_index,
                now=now,
            )
            if dimensions:
                return dimensions
        except Exception as exc:
            LOGGER.info(
                "Life dimensions cache service fallback for %s: %s", person_id, exc
            )

    return _build_life_dimensions_context(
        primary_topic_key=fallback_primary_topic_key,
        primary_moments=fallback_primary_moments,
        related_arc_payloads=fallback_related_arc_payloads,
    )


async def _load_topics_for_window(
    *,
    person_id: str,
    window: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    try:
        policy = await get_continuity_policy(person_id, CONTINUITY_SCOPE)
    except Exception as exc:
        LOGGER.info(
            "Continuity policy unavailable for life dimensions %s: %s", person_id, exc
        )
        return []
    if not bool(policy.get("enabled")):
        return []

    from_ts = _coerce_ts(window.get("from"))
    to_ts = _coerce_ts(window.get("to")) or now
    if from_ts is None or from_ts >= to_ts:
        from_ts = to_ts - timedelta(days=3650)

    try:
        journal_rows = await load_journal_entries_for_continuity(
            person_id,
            from_ts=from_ts,
            to_ts=to_ts,
            exclusions=policy.get("exclusions") or [],
        )
    except Exception as exc:
        LOGGER.info(
            "Journal continuity load unavailable for life dimensions %s: %s",
            person_id,
            exc,
        )
        return []

    try:
        compiled = compile_journal_continuity(
            person_id=person_id,
            journal_rows=journal_rows,
        )
        return build_compiled_topics_index(compiled, debug=False)
    except Exception as exc:
        LOGGER.info(
            "Continuity compile unavailable for life dimensions %s: %s", person_id, exc
        )
        return []


def _build_life_dimensions_context(
    *,
    primary_topic_key: str,
    primary_moments: list[dict[str, Any]],
    related_arc_payloads: list[dict[str, Any]],
) -> dict[str, dict[str, Any]] | None:
    now = datetime.now(UTC)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append_rows(topic_key: str, moments: list[dict[str, Any]]) -> None:
        for moment in moments:
            identity = _moment_identity(moment)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(
                {
                    "topic_key": topic_key,
                    "ts": _coerce_ts(moment.get("ts")),
                    "facet": str(moment.get("facet") or ""),
                    "stance": str(moment.get("stance") or "").lower().strip(),
                    "snippet": str(
                        moment.get("short_snippet") or moment.get("snippet") or ""
                    ).strip(),
                }
            )

    _append_rows(primary_topic_key, primary_moments)
    for related in related_arc_payloads:
        related_key = _normalize_topic_key(str(related.get("anchor") or ""))
        _append_rows(related_key, related.get("included_moments") or [])

    if not rows:
        return None

    def _recent(days: int) -> list[dict[str, Any]]:
        cutoff = now.timestamp() - (days * 86400)
        return [
            item
            for item in rows
            if isinstance(item.get("ts"), datetime) and item["ts"].timestamp() >= cutoff
        ]

    def _surface_standard(level: float, topic_count: int, entry_count: int) -> bool:
        return bool(
            (
                level
                >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_high
                or level
                <= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_low
            )
            and topic_count
            >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_min_topics
            and entry_count
            >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_min_entries
        )

    recent_14 = _recent(
        CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_time_window_days
    )
    recent_30 = _recent(
        CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_emotion_window_days
    )
    recent_60 = _recent(
        CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_financial_window_days
    )

    time_topics = sorted(
        {item["topic_key"] for item in recent_14 if item.get("topic_key")}
    )
    time_level = min(
        1.0, (len(time_topics) / 4.0) * 0.6 + (len(recent_14) / 20.0) * 0.4
    )
    time_direction = (
        "pressured"
        if time_level
        >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_high
        else (
            "resourced"
            if time_level
            <= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_low
            else "neutral"
        )
    )
    time_signal = (
        {
            "level": round(time_level, 4),
            "direction": time_direction,
            "affected_topics": time_topics[:3],
            "evidence_summary": (
                f"Recent activity is spread across {len(time_topics)} threads in the last "
                f"{CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_time_window_days} days."
            ),
        }
        if _surface_standard(time_level, len(time_topics), len(recent_14))
        else None
    )

    money_rows = [
        item
        for item in recent_60
        if set(
            _tokenize(f"{item.get('facet', '')} {item.get('snippet', '')}")
        ).intersection(_MONEY_TERMS)
    ]
    money_topics = sorted(
        {item["topic_key"] for item in money_rows if item.get("topic_key")}
    )
    money_level = min(1.0, len(money_rows) / 8.0)
    money_signal = (
        {
            "level": round(money_level, 4),
            "direction": (
                "pressured"
                if money_level
                >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.financial_surface_min_level
                else "neutral"
            ),
            "affected_topics": money_topics[:3],
            "evidence_summary": (
                f"Money or tradeoff language appeared across {len(money_topics)} active threads."
            ),
        }
        if (
            money_level
            >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.financial_surface_min_level
            and len(money_topics)
            >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_min_topics
            and len(money_rows)
            >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_min_entries
        )
        else None
    )

    stance_rows = [
        item for item in recent_30 if item.get("stance") in {"toward", "away"}
    ]
    away_count = sum(1 for item in stance_rows if item.get("stance") == "away")
    toward_count = sum(1 for item in stance_rows if item.get("stance") == "toward")
    emotional_level = (away_count / len(stance_rows)) if stance_rows else 0.0
    emotional_topics = sorted(
        {item["topic_key"] for item in stance_rows if item.get("topic_key")}
    )
    if (
        emotional_level
        >= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_high
    ):
        emotional_direction = "pressured"
    elif (
        toward_count > away_count
        and emotional_level
        <= CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE.dimension_surface_level_low
    ):
        emotional_direction = "resourced"
    else:
        emotional_direction = "neutral"
    emotional_signal = (
        {
            "level": round(emotional_level, 4),
            "direction": emotional_direction,
            "affected_topics": emotional_topics[:3],
            "evidence_summary": (
                "Recent stance signals show how emotionally stretched or resourced the thread set is."
            ),
        }
        if _surface_standard(emotional_level, len(emotional_topics), len(stance_rows))
        else None
    )

    if not any([time_signal, money_signal, emotional_signal]):
        return None

    return {
        "time_availability": time_signal,
        "financial_pressure": money_signal,
        "emotional_bandwidth": emotional_signal,
    }


def _moment_identity(moment: dict[str, Any]) -> str:
    source_ref = str(moment.get("source_ref") or "").strip()
    ts = str(moment.get("ts") or "").strip()
    if source_ref:
        return f"{source_ref}|{ts}"
    snippet = (
        str(moment.get("short_snippet") or moment.get("snippet") or "").strip().lower()
    )
    return f"{ts}|{snippet[:80]}"


def _build_evidence_anchors(
    included_moments: list[dict[str, Any]], *, limit: int
) -> list[dict[str, Any]]:
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
    middle = ordered[max(0, (total // 2) - 1) : max(0, (total // 2) + 2)]
    late = ordered[max(0, total - 6) :]

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
        LOGGER.info(
            "Delta lookup unavailable for deep reflection %s/%s: %s",
            person_id,
            topic_key,
            exc,
        )
        return {"has_previous": False, "error": str(exc)}

    if not row:
        return {"has_previous": False}

    previous = _parse_json_object(row.get("result_json"))
    prev_current = str(previous.get("current_stage") or "").strip()
    prev_recurring = [
        str(x).strip()
        for x in (previous.get("recurring_tensions") or [])
        if str(x).strip()
    ]
    prev_pivots = [
        str(x).strip() for x in (previous.get("key_pivots") or []) if str(x).strip()
    ]

    curr_current = str(deterministic.get("current_stage") or "").strip()
    curr_recurring = [
        str(x).strip()
        for x in (deterministic.get("recurring_tensions") or [])
        if str(x).strip()
    ]
    curr_pivots = [
        str(x).strip()
        for x in (deterministic.get("key_pivots") or [])
        if str(x).strip()
    ]

    return {
        "has_previous": True,
        "previous_reflection_at": _iso(row.get("created_at")),
        "current_stage_changed": bool(
            prev_current and curr_current and prev_current != curr_current
        ),
        "previous_current_stage": prev_current or None,
        "current_current_stage": curr_current or None,
        "new_recurring_tensions": [
            item for item in curr_recurring if item not in prev_recurring
        ][:3],
        "persisting_recurring_tensions": [
            item for item in curr_recurring if item in prev_recurring
        ][:3],
        "pivot_count_delta": len(curr_pivots) - len(prev_pivots),
    }


async def _load_recent_verbatim_turns(
    person_id: str,
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Load the last `limit` conversation turns (user + assistant) verbatim.

    No topic filtering — captures the immediate conversational context
    that shaped the user's Deep Reflect query, regardless of topic keywords.
    Only used for whole_story mode.
    """
    try:
        rows = await dbfetch(
            """
            SELECT role, text, created_at
            FROM conversation_turns
            WHERE user_id = $1::uuid OR person_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
        turns = []
        for row in reversed(rows or []):
            role = str(row.get("role") or "").lower()
            text = str(row.get("text") or "").strip()
            if role not in ("user", "assistant") or not text:
                continue
            turns.append(
                {
                    "role": role,
                    "ts": _iso(row.get("created_at")),
                    "text": _truncate(text, 300),
                }
            )
        return turns
    except Exception as exc:
        LOGGER.info("Recent verbatim turns unavailable for %s: %s", person_id, exc)
        return []


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
            identity_state = _parse_json_object(
                state_row.get("identity_momentum_state")
            )
            state_hints = {
                "emotion_hint": _extract_signal(
                    emotion_state, ("emotion", "mood", "state", "dominant_emotion")
                ),
                "companion_mode": _extract_signal(
                    longitudinal_state, ("mode", "companion_mode", "state")
                ),
                "load_hint": _extract_signal(
                    longitudinal_state, ("load", "load_level", "cognitive_load")
                ),
                "energy_hint": _extract_signal(
                    rhythm_state, ("energy", "energy_level", "energy_mode")
                ),
                "identity_phase": _extract_signal(
                    identity_state, ("phase", "momentum", "direction")
                ),
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


def _build_deep_reflection_prompt_messages(
    packet: dict[str, Any]
) -> list[dict[str, str]]:
    arc = packet.get("arc_compact_global") or {}
    latest = packet.get("latest_turn_context") or {}
    query_info = packet.get("current_query") or {}
    request_mode = (
        str(packet.get("request_mode") or "topic_reflection").strip()
        or "topic_reflection"
    )
    delta = packet.get("delta_since_last_reflection") or {}
    contract = packet.get("response_contract") or {}
    emotion_policy = (
        contract.get("emotion_policy")
        if isinstance(contract.get("emotion_policy"), dict)
        else {}
    )
    allow_emotion_reference = bool(emotion_policy.get("priority_conflict_detected"))

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
    related_topics = [
        item
        for item in (packet.get("related_topics_compact") or [])
        if isinstance(item, dict)
        and str(item.get("topic_label") or item.get("topic_key") or "").strip()
    ][:3]
    life_dimensions = (
        packet.get("life_dimensions")
        if isinstance(packet.get("life_dimensions"), dict)
        else {}
    )

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
    if related_topics:
        history_lines.append(
            "- Linked threads: "
            + " | ".join(
                (
                    f"{str(item.get('topic_label') or item.get('topic_key') or '').strip()} "
                    f"({int(item.get('selected_count') or 0)} moments)"
                ).strip()
                for item in related_topics
            )
        )

    state_hints = latest.get("state_hints") or {}
    person_lines: list[str] = []
    if recurring:
        person_lines.append(f"- Stable pattern: {recurring[0]}")
    if open_questions:
        person_lines.append(f"- Ongoing tension to hold: {open_questions[0]}")
    hint_parts = []
    for key, label in (
        ("load_hint", "load"),
        ("energy_hint", "energy"),
        ("identity_phase", "identity phase"),
    ):
        value = state_hints.get(key)
        if value in (None, "", [], {}):
            continue
        hint_parts.append(f"{label}={value}")
    emotion_hint = state_hints.get("emotion_hint")
    if allow_emotion_reference and emotion_hint not in (None, "", [], {}):
        hint_parts.append(f"emotion={emotion_hint}")
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

    dimension_lines: list[str] = []
    for key, label in (
        ("time_availability", "time"),
        ("financial_pressure", "money"),
        ("emotional_bandwidth", "emotional bandwidth"),
    ):
        payload = life_dimensions.get(key)
        if not isinstance(payload, dict):
            continue
        direction = str(payload.get("direction") or "neutral").strip()
        level = float(payload.get("level") or 0.0)
        topics = _clean_text_list(payload.get("affected_topics"), limit=3)
        if not topics:
            continue
        dimension_lines.append(
            f"- {label}: {direction} ({level:.0%}) across {', '.join(topics)}"
        )
    if dimension_lines:
        person_lines.append("- Cross-cutting dimensions:")
        person_lines.extend(dimension_lines)
    if not person_lines:
        person_lines.append("- No extra person-level signals beyond the topic history.")

    if request_mode in {"topic_reflection", "cross_context"}:
        # Longitudinal modes do not require a current user query.
        if request_mode == "cross_context":
            current_query = "Explain how this thread interacts with nearby threads and what that reveals."
            query_source = "cross_context_longitudinal"
        else:
            current_query = "Reflect on this topic's full arc."
            query_source = "longitudinal"
    else:
        current_query = str(
            query_info.get("text") or latest.get("effective_user_query") or ""
        ).strip()
        query_source = str(
            query_info.get("source")
            or latest.get("effective_user_query_source")
            or "none"
        ).strip()
        if not current_query:
            current_query = "(No active question was provided; answer as a concise decision reflection grounded in topic history.)"

    avoid = _clean_text_list(contract.get("avoid"), limit=5)
    response_lines = [
        f"- Voice: {str(contract.get('voice') or 'friend, warm, direct')}",
        f"- Length: {str(contract.get('length_words') or '80-140 words')}",
        f"- Format: {str(contract.get('format') or 'single short paragraph')}",
        f"- Max questions: {str(contract.get('max_questions') or 1)}",
    ]
    if avoid:
        response_lines.append(f"- Avoid: {', '.join(avoid)}")
    if emotion_policy.get("mention_only_with_priority_conflict"):
        if allow_emotion_reference:
            signals = _clean_text_list(
                emotion_policy.get("priority_conflict_signals"), limit=3
            )
            if signals:
                response_lines.append(
                    f"- Emotion mention: allowed but brief (max {emotion_policy.get('max_emotion_sentences', 1)} sentence) because priority conflict evidence is present: {', '.join(signals)}."
                )
            else:
                response_lines.append(
                    f"- Emotion mention: allowed but brief (max {emotion_policy.get('max_emotion_sentences', 1)} sentence) because priority conflict evidence is present."
                )
        else:
            response_lines.append(
                "- Emotion mention: omit unless a clear priority conflict is explicitly evidenced."
            )
    if request_mode == "whole_story":
        response_lines.append(
            "- Value add: answer the current query first, then use linked threads only when they add real clarity to the answer."
        )
    elif request_mode == "cross_context":
        response_lines.append(
            "- Value add: explicitly connect at least two linked threads, name one recurring tradeoff, and clarify what matters most right now."
        )
    else:
        response_lines.append(
            "- Value add: highlight what changed, what repeats, and one question to carry forward."
        )

    if request_mode == "topic_reflection":
        preamble = (
            "Write one longitudinal reflection for the user.\n"
            "Stay strictly within the topic context below.\n"
            "Reflect on the full arc — what changed, what repeats, what's unresolved.\n"
            "Do not import concerns from unrelated topics or turns.\n\n"
            f"Mode: {request_mode}\n\n"
        )
    elif request_mode == "cross_context":
        preamble = (
            "Write one cross-context reflection for the user.\n"
            "Describe how this thread interacts with the linked threads below.\n"
            "If two or more linked threads are present, explicitly name at least two.\n"
            "No current query to solve; focus on interplay, recurring tradeoffs, and what matters now.\n"
            "Keep it grounded in evidence and avoid generic motivation.\n\n"
            f"Mode: {request_mode}\n"
            f"Current query source: {query_source or 'none'}\n\n"
        )
    elif request_mode == "whole_story":
        preamble = (
            "Write one whole-story deep reflection reply for the user.\n"
            "Prioritize answering the current query directly.\n"
            "Use linked threads and life-dimension context only when directly relevant.\n"
            "Keep tradeoffs concrete and evidence-backed.\n"
            "Only mention emotions when clear priority-conflict evidence is present.\n\n"
            f"Mode: {request_mode}\n"
            f"Current query source: {query_source or 'none'}\n\n"
        )
    else:
        preamble = (
            "Write one deep reflection reply for the user.\n"
            "Stay strictly within the topic context below.\n"
            "Prioritize answering the current query directly.\n"
            "Use history and person context as grounding, not as a detour.\n"
            "Only mention emotions when clear priority-conflict evidence is present.\n"
            "Do not import concerns from unrelated topics or turns.\n\n"
            f"Mode: {request_mode}\n"
            f"Current query source: {query_source or 'none'}\n\n"
        )
    connected_lines: list[str] = []
    if related_topics:
        for item in related_topics:
            topic_label = str(
                item.get("topic_label") or item.get("topic_key") or ""
            ).strip()
            topic_signal = str(item.get("current_signal") or "").strip()
            topic_direction = str(item.get("direction") or "steady").strip()
            if not topic_label:
                continue
            connected_lines.append(
                f"- {topic_label}: {topic_signal or f'direction={topic_direction}'}"
            )
    if not connected_lines:
        connected_lines.append(
            "- No additional linked threads were included for this run."
        )

    connected_block = ""
    if request_mode in {"whole_story", "cross_context"}:
        connected_block = "\n\nConnected threads around this topic:\n" + "\n".join(
            connected_lines
        )

    # For whole_story: include recent verbatim turns as immediate conversational context
    recent_verbatim_turns = [
        item
        for item in (packet.get("recent_verbatim_turns") or [])
        if isinstance(item, dict) and str(item.get("text") or "").strip()
    ]
    verbatim_block = ""
    if recent_verbatim_turns and request_mode == "whole_story":
        turn_lines = [
            f"  {str(item.get('role') or 'user').capitalize()}: {str(item.get('text') or '').strip()}"
            for item in recent_verbatim_turns
        ]
        verbatim_block = (
            "\n\nRecent conversation (immediate context before this query):\n"
            + "\n".join(turn_lines)
        )

    user_prompt = (
        preamble
        + "History on this topic:\n"
        + "\n".join(history_lines)
        + "\n\nWhat we know about this person on this topic:\n"
        + "\n".join(person_lines)
        + connected_block
        + verbatim_block
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
    raw_parts.extend(
        str(item.get("facet") or "") for item in evidence if item.get("facet")
    )
    raw_parts.extend(
        str(item) for item in (deterministic.get("recurring_tensions") or [])
    )
    tokens = {
        token
        for token in _tokenize(" ".join(raw_parts))
        if len(token) > 2 and token not in _TOPIC_STOPWORDS
    }
    return tokens


def _assess_priority_conflict(
    *,
    current_query: str,
    recurring_tensions: list[str],
    open_questions: list[str],
    evidence_anchors: list[dict[str, Any]],
    recent_episodes: list[dict[str, Any]],
) -> dict[str, Any]:
    corpus_parts: list[str] = []
    if current_query:
        corpus_parts.append(current_query)
    corpus_parts.extend(recurring_tensions[:2])
    corpus_parts.extend(open_questions[:1])
    corpus_parts.extend(
        str(item.get("snippet") or "").strip() for item in evidence_anchors[:2]
    )
    corpus_parts.extend(
        str(item.get("summary") or "").strip() for item in recent_episodes[:1]
    )
    corpus = " ".join(part for part in corpus_parts if part).lower()
    query = str(current_query or "").strip().lower()
    scan_text = query or corpus

    connectors = bool(_PRIORITY_CONNECTOR_RE.search(scan_text))
    pressure = bool(_RESOURCE_PRESSURE_RE.search(scan_text))
    strong_phrase = bool(_STRONG_PRIORITY_CONFLICT_RE.search(scan_text))

    domains: set[str] = set()
    for key, pattern in _PRIORITY_DOMAIN_PATTERNS.items():
        if pattern.search(corpus):
            domains.add(key)

    conflict_detected = bool(
        strong_phrase or (connectors and pressure and len(domains) >= 2)
    )

    signals: list[str] = []
    if strong_phrase:
        signals.append("tradeoff_phrase")
    if connectors:
        signals.append("priority_connector")
    if pressure:
        signals.append("resource_pressure")
    if len(domains) >= 2:
        signals.append(f"multi_domain({','.join(sorted(domains)[:3])})")

    return {
        "detected": conflict_detected,
        "signals": signals[:4],
        "domain_count": len(domains),
    }


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


def _build_phase_packets(
    arc: dict[str, Any], included_moments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
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
        return (
            f"Started around {label}."
            if int(phase.get("index") or 0) == 0
            else f"Centered on {label}."
        )
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
            summaries.append(
                f"Phase {current['index'] + 1} shifted from {prev_label} toward {current_label}."
            )
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
    return [
        f"Recurring return to {facet.replace('_', ' ')}." for facet in recurring[:3]
    ]


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
    related_topics: list[str],
    mode: str,
    user_query: str | None,
) -> str:
    if mode == "whole_story" and str(user_query or "").strip():
        fallback_lines = [
            origin_story.strip(),
            key_pivots[0].strip() if key_pivots else "",
            current_stage.strip(),
            (
                f"Across {', '.join(related_topics[:2])}, the same tradeoff keeps resurfacing."
                if mode == "whole_story" and len(related_topics) >= 2
                else ""
            ),
            "One path worth trying: commit to a single direction for the next week and define one measurable checkpoint.",
            (
                open_questions[0].strip()
                if open_questions
                else "Set one check-in question for day seven."
            ),
        ]
        return " ".join(line for line in fallback_lines if line.strip())

    if mode == "cross_context":
        parts = [
            origin_story.strip(),
            key_pivots[0].strip() if key_pivots else "",
            current_stage.strip(),
            (
                f"Linked thread pressure is visible in {', '.join(related_topics[:2])}."
                if related_topics
                else ""
            ),
            recurring_tensions[0].strip() if recurring_tensions else "",
            (
                f"One question to hold: {open_questions[0].strip()}"
                if open_questions
                else ""
            ),
        ]
        return " ".join(part for part in parts if part)

    parts = [
        origin_story.strip(),
        key_pivots[0].strip() if key_pivots else "",
        current_stage.strip(),
        recurring_tensions[0].strip() if recurring_tensions else "",
        (
            f"One question to sit with: {open_questions[0].strip()}"
            if open_questions
            else ""
        ),
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
