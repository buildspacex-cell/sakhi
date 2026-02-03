"""
Tool Executor Service
---------------------
Manage and execute tools for Sakhi.
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """Definition of an available tool."""
    id: str
    tool_name: str
    display_name: str
    description: str
    category: str
    capabilities: List[str] = []
    parameters_schema: Dict[str, Any] = {}
    requires_approval: bool = True
    risk_level: str = "low"


class ToolResult(BaseModel):
    """Result of a tool execution."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    summary: Optional[str] = None


async def get_available_tools(
    person_id: Optional[str] = None,
) -> List[ToolDefinition]:
    """Get all available tools, optionally with user permissions."""
    if person_id:
        rows = await dbfetch(
            """
            SELECT t.*, p.permission, p.auto_approve
            FROM sakhi_tools t
            LEFT JOIN user_tool_permissions p ON p.tool_id = t.id AND p.person_id = $1
            WHERE t.enabled = true
            ORDER BY t.category, t.display_name
            """,
            person_id,
        )
    else:
        rows = await dbfetch(
            """
            SELECT * FROM sakhi_tools WHERE enabled = true
            ORDER BY category, display_name
            """
        )

    return [
        ToolDefinition(
            id=str(row["id"]),
            tool_name=row["tool_name"],
            display_name=row["display_name"],
            description=row["description"],
            category=row["category"],
            capabilities=row.get("capabilities") or [],
            parameters_schema=row.get("parameters_schema") or {},
            requires_approval=row.get("requires_approval", True),
            risk_level=row.get("risk_level", "low"),
        )
        for row in (rows or [])
    ]


async def get_tool_by_name(tool_name: str) -> Optional[ToolDefinition]:
    """Get a specific tool by name."""
    row = await dbfetch(
        "SELECT * FROM sakhi_tools WHERE tool_name = $1 AND enabled = true",
        tool_name,
        one=True,
    )

    if not row:
        return None

    return ToolDefinition(
        id=str(row["id"]),
        tool_name=row["tool_name"],
        display_name=row["display_name"],
        description=row["description"],
        category=row["category"],
        capabilities=row.get("capabilities") or [],
        parameters_schema=row.get("parameters_schema") or {},
        requires_approval=row.get("requires_approval", True),
        risk_level=row.get("risk_level", "low"),
    )


async def can_auto_execute(person_id: str, tool_name: str) -> bool:
    """Check if tool can be executed without user approval."""
    row = await dbfetch(
        """
        SELECT
            CASE
                WHEN t.requires_approval = false THEN true
                WHEN p.auto_approve = true THEN true
                WHEN p.permission = 'allow' THEN true
                ELSE false
            END as can_execute
        FROM sakhi_tools t
        LEFT JOIN user_tool_permissions p ON p.tool_id = t.id AND p.person_id = $2
        WHERE t.tool_name = $1 AND t.enabled = true
        """,
        tool_name,
        person_id,
        one=True,
    )
    return bool(row and row.get("can_execute"))


