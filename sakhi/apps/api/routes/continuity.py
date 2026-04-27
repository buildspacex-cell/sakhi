from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from sakhi.apps.api.services.continuity import (
    CONTINUITY_SCOPE,
    enable_continuity_policy,
    exclude_continuity_ref,
    get_continuity_arc,
    get_continuity_policy,
    get_continuity_topics,
    upsert_continuity_label,
    upsert_continuity_policy,
)
from sakhi.apps.api.services.continuity.reflection import (
    create_deep_reflection_job,
    get_deep_reflection_result,
    get_deep_reflection_status,
)
from sakhi.apps.api.utils.person_resolver import resolve_person

router = APIRouter(prefix="/continuity", tags=["continuity"])


def _load_continuation_prompt_handler():
    """Resolve lazily so a missing helper doesn't crash API startup."""
    from sakhi.apps.api.services.continuity import service as continuity_service

    handler = getattr(continuity_service, "get_continuation_prompt", None)
    if handler is None:
        raise LookupError("Continuation prompt handler is unavailable in this deployment.")
    return handler


class ContinuityPolicyRequest(BaseModel):
    person_id: str
    enabled: bool = False
    scope: str = Field(default=CONTINUITY_SCOPE)
    exclusions: list[dict[str, Any]] = Field(default_factory=list)


class ContinuityLabelRequest(BaseModel):
    person_id: str
    source_id: str
    source_type: str = "journal"
    anchor: str
    facets: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    scalar: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContinuityPolicyEnableRequest(BaseModel):
    person_id: str
    scope: str = Field(default=CONTINUITY_SCOPE)


class ContinuityPolicyExcludeRequest(BaseModel):
    person_id: str
    source_ref: str
    scope: str = Field(default=CONTINUITY_SCOPE)


class ContinuityReflectionRunRequest(BaseModel):
    person_id: str
    topic_key: str
    window: str = "3650d"
    mode: Literal["topic_reflection", "whole_story", "cross_context"] = "topic_reflection"
    topic_keys: list[str] = Field(default_factory=list)
    user_query: str | None = None


@router.get("/prompt")
async def get_continuation_prompt_route(
    request: Request,
    person_id: str,
):
    """Return a return-visit continuation card for the app home screen."""
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    try:
        continuation_prompt = _load_continuation_prompt_handler()
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return await continuation_prompt(resolved_person_id)


@router.get("/policy")
async def get_continuity_policy_route(
    request: Request,
    person_id: str,
    scope: str = CONTINUITY_SCOPE,
):
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    policy = await get_continuity_policy(resolved_person_id, scope)
    return {
        "person_id": resolved_person_id,
        "scope": scope,
        "enabled": bool(policy.get("enabled")),
        "exclusions": policy.get("exclusions") or [],
    }


