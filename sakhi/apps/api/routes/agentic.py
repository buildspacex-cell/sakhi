"""
Agentic API Routes
------------------
Endpoints for agentic capabilities (search, tasks, research).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from sakhi.apps.api.core.event_logger import log_event
from sakhi.apps.api.services.agentic.search import (
    web_search,
    news_search,
    fetch_url,
    summarize_search_results,
)
from sakhi.apps.api.services.agentic.tools import (
    get_available_tools,
    get_tool_by_name,
    execute_tool,
)
from sakhi.apps.api.services.agentic.planner import (
    create_task_plan,
    get_task_plan,
    approve_task_plan,
    cancel_task_plan,
    get_active_plans,
)
from sakhi.apps.api.services.agentic.recurring import (
    RecurringRunLog,
    RecurringSchedule,
    approve_recurring_schedule,
    cancel_recurring_schedule,
    create_recurring_schedule,
    get_recurring_schedule,
    get_recurring_schedule_runs,
    list_recurring_schedules,
    run_recurring_schedule_now,
)
from sakhi.apps.api.services.agentic.research import (
    start_research,
    get_research_session,
    expand_research,
    synthesize_research,
    get_active_research,
)

router = APIRouter(prefix="/api/v1/agent", tags=["agentic"])
LOGGER = logging.getLogger(__name__)


async def _log_stage2_event(
    person_id: Optional[str],
    event: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort Stage 2 funnel event logging."""
    if not person_id:
        return
    try:
        await log_event(
            person_id=person_id,
            layer="stage2_outer_action",
            event=event,
            payload=payload or {},
        )
    except Exception as exc:
        LOGGER.debug("[agentic] stage2 event log failed: %s", exc)


# =============================================================================
# Request/Response Models
# =============================================================================

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5
    include_summary: bool = True


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    summary: Optional[str] = None
    cached: bool = False


class FetchRequest(BaseModel):
    url: str
    extract_content: bool = True


class TaskRequest(BaseModel):
    task: str
    auto_execute: bool = False


class TaskResponse(BaseModel):
    plan_id: str
    status: str
    goal: str
    steps: List[Dict[str, Any]]
    requires_approval: bool
    final_output: Optional[str] = None


class ResearchRequest(BaseModel):
    topic: str
    question: Optional[str] = None
    auto_search: bool = True


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = {}


class RecurringScheduleRequest(BaseModel):
    task: str
    goal_hint: Optional[str] = None
    cadence: str = "monthly"
    cadence_interval: int = 1
    run_timezone: str = "UTC"
    day_of_month: int = 1
    run_hour: int = 9
    run_minute: int = 0
    metadata: Dict[str, Any] = {}


def _serialize_task_response(plan: Any) -> TaskResponse:
    return TaskResponse(
        plan_id=plan.id,
        status=plan.status.value,
        goal=plan.goal,
        steps=[s.model_dump() for s in plan.steps],
        requires_approval=plan.status.value == "pending_approval",
        final_output=plan.final_output,
    )


def _serialize_recurring_schedule(schedule: RecurringSchedule) -> Dict[str, Any]:
    return {
        "schedule_id": schedule.id,
        "person_id": schedule.person_id,
        "task_description": schedule.task_description,
        "goal_hint": schedule.goal_hint,
        "cadence": schedule.cadence,
        "cadence_interval": schedule.cadence_interval,
        "run_timezone": schedule.run_timezone,
        "day_of_month": schedule.day_of_month,
        "run_hour": schedule.run_hour,
        "run_minute": schedule.run_minute,
        "status": schedule.status.value,
        "is_running": schedule.is_running,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        "last_run_status": schedule.last_run_status,
        "consecutive_failures": schedule.consecutive_failures,
        "created_plan_id": schedule.created_plan_id,
        "latest_plan_id": schedule.latest_plan_id,
        "metadata": schedule.metadata,
    }


def _serialize_recurring_run(run: RecurringRunLog) -> Dict[str, Any]:
    return {
        "id": run.id,
        "schedule_id": run.schedule_id,
        "person_id": run.person_id,
        "plan_id": run.plan_id,
        "trigger_source": run.trigger_source,
        "status": run.status.value,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "summary": run.summary,
        "error": run.error,
        "metadata": run.metadata,
    }


# =============================================================================
# Search Endpoints
# =============================================================================

@router.post("/search", response_model=SearchResponse)
async def search_web(
    request: SearchRequest,
    person_id: str = Query(...),
):
    """Search the web for information."""
    results = await web_search(request.query, request.max_results)

    summary = None
    if request.include_summary and results.results:
        summary = await summarize_search_results(results.results, request.query)

    return SearchResponse(
        query=results.query,
        results=[r.model_dump() for r in results.results],
        summary=summary,
        cached=results.cached,
    )


