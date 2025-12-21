from __future__ import annotations

import logging
import json
from typing import Any, Dict

from sakhi.apps.api.services.planner.extract import extract_intents
from sakhi.apps.api.services.planner.rank import rank_intents
from sakhi.apps.api.services.planner.commit import update_existing_plans
from sakhi.apps.api.services.planner.decompose import build_plan_graph
from sakhi.apps.api.services.planner.cache import refresh_planner_cache
from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.api.services.memory.recall import build_recall_context

LOGGER = logging.getLogger(__name__)


async def planner_suggest(person_id: str, text: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    intents = await extract_intents(person_id, text)
    ranked = await rank_intents(person_id, intents)
    recall_ctx = await build_recall_context(person_id, text)
    plan_graph = build_plan_graph(person_id, ranked)
    return {
        "intents": ranked,
        "suggestions": plan_graph.get("tasks", []),
        "plan_graph": plan_graph,
        "recall_context": recall_ctx,
    }


async def planner_commit(person_id: str, plan_payload: Dict[str, Any]) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    details = await update_existing_plans(person_id, plan_payload)
    await refresh_planner_cache(person_id)
    return {"status": "ok", "details": details}


async def planner_summary(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT payload
        FROM planner_context_cache
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if row:
        payload_raw = row["payload"] or {}
        if isinstance(payload_raw, dict):
            payload = dict(payload_raw)
        elif isinstance(payload_raw, str):
            payload = json.loads(payload_raw)
        else:
            payload = dict(payload_raw)
        payload["source"] = "cache"
        payload["rhythm_alignment"] = await _fetch_rhythm_alignment(person_id)
        return payload

    payload = await refresh_planner_cache(person_id)
    payload["source"] = "fresh"
    payload["rhythm_alignment"] = await _fetch_rhythm_alignment(person_id)
    return payload


async def _fetch_rhythm_alignment(person_id: str) -> Dict[str, Any]:
    rows = await q(
        """
        SELECT horizon, recommendations, generated_at
        FROM rhythm_planner_alignment
        WHERE person_id = $1
        ORDER BY generated_at DESC
        """,
        person_id,
    )
    alignment: Dict[str, Any] = {}
    for row in rows:
        recs = row["recommendations"]
        if isinstance(recs, str):
            try:
                recs = json.loads(recs)
            except json.JSONDecodeError:
                recs = row["recommendations"]
        alignment[row["horizon"]] = {
            "recommendations": recs,
            "generated_at": row["generated_at"],
        }
    return alignment


__all__ = ["planner_suggest", "planner_commit", "planner_summary"]
