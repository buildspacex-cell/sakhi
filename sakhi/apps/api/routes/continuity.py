from __future__ import annotations

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