@router.post("/search/news", response_model=SearchResponse)
async def search_news(
    request: SearchRequest,
    person_id: str = Query(...),
):
    """Search for recent news articles."""
    results = await news_search(request.query, request.max_results)

    summary = None
    if request.include_summary and results.results:
        summary = await summarize_search_results(results.results, request.query)

    return SearchResponse(
        query=results.query,
        results=[r.model_dump() for r in results.results],
        summary=summary,
        cached=results.cached,
    )


@router.post("/fetch")
async def fetch_page(request: FetchRequest):
    """Fetch content from a URL."""
    result = await fetch_url(request.url, request.extract_content)
    return result


# =============================================================================
# Tool Endpoints
# =============================================================================

@router.get("/tools")
async def list_tools(person_id: str = Query(...)):
    """List available tools for the user."""
    tools = await get_available_tools(person_id)
    return {
        "tools": [t.model_dump() for t in tools],
        "count": len(tools),
    }


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get details for a specific tool."""
    tool = await get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(404, f"Tool not found: {tool_name}")
    return tool.model_dump()


@router.post("/tools/execute")
async def execute_tool_endpoint(
    request: ToolExecuteRequest,
    person_id: str = Query(...),
):
    """Execute a tool."""
    result = await execute_tool(
        person_id=person_id,
        tool_name=request.tool_name,
        parameters=request.parameters,
    )

    if not result.success and result.error == "Tool requires user approval":
        raise HTTPException(403, "Tool requires user approval")

    return result.model_dump()


# =============================================================================
# Task Planning Endpoints
# =============================================================================

@router.post("/task", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    person_id: str = Query(...),
    session_id: Optional[str] = Query(None),
):
    """Create a task plan."""
    try:
        plan = await create_task_plan(
            person_id=person_id,
            task_description=request.task,
            session_id=session_id,
            auto_approve=request.auto_execute,
        )
    except Exception:
        await _log_stage2_event(
            person_id,
            "task_plan_create_failed",
            {"task": request.task, "auto_execute": request.auto_execute},
        )
        raise

    await _log_stage2_event(
        person_id,
        "task_plan_created",
        {
            "plan_id": plan.id,
            "status": plan.status.value,
            "steps_count": len(plan.steps),
            "auto_execute": request.auto_execute,
        },
    )

    return TaskResponse(
        plan_id=plan.id,
        status=plan.status.value,
        goal=plan.goal,
        steps=[s.model_dump() for s in plan.steps],
        requires_approval=plan.status.value == "pending_approval",
        final_output=plan.final_output,
    )


@router.get("/task/{plan_id}")
async def get_task(plan_id: str):
    """Get a task plan by ID."""
    plan = await get_task_plan(plan_id)
    if not plan:
        raise HTTPException(404, f"Task plan not found: {plan_id}")

    return TaskResponse(
        plan_id=plan.id,
        status=plan.status.value,
        goal=plan.goal,
        steps=[s.model_dump() for s in plan.steps],
        requires_approval=plan.status.value == "pending_approval",
        final_output=plan.final_output,
    )


@router.post("/task/{plan_id}/approve")
async def approve_task(
    plan_id: str,
    person_id: str = Query(...),
):
    """Approve and execute a task plan."""
    plan = await approve_task_plan(plan_id, person_id)
    if not plan:
        raise HTTPException(404, "Task plan not found or already processed")

    await _log_stage2_event(
        person_id,
        "task_plan_approved",
        {
            "plan_id": plan.id,
            "status": plan.status.value,
            "steps_count": len(plan.steps),
        },
    )

    return TaskResponse(
        plan_id=plan.id,
        status=plan.status.value,
        goal=plan.goal,
        steps=[s.model_dump() for s in plan.steps],
        requires_approval=False,
        final_output=plan.final_output,
    )


@router.post("/task/{plan_id}/cancel")
async def cancel_task(
    plan_id: str,
    person_id: str = Query(...),
):
    """Cancel a task plan."""
    success = await cancel_task_plan(plan_id, person_id)
    if success:
        await _log_stage2_event(
            person_id,
            "task_plan_cancelled",
            {"plan_id": plan_id},
        )
    return {"cancelled": success, "plan_id": plan_id}


@router.get("/tasks/active")
async def get_active_tasks(person_id: str = Query(...)):
    """Get active task plans for the user."""
    plans = await get_active_plans(person_id)
    return {
        "tasks": [
            {
                "plan_id": p.id,
                "status": p.status.value,
                "goal": p.goal,
                "steps_count": len(p.steps),
            }
            for p in plans
        ],
        "count": len(plans),
    }


@router.post("/recurring")
async def create_recurring_task(
    request: RecurringScheduleRequest,
    person_id: str = Query(...),
):
    """Create recurring schedule + initial pending approval plan."""
    try:
        schedule, first_plan = await create_recurring_schedule(
            person_id=person_id,
            task_description=request.task,
            goal_hint=request.goal_hint,
            cadence=request.cadence,
            cadence_interval=request.cadence_interval,
            run_timezone=request.run_timezone,
            day_of_month=request.day_of_month,
            run_hour=request.run_hour,
            run_minute=request.run_minute,
            metadata=request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await _log_stage2_event(
        person_id,
        "recurring_schedule_created",
        {
            "schedule_id": schedule.id,
            "plan_id": first_plan.id,
            "status": schedule.status.value,
        },
    )

    return {
        "schedule": _serialize_recurring_schedule(schedule),
        "first_run_plan": _serialize_task_response(first_plan).model_dump(),
        "run_logs": [],
    }


@router.get("/recurring")
async def list_recurring_tasks(
    person_id: str = Query(...),
    include_inactive: bool = Query(False),
):
    schedules = await list_recurring_schedules(
        person_id,
        include_inactive=include_inactive,
        limit=20,
    )
    return {
        "schedules": [_serialize_recurring_schedule(s) for s in schedules],
        "count": len(schedules),
    }


@router.get("/recurring/{schedule_id}")
async def get_recurring_task(
    schedule_id: str,
    person_id: str = Query(...),
):
    schedule = await get_recurring_schedule(schedule_id, person_id=person_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Recurring schedule not found")

    run_logs = await get_recurring_schedule_runs(schedule_id, limit=10)
    latest_plan = None
    if schedule.latest_plan_id:
        latest_plan = await get_task_plan(schedule.latest_plan_id)
    elif schedule.created_plan_id:
        latest_plan = await get_task_plan(schedule.created_plan_id)

    return {
        "schedule": _serialize_recurring_schedule(schedule),
        "latest_plan": _serialize_task_response(latest_plan).model_dump() if latest_plan else None,
        "run_logs": [_serialize_recurring_run(run) for run in run_logs],
    }


@router.post("/recurring/{schedule_id}/approve")
async def approve_recurring_task(
    schedule_id: str,
    person_id: str = Query(...),
):
    try:
        schedule, plan, run_log = await approve_recurring_schedule(schedule_id, person_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    await _log_stage2_event(
        person_id,
        "recurring_schedule_first_run_completed",
        {
            "schedule_id": schedule.id,
            "plan_id": plan.id,
            "run_status": run_log.status.value,
        },
    )

    return {
        "schedule": _serialize_recurring_schedule(schedule),
        "plan": _serialize_task_response(plan).model_dump(),
        "run_log": _serialize_recurring_run(run_log),
    }


@router.post("/recurring/{schedule_id}/cancel")
async def cancel_recurring_task(
    schedule_id: str,
    person_id: str = Query(...),
):
    cancelled = await cancel_recurring_schedule(schedule_id, person_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Recurring schedule not found")
    return {"cancelled": True, "schedule_id": schedule_id}


@router.post("/recurring/{schedule_id}/run")
async def run_recurring_task(
    schedule_id: str,
    person_id: str = Query(...),
):
    try:
        schedule, plan, run_log = await run_recurring_schedule_now(schedule_id, person_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 409
        raise HTTPException(status_code=status_code, detail=message) from exc

    return {
        "schedule": _serialize_recurring_schedule(schedule),
        "plan": _serialize_task_response(plan).model_dump() if plan else None,
        "run_log": _serialize_recurring_run(run_log),
    }


# =============================================================================
# Research Endpoints
# =============================================================================

@router.post("/research")
async def start_research_session(
    request: ResearchRequest,
    person_id: str = Query(...),
):
    """Start a new research session."""
    session = await start_research(
        person_id=person_id,
        topic=request.topic,
        question=request.question,
        auto_search=request.auto_search,
    )

    return {
        "session_id": session.id,
        "topic": session.topic,
        "sources_count": len(session.sources),
        "sources": [s.model_dump() for s in session.sources],
    }


@router.get("/research/{session_id}")
async def get_research(session_id: str):
    """Get a research session by ID."""
    session = await get_research_session(session_id)
    if not session:
        raise HTTPException(404, f"Research session not found: {session_id}")

    return {
        "session_id": session.id,
        "topic": session.topic,
        "question": session.question,
        "status": session.status,
        "sources": [s.model_dump() for s in session.sources],
        "findings": session.findings,
        "synthesis": session.synthesis,
    }


@router.post("/research/{session_id}/expand")
async def expand_research_session(
    session_id: str,
    query: str = Query(..., description="Follow-up query"),
):
    """Expand research with a follow-up query."""
    session = await expand_research(session_id, query)

    return {
        "session_id": session.id,
        "new_sources_count": len(session.sources),
        "sources": [s.model_dump() for s in session.sources],
    }


@router.post("/research/{session_id}/synthesize")
async def synthesize_research_session(session_id: str):
    """Synthesize research into a comprehensive answer."""
    synthesis = await synthesize_research(session_id)

    return {
        "session_id": session_id,
        "synthesis": synthesis,
    }


@router.get("/research/active")
async def get_active_research_sessions(person_id: str = Query(...)):
    """Get active research sessions for the user."""
    sessions = await get_active_research(person_id)
    return {
        "sessions": [
            {
                "session_id": s.id,
                "topic": s.topic,
                "sources_count": len(s.sources),
                "status": s.status,
            }
            for s in sessions
        ],
        "count": len(sessions),
    }


__all__ = ["router"]
