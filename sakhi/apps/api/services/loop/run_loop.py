from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sakhi.libs.schemas.db import get_async_pool
from sakhi.apps.api.core.db import q

from .extract import extract_actions_and_reply
from .fast_parse import fast_parse
from .frontier import compute_frontier
from .journal import write_journal_entry
from .llm_bridge import talk_with_objective
from .policy import rank_frontier
from .verbs import dispatch_actions
from .interpret_tone import detect_tone
from ..interpret.classifier import classify_archetype
from ..interpret.controls import control_intent
from ..interpret.topic_shift import topic_shift_score
from ..memory.session_match import SIM_MATCH, SIM_MAYBE, best_match
from ..memory.session_namer import infer_slug, infer_title_from_candidates
from ..memory.session_vectors import upsert_session_vector
from ..memory.sessions import (
    append_turn,
    ensure_session,
    get_session_info,
    get_summary,
    load_recent_turns,
    set_session_title,
    set_summary,
)
from ..memory.salience import load_memories
from ..memory.summarize import roll_summary
from ..triggers.trigger_engine import compute_triggers
from ..journaling.enrich import enrich_journal_entry
from ..memory_graph.graph import build_graph_from_enrichment, reason_about_graph
from ..memory_graph.persist import persist_enrichment, persist_memory_graph

HISTORY_LIMIT = 10
SUMMARY_ROLL_EVERY = 6
SHIFT_HI = 0.55
SHIFT_LO = 0.40


async def build_context(user_id: str, session_id: str) -> Dict[str, Any]:
    now = datetime.now()
    prefs = await load_memories(user_id, kinds=["preference", "value", "goal", "constraint"])
    return {
        "now": now,
        "time_of_day": "evening",
        "preferred_time": "evening",
        "last_project_id": None,
        "user_id": user_id,
        "prefs": prefs,
    }


