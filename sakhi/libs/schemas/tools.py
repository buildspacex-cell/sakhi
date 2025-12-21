"""Structured tool schemas shared between router and API."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

CREATE_PLAN_TOOL = {
    "name": "create_plan",
    "description": "Generate a short actionable plan for the stated objective.",
    "parameters": {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "The goal or outcome the user wants to achieve.",
                "minLength": 1,
            },
            "horizon": {
                "type": "string",
                "description": "Optional time horizon such as 'Nov 10' or 'this week'.",
            },
            "work_block": {
                "type": "integer",
                "description": "Preferred focus block length in minutes.",
                "minimum": 15,
                "maximum": 240,
            },
        },
        "required": ["objective"],
        "additionalProperties": False,
    },
}

_TOOL_REGISTRY = {
    CREATE_PLAN_TOOL["name"]: CREATE_PLAN_TOOL,
}

_DEFAULT_TOOL_NAMES = ["create_plan"]


def get_tool_definition(name: str) -> dict:
    """Return a copy of the tool definition for the given name."""

    try:
        return dict(_TOOL_REGISTRY[name])
    except KeyError as exc:
        raise ValueError(f"Unknown tool '{name}'") from exc


def default_tools() -> list[dict]:
    """Return the default tool definitions exposed to LLM providers."""

    return [get_tool_definition(name) for name in _DEFAULT_TOOL_NAMES]


def resolve_tool_definitions(tools: Sequence[Mapping[str, object] | str] | None) -> list[dict]:
    """Coerce client-supplied tool references into full tool definitions."""

    if not tools:
        return default_tools()

    resolved: list[dict] = []
    for item in tools:
        if isinstance(item, str):
            resolved.append(get_tool_definition(item))
            continue

        if not isinstance(item, Mapping):
            raise TypeError("Tool definitions must be mappings or string identifiers")

        name = item.get("name")
        if isinstance(name, str) and name in _TOOL_REGISTRY:
            resolved.append(get_tool_definition(name))
            continue

        resolved.append(dict(item))

    return resolved


def list_tool_names() -> list[str]:
    """Return the canonical list of tool identifiers."""

    return list(_TOOL_REGISTRY.keys())


__all__ = [
    "CREATE_PLAN_TOOL",
    "default_tools",
    "get_tool_definition",
    "list_tool_names",
    "resolve_tool_definitions",
]