async def execute_tool(
    person_id: str,
    tool_name: str,
    parameters: Dict[str, Any],
    task_plan_id: Optional[str] = None,
    skip_approval_check: bool = False,
) -> ToolResult:
    """
    Execute a tool.

    Args:
        person_id: User ID
        tool_name: Name of tool to execute
        parameters: Tool parameters
        task_plan_id: Optional task plan this belongs to
        skip_approval_check: Skip approval check (for pre-approved tasks)

    Returns:
        ToolResult with success/failure and result data
    """
    import time

    tool = await get_tool_by_name(tool_name)
    if not tool:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            error=f"Tool not found: {tool_name}",
        )

    # Check approval
    if not skip_approval_check:
        can_execute = await can_auto_execute(person_id, tool_name)
        if not can_execute:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="Tool requires user approval",
            )

    # Record execution start
    execution_id = await _start_execution(
        person_id=person_id,
        tool_name=tool_name,
        tool_id=tool.id,
        parameters=parameters,
        task_plan_id=task_plan_id,
    )

    start_time = time.time()

    try:
        # Route to appropriate handler
        result = await _execute_tool_handler(tool_name, parameters)
        duration_ms = int((time.time() - start_time) * 1000)

        # Record success
        await _complete_execution(
            execution_id=execution_id,
            success=True,
            result=result,
            duration_ms=duration_ms,
        )

        # Update user tool stats
        await _update_tool_usage(person_id, tool.id)

        return ToolResult(
            tool_name=tool_name,
            success=True,
            result=result.get("data"),
            summary=result.get("summary"),
            execution_time_ms=duration_ms,
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        LOGGER.error("[tools] Execution failed: %s - %s", tool_name, e)

        await _complete_execution(
            execution_id=execution_id,
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )

        return ToolResult(
            tool_name=tool_name,
            success=False,
            error=str(e),
            execution_time_ms=duration_ms,
        )


async def _execute_tool_handler(
    tool_name: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Route to the appropriate tool handler."""
    from sakhi.apps.api.services.agentic.search import (
        web_search,
        news_search,
        fetch_url,
        summarize_search_results,
    )

    if tool_name == "web_search":
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 5)
        response = await web_search(query, max_results)
        summary = await summarize_search_results(response.results, query)
        return {
            "data": {
                "query": response.query,
                "results": [r.model_dump() for r in response.results],
                "total": response.total_results,
            },
            "summary": summary,
        }

    elif tool_name == "news_search":
        query = parameters.get("query", "")
        response = await news_search(query)
        summary = await summarize_search_results(response.results, query)
        return {
            "data": {
                "query": response.query,
                "results": [r.model_dump() for r in response.results],
                "total": response.total_results,
            },
            "summary": summary,
        }

    elif tool_name == "fetch_url":
        url = parameters.get("url", "")
        result = await fetch_url(url)
        return {
            "data": result,
            "summary": result.get("title", url)[:100] if result.get("success") else result.get("error"),
        }

    elif tool_name == "summarize":
        text = parameters.get("text", "")
        max_length = parameters.get("max_length", 200)
        summary = await _summarize_text(text, max_length)
        return {
            "data": {"summary": summary, "original_length": len(text)},
            "summary": summary,
        }

    elif tool_name == "weather":
        location = parameters.get("location", "")
        weather = await _get_weather(location)
        return {
            "data": weather,
            "summary": weather.get("summary", f"Weather for {location}"),
        }

    elif tool_name == "calculate":
        expression = parameters.get("expression", "")
        result = await _calculate(expression)
        return {
            "data": {"expression": expression, "result": result},
            "summary": f"{expression} = {result}",
        }

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


async def _summarize_text(text: str, max_length: int = 200) -> str:
    """Summarize text using LLM."""
    from sakhi.apps.api.core.llm import get_router

    if len(text) <= max_length:
        return text

    try:
        router = get_router()
        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize this text in {max_length} characters or less:\n\n{text[:5000]}",
                }
            ],
            model="claude-sonnet-4-20250514",
            max_tokens=200,
        )
        return response.content[0].text if response.content else text[:max_length]
    except Exception as e:
        LOGGER.error("[tools] Summarization failed: %s", e)
        return text[:max_length]


async def _get_weather(location: str) -> Dict[str, Any]:
    """Get weather for a location."""
    # In production, use a real weather API
    # For now, return placeholder
    return {
        "location": location,
        "temperature": "Unable to fetch",
        "conditions": "Weather API not configured",
        "summary": f"Weather data for {location} requires API configuration",
    }


async def _calculate(expression: str) -> Any:
    """Safely evaluate a mathematical expression."""
    import ast
    import operator

    # Allowed operators
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def eval_expr(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = eval_expr(node.left)
            right = eval_expr(node.right)
            return operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = eval_expr(node.operand)
            return operators[type(node.op)](operand)
        else:
            raise ValueError(f"Unsupported operation: {type(node)}")

    try:
        tree = ast.parse(expression, mode='eval')
        return eval_expr(tree.body)
    except Exception as e:
        return f"Error: {e}"


async def _start_execution(
    person_id: str,
    tool_name: str,
    tool_id: str,
    parameters: Dict[str, Any],
    task_plan_id: Optional[str] = None,
) -> str:
    """Record start of tool execution."""
    row = await dbfetch(
        """
        INSERT INTO tool_executions (
            person_id, tool_id, tool_name, parameters, task_plan_id,
            status, started_at
        )
        VALUES ($1, $2, $3, $4::jsonb, $5, 'executing', NOW())
        RETURNING id
        """,
        person_id,
        tool_id,
        tool_name,
        json.dumps(parameters),
        task_plan_id,
        one=True,
    )
    return str(row["id"]) if row else ""


async def _complete_execution(
    execution_id: str,
    success: bool,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    duration_ms: int = 0,
) -> None:
    """Record completion of tool execution."""
    status = "completed" if success else "failed"
    await dbexec(
        """
        UPDATE tool_executions
        SET status = $2,
            completed_at = NOW(),
            duration_ms = $3,
            result = $4::jsonb,
            result_summary = $5,
            error = $6
        WHERE id = $1
        """,
        execution_id,
        status,
        duration_ms,
        json.dumps(result) if result else None,
        result.get("summary") if result else None,
        error,
    )


async def _update_tool_usage(person_id: str, tool_id: str) -> None:
    """Update user's tool usage statistics."""
    await dbexec(
        """
        INSERT INTO user_tool_permissions (person_id, tool_id, times_used, last_used_at)
        VALUES ($1, $2, 1, NOW())
        ON CONFLICT (person_id, tool_id) DO UPDATE
        SET times_used = user_tool_permissions.times_used + 1,
            last_used_at = NOW()
        """,
        person_id,
        tool_id,
    )


__all__ = [
    "ToolDefinition",
    "ToolResult",
    "get_available_tools",
    "get_tool_by_name",
    "can_auto_execute",
    "execute_tool",
]
