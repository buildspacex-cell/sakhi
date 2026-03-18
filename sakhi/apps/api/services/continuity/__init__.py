from __future__ import annotations

from typing import Any

__all__ = [
    "CONTINUITY_SCOPE",
    "ClassificationState",
    "canonicalize_anchor",
    "classify_continuity_text",
    "compile_journal_continuity",
    "create_deep_reflection_job",
    "enable_continuity_policy",
    "exclude_continuity_ref",
    "get_continuity_arc",
    "get_continuity_policy",
    "get_continuity_topics",
    "get_deep_reflection_result",
    "get_deep_reflection_status",
    "load_continuity_items",
    "load_journal_entries_for_continuity",
    "parse_continuity_window",
    "upsert_continuity_label",
    "upsert_continuity_policy",
]


def __getattr__(name: str) -> Any:
    if name in {
        "canonicalize_anchor",
        "get_continuity_policy",
        "load_continuity_items",
        "load_journal_entries_for_continuity",
        "upsert_continuity_label",
        "upsert_continuity_policy",
    }:
        from sakhi.apps.api.services.continuity import adapters

        return getattr(adapters, name)

    if name in {
        "ClassificationState",
        "classify_continuity_text",
        "compile_journal_continuity",
        "parse_continuity_window",
    }:
        from sakhi.apps.api.services.continuity import compiler

        return getattr(compiler, name)

    if name in {
        "CONTINUITY_SCOPE",
        "enable_continuity_policy",
        "exclude_continuity_ref",
        "get_continuity_arc",
        "get_continuity_topics",
    }:
        from sakhi.apps.api.services.continuity import service

        return getattr(service, name)

    if name in {
        "create_deep_reflection_job",
        "get_deep_reflection_result",
        "get_deep_reflection_status",
    }:
        from sakhi.apps.api.services.continuity import reflection

        return getattr(reflection, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