@router.put("/policy")
async def put_continuity_policy(request: Request, body: ContinuityPolicyRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    return await upsert_continuity_policy(
        resolved_person_id,
        scope=body.scope,
        enabled=body.enabled,
        exclusions=body.exclusions,
    )


@router.post("/policy/enable")
async def post_continuity_policy_enable(request: Request, body: ContinuityPolicyEnableRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    return await enable_continuity_policy(resolved_person_id, scope=body.scope)


@router.post("/policy/exclude")
async def post_continuity_policy_exclude(request: Request, body: ContinuityPolicyExcludeRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    return await exclude_continuity_ref(
        resolved_person_id,
        body.source_ref,
        scope=body.scope,
    )


@router.post("/label")
async def post_continuity_label(request: Request, body: ContinuityLabelRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    return await upsert_continuity_label(
        resolved_person_id,
        source_id=body.source_id,
        source_type=body.source_type,
        anchor=body.anchor,
        facets=body.facets,
        entities=body.entities,
        scalar=body.scalar,
        metadata=body.metadata,
    )


@router.get("/topics")
async def get_continuity_topics_route(
    request: Request,
    person_id: str,
    window: str = "120d",
    debug: int = 0,
):
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    try:
        return await get_continuity_topics(
            resolved_person_id,
            window=window,
            debug=bool(debug),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/arc")
async def get_continuity_arc_route(
    request: Request,
    person_id: str,
    anchor: str,
    window: str = "90d",
    max_gap_days: int = 21,
    min_len: int = 3,
    debug: int = 0,
):
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    try:
        return await get_continuity_arc(
            resolved_person_id,
            anchor,
            window=window,
            max_gap_days=max_gap_days,
            min_len=min_len,
            debug=bool(debug),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reflection/run")
async def post_continuity_reflection_run(request: Request, body: ContinuityReflectionRunRequest):
    resolved_person_id, _, _ = await resolve_person(request, body.person_id)
    try:
        user_query = str(body.user_query or "").strip() or None
        return await create_deep_reflection_job(
            resolved_person_id,
            body.topic_key,
            window=body.window,
            mode=body.mode,
            topic_keys=body.topic_keys,
            user_query=user_query,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reflection/status")
async def get_continuity_reflection_status_route(
    request: Request,
    id: str,
    person_id: str | None = Query(default=None),
):
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    try:
        return await get_deep_reflection_status(id, resolved_person_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/open-loops")
async def get_open_loops_route(
    request: Request,
    person_id: str,
    status: str = "open",
):
    """Return the open loops ledger for a person, split by type."""
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    from sakhi.apps.api.services.continuity.loops import get_open_loops

    loops = await get_open_loops(resolved_person_id, status=status)
    return {
        "person_id": resolved_person_id,
        "status": status,
        "decisions": loops.get("decisions", []),
        "commitments": loops.get("commitments", []),
        "total": len(loops.get("decisions", [])) + len(loops.get("commitments", [])),
    }


@router.post("/open-loops/{loop_id}/resolve")
async def resolve_open_loop_route(
    loop_id: str,
    request: Request,
    person_id: str | None = Query(default=None),
):
    """Mark a loop as resolved (e.g. user dismissed it from the UI)."""
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    from sakhi.apps.api.services.continuity.loops import resolve_loop

    await resolve_loop(loop_id)
    return {"loop_id": loop_id, "status": "resolved"}


@router.get("/morning-review")
async def get_morning_review_route(
    request: Request,
    person_id: str,
):
    """Return structured Today's Review payload: what changed, one thing, think, act."""
    from datetime import datetime, timezone

    from sakhi.apps.api.services.continuity.loops import get_open_loops
    from sakhi.apps.api.services.continuity.stance import get_morning_stance_shift

    resolved_person_id, _, _ = await resolve_person(request, person_id)

    loops, what_changed = await asyncio.gather(
        get_open_loops(resolved_person_id),
        get_morning_stance_shift(resolved_person_id),
        return_exceptions=True,
    )
    if isinstance(loops, Exception):
        loops = {"decisions": [], "commitments": []}
    if isinstance(what_changed, Exception):
        what_changed = None

    decisions = loops.get("decisions", [])
    commitments = loops.get("commitments", [])

    # "One Thing" — oldest unresolved decision first (most stale = highest priority to confront)
    one_thing = None
    if decisions:
        oldest = sorted(decisions, key=lambda x: x.get("first_raised_at") or "")
        loop = oldest[0]
        first_raised = loop.get("first_raised_at")
        days_open = 0
        if first_raised:
            try:
                raised_dt = datetime.fromisoformat(first_raised.replace("Z", "+00:00"))
                days_open = (datetime.now(timezone.utc) - raised_dt).days
            except Exception:
                pass
        one_thing = {
            "id": loop["id"],
            "topic": loop["topic"],
            "loop_type": loop.get("loop_type", "open_decision"),
            "days_open": days_open,
        }

    hour = datetime.now(timezone.utc).hour
    if hour < 12:
        time_of_day = "morning"
    elif hour < 17:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"

    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "time_of_day": time_of_day,
        "what_changed": what_changed,
        "one_thing": one_thing,
        "think": decisions[:3],
        "act": commitments[:3],
        "total_open": len(decisions) + len(commitments),
    }


@router.get("/paywall-status")
async def get_paywall_status_route(
    request: Request,
    person_id: str,
):
    """Return whether to show the upgrade CTA based on usage thresholds.

    Thresholds (free tier):
      - 20 total conversation turns  →  trigger = "turns"
      - 3 open loops surfaced        →  trigger = "loops"

    No DB subscription column yet — tier is always 'free'. Once payment
    is integrated, add subscription_tier to auth_users and check it here.
    """
    from sakhi.apps.api.core.db import q as dbfetch
    from sakhi.apps.api.services.continuity.loops import get_open_loops

    FREE_TURN_THRESHOLD = 20
    FREE_LOOPS_THRESHOLD = 3

    resolved_person_id, _, _ = await resolve_person(request, person_id)

    turn_count_result, loops = await asyncio.gather(
        dbfetch(
            """
            SELECT COALESCE(SUM(turn_count), 0) AS total_turns
            FROM conversation_sessions
            WHERE user_id = $1
            """,
            resolved_person_id,
        ),
        get_open_loops(resolved_person_id),
        return_exceptions=True,
    )

    turn_count = 0
    if not isinstance(turn_count_result, Exception) and turn_count_result:
        turn_count = int(turn_count_result[0]["total_turns"] or 0)

    loops_count = 0
    if not isinstance(loops, Exception):
        loops_count = len(loops.get("decisions", [])) + len(loops.get("commitments", []))

    trigger = None
    if turn_count >= FREE_TURN_THRESHOLD:
        trigger = "turns"
    elif loops_count >= FREE_LOOPS_THRESHOLD:
        trigger = "loops"

    return {
        "tier": "free",
        "show_upgrade_cta": trigger is not None,
        "trigger": trigger,
        "turn_count": turn_count,
        "loops_count": loops_count,
        "thresholds": {
            "turns": FREE_TURN_THRESHOLD,
            "loops": FREE_LOOPS_THRESHOLD,
        },
    }


@router.get("/reflection/result")
async def get_continuity_reflection_result_route(
    request: Request,
    id: str,
    person_id: str | None = Query(default=None),
):
    resolved_person_id, _, _ = await resolve_person(request, person_id)
    try:
        return await get_deep_reflection_result(id, resolved_person_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
