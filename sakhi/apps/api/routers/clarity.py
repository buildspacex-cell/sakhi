from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sakhi.apps.api.clarity.hcb import build_context_pack
from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.metrics import aw_events_written, derivatives_written
from sakhi.apps.api.core.persons import ensure_person_id
from sakhi.apps.api.core.trace import Trace
from sakhi.apps.api.core.trace_store import persist_trace
from sakhi.apps.api.services.debug import DebugFlow, trace_id_var
from sakhi.apps.api.services.explain import summarize_layers
from sakhi.apps.api.services.memory.personal_model import update_personal_model

router = APIRouter(prefix="/clarity", tags=["clarity"])


class EvaluateIn(BaseModel):
    person_id: str | None = None
    user_text: str
    need: str = "plan"
    horizon: str = "week"


@router.post("/evaluate")
async def evaluate(body: EvaluateIn) -> dict:
    base_ref = body.person_id or os.getenv("DEMO_USER_ID")
    person_id = await ensure_person_id(base_ref)

    trace = Trace(person_id=person_id, flow="clarity")
    dbg = DebugFlow(trace_id=trace.trace_id, person_id=person_id)
    token = trace_id_var.set(trace.trace_id)

    pack = await build_context_pack(body.user_text, body.need, body.horizon, person_id)

    context_obj = pack.get("context") if isinstance(pack.get("context"), dict) else {}
    context_support = context_obj.get("support") or {}
    themes_payload = pack.get("themes") if isinstance(pack.get("themes"), list) else []
    theme_names = [t.get("theme") for t in themes_payload if isinstance(t, dict) and t.get("theme")]

    context_summary_text = "Assembled the planning context from recent themes and notes."
    if theme_names:
        preview = ", ".join(theme_names[:2])
        if len(theme_names) > 2:
            preview += ", ..."
        context_summary_text = f"Focused the planning context around themes like {preview}."

    recent_notes_text = context_obj.get("recent_notes") or pack.get("recent_notes")
    if isinstance(recent_notes_text, str) and recent_notes_text.strip():
        context_summary_text += " Included the latest journal highlights."

    avg_mood_value = context_support.get("avg_mood_7d")
    if isinstance(avg_mood_value, (int, float)):
        if avg_mood_value >= 0.7:
            context_summary_text += " Energy signals look upbeat."
        elif avg_mood_value >= 0.4:
            context_summary_text += " Energy signals look steady."
        else:
            context_summary_text += " Energy looks low, so we respond gently."

    trace.add(
        "clarity.context",
        "Built context pack",
        {
            "context": pack["context"],
            "anchors": pack["anchors"],
            "person_summary": pack["person_summary"],
            "summary_text": context_summary_text,
        },
        explanation="Pulled person history, themes, and anchors to understand what they care about right now.",
    )
    state_vector = pack["context"].get("state_vector") if isinstance(pack.get("context"), dict) else None
    if state_vector:
        confidence_val = state_vector.get("confidence")
        state_summary_text = (
            f"Confidence we are on the right topic is {(confidence_val * 100):.0f}%."
            if isinstance(confidence_val, (int, float))
            else "Blended the readiness signal from the state model."
        )
        trace.add(
            "clarity.state_vector",
            "State vector applied",
            {
                "state_vector": state_vector,
                "summary_text": state_summary_text,
            },
            decision=f"confidence={state_vector.get('confidence')}",
            explanation=f"Blended the readiness signal (confidence {state_vector.get('confidence')}) into the planning context.",
        )

    phrase_payload = pack.get("phrase") or {}
    phrase_meta = phrase_payload.get("meta") or {}
    phrase_lines = phrase_payload.get("lines") or []
    if phrase_meta.get("skipped"):
        reason = phrase_meta.get("reason") or "policy"
        if reason == "phrase_confidence_low":
            phrase_summary_text = "Held back on a phrase because its confidence score was low."
        elif reason == "state_confidence_low":
            phrase_summary_text = "Stayed quiet because the readiness model asked us to listen longer."
        elif reason == "duplicate_recent":
            phrase_summary_text = "Skipped a duplicate phrase that was suggested recently."
        elif reason == "max_suggestions_window":
            phrase_summary_text = "Paused new phrases so the last suggestion has time to land."
        elif reason == "llm_error":
            phrase_summary_text = "The phrase generator hit an error, so nothing was delivered."
        else:
            phrase_summary_text = "Chose not to send a companion phrase this turn."
    elif phrase_lines:
        phrase_summary_text = f'Shared a companion phrase: "{phrase_lines[0]}"'
    else:
        phrase_summary_text = "Delivered a companion phrase for this turn."

    trace.add(
        "clarity.phrase",
        "Phrase policy outcome",
        {
            "phrase": phrase_payload,
            "summary_text": phrase_summary_text,
        },
        decision=(phrase_payload.get("meta") or {}).get("reason") or "unknown",
        explanation="Evaluated whether to offer a companion phrase and captured the policy decision.",
    )

    llm_payload = pack.get("llm", {})
    phrase = pack.get("phrase")

    def _mood_label(score: Any) -> str | None:
        if not isinstance(score, (int, float)):
            return None
        if score >= 0.7:
            return "optimistic"
        if score >= 0.4:
            return "steady"
        if score >= 0.2:
            return "concerned"
        return "depleted"

    themes_list = [
        t.get("theme")
        for t in pack.get("themes", [])
        if isinstance(t, dict) and t.get("theme")
    ]
    mood_score = context_support.get("avg_mood_7d")
    clarity_summary = {
        "intent": body.need,
        "focus": theme_names[:2],
        "emotion": _mood_label(mood_score),
        "state_confidence": state_vector.get("confidence") if isinstance(state_vector, dict) else None,
        "time_scope": body.horizon,
        "anchors": pack.get("anchors"),
        "user_text": body.user_text,
    }
    clarity_summary = {k: v for k, v in clarity_summary.items() if v not in (None, [], {})}
    personal_model_payload: Dict[str, Any] = {}
    if clarity_summary:
        personal_model_payload = await update_personal_model(person_id, clarity_summary)
        trace.add(
            "memory.personal_model",
            "Updated layered personal model",
            {
                "keys": list(clarity_summary.keys()),
                "summary_text": "Merged clarity insight into personal model layers.",
            },
        )
        dbg.add(
            "memory.personal_model",
            "Updated layered personal model",
            {"keys": list(clarity_summary.keys())},
        )

    trace.add(
        "spine",
        "Pipeline spine executed",
        {
            "steps": [
                "observe",
                "clarity",
                "personal_model",
                "prompt_builder",
                "llm.chat",
                "observe",
            ]
        },
    )
    trace_payload = trace.to_dict()
    trace_payload["person_id"] = person_id
    trace_payload["flow"] = "clarity"
    await persist_trace(trace_payload)

    provenance = {
        "episodes": (
            await q(
                """
                SELECT COUNT(*) AS c
                FROM aw_event
                WHERE person_id = $1
                  AND ts > NOW() - INTERVAL '30 days'
                """,
                person_id,
                one=True,
            )
        )["c"],
        "derivatives": (
            await q(
                """
                SELECT COUNT(*) AS c
                FROM insight
                WHERE person_id = $1
                  AND ts > NOW() - INTERVAL '30 days'
                """,
                person_id,
                one=True,
            )
        )["c"],
    }
    pack.setdefault("anchors", {})["provenance"] = provenance

    debug_payload: Dict[str, Any] = {"trace": trace_payload}
    debug_payload.update(pack)
    if "trace_id" not in debug_payload:
        debug_payload["trace_id"] = trace_payload.get("trace_id")
    human_narrative, layer_summaries = summarize_layers(trace_payload.get("steps", []))
    debug_payload["human_narrative"] = human_narrative
    debug_payload["plain_layers"] = layer_summaries
    if personal_model_payload:
        debug_payload["personal_model"] = personal_model_payload.get("data")
        debug_payload["personal_model_full"] = personal_model_payload
    debug_payload["spine"] = [
        "observe",
        "clarity",
        "personal_model",
        "prompt_builder",
        "llm.chat",
        "observe",
    ]

    options = llm_payload.get("options", [])
    anchors = pack.get("anchors") or {}
    message = f"Generated plan with {len(options)} options for need={body.need}, horizon={body.horizon}"
    insight_id = f"ins_{uuid.uuid4().hex}"
    confidence = anchors.get("overall_confidence", 0.0)
    why_json = json.dumps({"anchors": anchors}, ensure_ascii=False)
    actions_json = json.dumps({"options": options}, ensure_ascii=False)
    await q(
        """
        INSERT INTO insight(id, person_id, from_ids, kind, message, why, actions, confidence)
        VALUES ($1, $2, $3, 'plan', $4, $5::jsonb, $6::jsonb, $7)
        """,
        insight_id,
        person_id,
        [],
        message,
        why_json,
        actions_json,
        confidence,
    )
    derivatives_written.inc()

    aw_event_id = f"evt_{uuid.uuid4().hex}"
    payload_json = json.dumps({"insight_id": insight_id, "message": message}, ensure_ascii=False)
    context_json = json.dumps({"device": "server", "tz": "Asia/Kolkata", "privacy_flags": ["no_xfer"]}, ensure_ascii=False)
    await q(
        """
        INSERT INTO aw_event(id, actor, modality, person_id, payload, context_json, schema_version, hash)
        VALUES ($1, 'sakhi', 'thought', $2, $3::jsonb, $4::jsonb, 'aw_1', $5)
        """,
        aw_event_id,
        person_id,
        payload_json,
        context_json,
        f"insight:{insight_id}",
    )
    aw_events_written.inc()

    await q(
        "INSERT INTO aw_edge(src_id, dst_id, kind) VALUES ($1, $2, 'reflects') ON CONFLICT DO NOTHING",
        insight_id,
        aw_event_id,
    )
    receipts = [
        {"kind": "insight", "insight_id": insight_id},
        {"kind": "aw_event", "event_id": aw_event_id},
    ]
    dbg.events = trace_payload.get("steps", [])

    await dbg.finish(True, {"insight_id": insight_id, "receipts": receipts})

    response_payload = {
        "context": pack["context"],
        "impact_panel": pack["anchors"],
        "options": llm_payload.get("options", []),
        "notes": llm_payload.get("notes", []),
        "clarifications": llm_payload.get("clarifications", []),
        "risk_flags": llm_payload.get("risk_flags", []),
        "phrase": phrase,
        "person_summary": pack.get("person_summary"),
        "debug": debug_payload,
        "insight_id": insight_id,
        "spine": debug_payload.get("spine"),
    }
    if personal_model_payload:
        response_payload["personal_model"] = personal_model_payload.get("data")
        response_payload["personal_model_full"] = personal_model_payload

    trace_id_var.reset(token)
    return JSONResponse(response_payload, headers={"x-trace-id": trace.trace_id})
