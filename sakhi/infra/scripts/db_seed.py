"""Seed script for inserting starter knowledge."""

from __future__ import annotations

import asyncio
from datetime import datetime

import asyncpg

from sakhi.libs.schemas import get_settings

EMBEDDING_DIM = 1536
SEED_DOCUMENTS = [
    {
        "content": "Sakhi is an AI companion focused on empathetic conversations.",
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
        for doc in SEED_DOCUMENTS:
            await conn.execute(
                """
                INSERT INTO documents (content, embedding, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO NOTHING
                """,
                doc["content"],
                doc["embedding"],
                datetime.utcnow(),
            )
    finally:
        await conn.close()


def main() -> None:  # pragma: no cover - CLI entrypoint
    asyncio.run(seed())


if __name__ == "__main__":  # pragma: no cover
    main()
