"""Seed local Supabase/Postgres instance with starter data."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import asyncpg

from sakhi.libs.schemas import get_settings

EMBEDDING_DIM = 1536
SEED_ROWS: list[dict[str, Any]] = [
    {
        "content": "Sakhi is an empathetic AI companion that remembers prior conversations.",
        "embedding": [0.0] * EMBEDDING_DIM,
    }
]


async def seed() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(
        settings.postgres_dsn,
        statement_cache_size=0,
        max_inactive_connection_lifetime=300,
        max_cached_statement_lifetime=0,
    )
    try:
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                content text,
                embedding vector(1536),
                updated_at timestamptz DEFAULT now()
            );
            """
        )
        for row in SEED_ROWS:
            await conn.execute(
                """
                INSERT INTO documents (content, embedding, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO NOTHING
                """,
                row["content"],
                row["embedding"],
                datetime.utcnow(),
            )
    finally:
        await conn.close()


def main() -> None:  # pragma: no cover - CLI entrypoint
    asyncio.run(seed())


if __name__ == "__main__":  # pragma: no cover
    main()
