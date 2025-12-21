"""Minimal tool execution helpers for LLM router tooling."""

from __future__ import annotations

from typing import Any, Dict

from jsonschema import validate

from sakhi.libs.schemas.tools import CREATE_PLAN_TOOL


def _create_plan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input and return a simple structured plan."""

    validate(instance=args, schema=CREATE_PLAN_TOOL["parameters"])
    block = int(args.get("work_block") or 45)
    return {
        "objective": args["objective"],
        "horizon": args.get("horizon", "week"),
        "tasks": [
            {"name": "Clarify outcome", "minutes": block},
            {"name": "Research inputs", "minutes": block},
            {"name": "Outline", "minutes": block},
            {"name": "Draft", "minutes": block},
            {"name": "Polish", "minutes": block},
        ],
    }


def run_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch to a small set of locally implemented tools."""

    if tool_name == "create_plan":
        return _create_plan(arguments)
    return {"error": f"Unknown tool {tool_name}"}


__all__ = ["run_tool"]
