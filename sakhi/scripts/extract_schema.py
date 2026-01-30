#!/usr/bin/env python3
"""
Extract database schema from Supabase and generate documentation.
Usage: python sakhi/scripts/extract_schema.py > docs/architecture/database-schema.md
"""
import asyncio
import os
import sys
from typing import Any

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

SCHEMA_QUERY = """
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default,
    c.character_maximum_length,
    c.udt_name
FROM information_schema.columns c
JOIN information_schema.tables t ON c.table_name = t.table_name
WHERE t.table_schema = 'public'
  AND t.table_type = 'BASE TABLE'
ORDER BY c.table_name, c.ordinal_position;
"""

# Tables organized by category for documentation
TABLE_CATEGORIES = {
    "Core": [
        "users", "profiles", "persons", "auth_users", "personal_model",
    ],
    "Conversation": [
        "conversation_turns", "conversation_sessions", "conversation_state",
        "session_summaries", "session_continuity", "continuity_state",
    ],
    "Memory": [
        "journal_entries", "journal_embeddings", "journal_inference",
        "memory_short_term", "memory_episodic", "memory_context_cache",
        "memory_weekly_signals", "memory_nodes", "memory_edges",
    ],
    "Patterns": [
        "pattern_occurrences", "crystallized_patterns", "crystallization_log",
    ],
    "Planning": [
        "goals", "goal_history", "goal_suggestions", "intent_extractions",
        "intents", "tasks", "planned_items", "planner_weekly_pressure",
    ],
    "Rhythm": [
        "rhythm_weekly_rollups", "rhythm_daily_curve", "rhythm_forecasts",
    ],
    "Body & Health": [
        "health_data_sync", "body_state_history", "self_report_body",
    ],
    "Reflection": [
        "reflections", "reflection_inquiry_turns", "reflection_inquiry_embeddings",
        "reflection_trace",
    ],
    "Cache Tables": [
        "daily_reflection_cache", "morning_preview_cache", "morning_momentum_cache",
        "micro_journey_cache", "micro_momentum_cache", "micro_recovery_cache",
        "mini_flow_cache", "focus_path_cache", "forecast_cache",
        "analytics_cache", "coherence_cache", "identity_drift_cache",
    ],
    "Ayurvedic": [
        "ay_nodes", "ay_edges", "elemental_signal_stm",
    ],
}


async def get_schema() -> dict[str, list[dict[str, Any]]]:
    """Fetch schema from database."""
    conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
    try:
        rows = await conn.fetch(SCHEMA_QUERY)
        tables: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            table = row["table_name"]
            if table not in tables:
                tables[table] = []
            tables[table].append({
                "column": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
                "default": row["column_default"],
                "udt": row["udt_name"],
            })
        return tables
    finally:
        await conn.close()


def format_type(col: dict[str, Any]) -> str:
    """Format column type for display."""
    t = col["type"]
    if t == "USER-DEFINED":
        return col["udt"]  # vector, etc.
    if t == "ARRAY":
        return f"{col['udt']}[]"
    return t


def generate_markdown(tables: dict[str, list[dict[str, Any]]]) -> str:
    """Generate markdown documentation."""
    lines = [
        "# Database Schema",
        "",
        "> Auto-generated schema documentation for Sakhi database.",
        "> ",
        f"> **Tables:** {len(tables)}",
        "",
        "---",
        "",
        "## Table of Contents",
        "",
    ]

    # TOC by category
    categorized = set()
    for category, table_list in TABLE_CATEGORIES.items():
        existing = [t for t in table_list if t in tables]
        if existing:
            lines.append(f"### {category}")
            for t in existing:
                lines.append(f"- [{t}](#{t})")
                categorized.add(t)
            lines.append("")

    # Uncategorized tables
    uncategorized = [t for t in sorted(tables.keys()) if t not in categorized]
    if uncategorized:
        lines.append("### Other")
        for t in uncategorized:
            lines.append(f"- [{t}](#{t})")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Generate table schemas by category
    for category, table_list in TABLE_CATEGORIES.items():
        existing = [t for t in table_list if t in tables]
        if existing:
            lines.append(f"## {category}")
            lines.append("")
            for table_name in existing:
                lines.extend(format_table(table_name, tables[table_name]))

    # Uncategorized
    if uncategorized:
        lines.append("## Other Tables")
        lines.append("")
        for table_name in uncategorized:
            lines.extend(format_table(table_name, tables[table_name]))

    return "\n".join(lines)


def format_table(name: str, columns: list[dict[str, Any]]) -> list[str]:
    """Format a single table schema."""
    lines = [
        f"### {name}",
        "",
        "| Column | Type | Nullable | Default |",
        "|--------|------|----------|---------|",
    ]

    for col in columns:
        col_type = format_type(col)
        nullable = "✓" if col["nullable"] else ""
        default = col["default"] or ""
        # Truncate long defaults
        if len(default) > 40:
            default = default[:37] + "..."
        lines.append(f"| `{col['column']}` | {col_type} | {nullable} | {default} |")

    lines.append("")
    return lines


async def main():
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    print("Fetching schema from database...", file=sys.stderr)
    tables = await get_schema()
    print(f"Found {len(tables)} tables", file=sys.stderr)

    md = generate_markdown(tables)
    print(md)


if __name__ == "__main__":
    asyncio.run(main())
