"""Minimal migration script to bootstrap required extensions."""

from __future__ import annotations

import asyncio

import asyncpg

from sakhi.libs.schemas import get_settings

MIGRATION_STATEMENTS = (
    'CREATE EXTENSION IF NOT EXISTS "pgcrypto";',
    "CREATE EXTENSION IF NOT EXISTS vector;",
    """
    CREATE TABLE IF NOT EXISTS documents (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        content text,
        embedding vector(1536),
        updated_at timestamptz DEFAULT now()
    );
    """,
)


async def migrate() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(
        settings.postgres_dsn,
        statement_cache_size=0,
        max_inactive_connection_lifetime=300,
        max_cached_statement_lifetime=0,
    )
    try:
        for statement in MIGRATION_STATEMENTS:
            await conn.execute(statement)
    finally:
        await conn.close()


def main() -> None:  # pragma: no cover - CLI entrypoint
    asyncio.run(migrate())


if __name__ == "__main__":  # pragma: no cover
    main()