async def load_graph(user_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        task_rows = await conn.fetch("SELECT * FROM tasks WHERE user_id = $1", user_id)
        dependency_rows = await conn.fetch(
            """
            SELECT td.*
            FROM task_dependencies td
            WHERE EXISTS (
                SELECT 1 FROM tasks t WHERE t.id = td.task_id AND t.user_id = $1
            )
            """,
            user_id,
        )
    tasks = [dict(row) for row in task_rows]
    deps = [dict(row) for row in dependency_rows]
    return tasks, deps


async def _session_context(session_id: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    summary = await get_summary(session_id)
    history = await load_recent_turns(session_id, limit=HISTORY_LIMIT)
    info = await get_session_info(session_id)
    return summary, history, info


async def _finalize_summary(session_id: str, summary: str, history: List[Dict[str, Any]]) -> None:
    if not history:
        return
    new_summary = await roll_summary(summary, history[-HISTORY_LIMIT:])
    if new_summary:
        await set_summary(session_id, new_summary)
        info = await get_session_info(session_id)
        await upsert_session_vector(session_id, info.get("title"), new_summary)


async def pick_session_for_turn(user_id: str, current_slug: str, text: str) -> Dict[str, Any]:
    control = control_intent(text)
    current_session_id = await ensure_session(user_id, current_slug)
    summary, history, info = await _session_context(current_session_id)
    last_user_texts = [turn["text"] for turn in history if turn.get("role") == "user"]
    shift_scores = await topic_shift_score(text, summary, last_user_texts)

    switch_meta: Dict[str, Any] = {
        "switched": False,
        "reason": None,
        "to": info.get("title") or info.get("slug") or current_slug,
        "hint": SHIFT_LO <= shift_scores["shift"] < SHIFT_HI,
    }
    finalize_prev: Optional[Dict[str, Any]] = None

    if control is not None:
        if control["type"] == "switch":
            match, score = await best_match(user_id, control.get("hint", ""))
            if match and score >= SIM_MAYBE:
                session_id = match["id"]
                summary, history, info = await _session_context(session_id)
                switch_meta = {
                    "switched": session_id != current_session_id,
                    "reason": "user_switch",
                    "to": match.get("title") or match.get("slug"),
                    "hint": False,
                }
                return {
                    "session_id": session_id,
                    "summary": summary,
                    "history": history,
                    "info": info,
                    "switch": switch_meta,
                    "topic_shift": shift_scores,
                    "control": control,
                    "finalize_prev": None,
                }
            new_slug = infer_slug(control.get("hint", text))
            new_session_id = await ensure_session(user_id, new_slug)
            summary, history, info = await _session_context(new_session_id)
            switch_meta = {
                "switched": True,
                "reason": "user_new",
                "to": info.get("title") or info.get("slug") or new_slug,
                "hint": False,
            }
            return {
                "session_id": new_session_id,
                "summary": summary,
                "history": history,
                "info": info,
                "switch": switch_meta,
                "topic_shift": shift_scores,
                "control": control,
                "finalize_prev": None,
            }
        if control["type"] == "new":
            new_slug = infer_slug(text)
            new_session_id = await ensure_session(user_id, new_slug)
            summary, history, info = await _session_context(new_session_id)
            switch_meta = {
                "switched": True,
                "reason": "user_new",
                "to": info.get("title") or info.get("slug") or new_slug,
                "hint": False,
            }
            return {
                "session_id": new_session_id,
                "summary": summary,
                "history": history,
                "info": info,
                "switch": switch_meta,
                "topic_shift": shift_scores,
                "control": control,
                "finalize_prev": None,
            }

    match, score = await best_match(user_id, text)
    if match and score >= SIM_MATCH:
        session_id = match["id"]
        summary, history, info = await _session_context(session_id)
        switch_meta = {
            "switched": session_id != current_session_id,
            "reason": "auto_resume",
            "to": match.get("title") or match.get("slug"),
            "hint": False,
        }
        return {
            "session_id": session_id,
            "summary": summary,
            "history": history,
            "info": info,
            "switch": switch_meta,
            "topic_shift": shift_scores,
            "control": control,
            "finalize_prev": None,
        }

    if shift_scores["shift"] >= SHIFT_HI:
        new_slug = infer_slug(text)
        new_session_id = await ensure_session(user_id, new_slug)
        finalize_prev = {
            "session_id": current_session_id,
            "summary": summary,
            "history": history,
        }
        summary, history, info = await _session_context(new_session_id)
        switch_meta = {
            "switched": True,
            "reason": "auto_new",
            "to": info.get("title") or info.get("slug") or new_slug,
            "hint": False,
        }
        return {
            "session_id": new_session_id,
            "summary": summary,
            "history": history,
            "info": info,
            "switch": switch_meta,
            "topic_shift": shift_scores,
            "control": control,
            "finalize_prev": finalize_prev,
        }

    return {
        "session_id": current_session_id,
        "summary": summary,
        "history": history,
        "info": info,
        "switch": switch_meta,
        "topic_shift": shift_scores,
        "control": control,
        "finalize_prev": None,
    }


async def run_loop(
    user_id: str,
    text: str,
    session_slug: str = "journal",
    clarity_hint: str | None = None,
) -> Dict[str, Any]:
    pick = await pick_session_for_turn(user_id, session_slug, text)

    session_id = pick["session_id"]
    summary = pick["summary"]
    history = pick["history"]
    info = pick["info"]
    switch_meta = pick["switch"]
    topic_shift_meta = pick["topic_shift"]
    control = pick["control"]

    finalize_prev = pick.get("finalize_prev")
    if finalize_prev:
        await _finalize_summary(
            finalize_prev["session_id"],
            finalize_prev.get("summary", ""),
            finalize_prev.get("history", []),
        )

    tone_info = detect_tone(text)
    mode = classify_archetype(text, summary)

    await append_turn(
        user_id=user_id,
        session_id=session_id,
        role="user",
        text=text,
        tone=tone_info.get("tone"),
        archetype=mode,
    )

    history = await load_recent_turns(session_id, limit=HISTORY_LIMIT)
    context = await build_context(user_id, session_id)
    context.update(
        {
            "tone": tone_info.get("tone"),
            "mood": tone_info.get("mood"),
            "archetype": mode,
            "summary": summary,
            "history": history,
            "topic_shift": topic_shift_meta,
        }
    )
    try:
        reflection_row = await q(
            """
            SELECT summary
            FROM meta_reflections
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
        )
        if reflection_row:
            context["reflection_summary"] = reflection_row[0]["summary"]
    except Exception:
        context["reflection_summary"] = context.get("reflection_summary")

    objective = (
        "Move toward a concrete next step or meaningful reflection, "
        "asking at most one critical slot."
    )

    parsed, confidence = fast_parse(text)
    intents_payload: List[Dict[str, Any]] = []
    parsed_kind = getattr(parsed, "kind", None)
    if parsed_kind and parsed_kind != "none":
        intents_payload.append({"intent_type": parsed_kind, "raw": text})
    reply: Optional[str] = None
    confirmations: List[str] = []
    assistant_archetype = mode
    actions: Optional[List[Dict[str, Any]]] = None

    decisions: List[Dict[str, Any]] = []

    def log_decision(stage: str, summary: str, **extra: Any) -> None:
        decisions.append({"stage": stage, "summary": summary, **extra})

    log_decision(
        "intent.parse",
        "Parsed intent from the message.",
        parsed=parsed.model_dump() if hasattr(parsed, "model_dump") else repr(parsed),
        confidence=confidence,
    )

    if confidence >= 0.85 and parsed.kind != "none":
        actions = [action.model_dump() for action in parsed.to_actions()]
        confirmations = await dispatch_actions(user_id, actions)
        reply = None
        log_decision(
            "intent.auto_actions",
            "Confidence high, executing structured actions without LLM reply.",
            actions=actions,
        )
    else:
        llm_out = await talk_with_objective(
            user_id,
            text,
            context,
            objective,
            clarity_hint=clarity_hint,
        )
        log_decision(
            "llm.reply",
            "Called the assistant LLM to craft the reply.",
            clarity_hint=clarity_hint,
        )
        reply, actions = extract_actions_and_reply(llm_out)
        if actions:
            confirmations = await dispatch_actions(user_id, actions)
            if any(action.get("type") in {"log_journal", "summarize_reflection"} for action in actions):
                assistant_archetype = "reflect"
            elif any(action.get("type") == "search_entities" for action in actions):
                assistant_archetype = "research"
            else:
                assistant_archetype = "act"
            log_decision(
                "llm.actions",
                "LLM suggested actions that were dispatched.",
                actions=actions,
            )
        else:
            assistant_archetype = "dialog"
            log_decision("llm.dialog", "LLM produced a dialogue response without actions.")

    if actions:
        for action in actions:
            intents_payload.append(
                {
                    "intent_type": action.get("type"),
                    "raw": action,
                }
            )

    auto_title_assigned: Optional[str] = None

    if control and control.get("type") == "title" and control.get("title"):
        title_text = control["title"]
        await set_session_title(session_id, title_text)
        confirmations.insert(0, f"Titled this session “{title_text}”.")
        info["title"] = title_text
        await upsert_session_vector(session_id, title_text, summary)
        log_decision("session.title", "Applied explicit title from control signal.", title=title_text)
    elif control and control.get("type") == "bookmark":
        confirmations.insert(0, "Bookmarked this moment.")
        log_decision("session.bookmark", "Marked this turn as bookmarked.")
    elif not info.get("title"):
        candidate_texts: List[str] = []
        first_user_turn = next((turn.get("text") for turn in history if turn.get("role") == "user"), None)
        if first_user_turn:
            candidate_texts.append(first_user_turn)
        candidate_texts.append(text)
        if summary:
            candidate_texts.append(summary)
        auto_title = infer_title_from_candidates(candidate_texts, info.get("slug") or session_slug)
        if auto_title:
            await set_session_title(session_id, auto_title)
            info["title"] = auto_title
            auto_title_assigned = auto_title
            await upsert_session_vector(session_id, auto_title, summary)
            log_decision("session.auto_title", "Auto-titled session based on recent text.", title=auto_title)

    if switch_meta.get("hint") and (reply is None or reply.strip()):
        hint_text = "(If this feels like a new topic, we can start a fresh space anytime.)"
        if reply:
            reply = reply.strip()
            if hint_text not in reply:
                reply = f"{reply}\n\n{hint_text}"
        else:
            reply = hint_text
        log_decision("topic.hint", "Appended topic-switch hint to the reply.")

    need_title_prompt = False

    await append_turn(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        text=reply or "",
        tone=None,
        archetype=assistant_archetype,
    )
    log_decision("memory.append_turn", "Recorded assistant turn in session history.")

    history = await load_recent_turns(session_id, limit=HISTORY_LIMIT)

    tasks, deps = await load_graph(user_id)
    frontier = compute_frontier(tasks, deps)
    ranked = rank_frontier(frontier, context, {})
    frontier_top = [task.get("title") for task in ranked[:3]]
    log_decision("frontier.rank", "Ranked tasks to surface top suggestions.", suggestions=frontier_top)

    assistant_turns = [turn for turn in history if turn.get("role") == "assistant"]
    if assistant_turns and len(assistant_turns) % SUMMARY_ROLL_EVERY == 0:
        new_summary = await roll_summary(summary, history)
        if new_summary:
            await set_summary(session_id, new_summary)
            summary = new_summary
            await upsert_session_vector(session_id, info.get("title"), summary)

    journal_entry_id = await write_journal_entry(user_id, text, reply)
    log_decision("memory.journal_entry", "Persisted this turn in the journal store.")

    enrichment = await enrich_journal_entry(text, person_id=user_id)
    journal_entry_payload = {"content": text, "kind": "loop"}
    trigger_flags = await compute_triggers(
        person_id=user_id,
        intents=intents_payload,
        journal_entry=journal_entry_payload,
        mood=tone_info.get("mood"),
    )

    memory_graph = build_graph_from_enrichment(enrichment)
    reasoning = reason_about_graph(memory_graph)

    result = {
        "reply": reply,
        "confirmations": confirmations,
        "suggestions": frontier_top,
        "frontierTop3": frontier_top,
        "lastObjective": objective,
        "tone": tone_info.get("tone"),
        "mood": tone_info.get("mood"),
        "archetype": assistant_archetype,
        "usedSummary": bool(summary),
        "historyCount": len(history),
        "sessionId": session_id,
        "sessionSlug": info.get("slug") or session_slug,
        "sessionTitle": info.get("title"),
        "topicShift": topic_shift_meta,
        "switch": switch_meta,
        "titlePrompted": need_title_prompt,
        "autoTitle": auto_title_assigned,
        "clarityHint": clarity_hint,
        "decisions": decisions,
    }
    result["triggers"] = trigger_flags
    result["enrichment"] = enrichment
    result["memory_graph"] = memory_graph
    result["memory_reasoning"] = reasoning

    try:
        if journal_entry_id:
            await persist_enrichment(journal_entry_id, enrichment)
        await persist_memory_graph(user_id, memory_graph)
    except Exception as exc:  # pragma: no cover - persistence best effort
        LOGGER.error("[Patch V] Enrichment persistence failed: %s", exc)
    return result
LOGGER = logging.getLogger(__name__)
