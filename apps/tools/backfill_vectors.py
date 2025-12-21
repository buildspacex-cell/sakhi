from __future__ import annotations

import asyncio
import os

import asyncpg

from sakhi.libs.embeddings import embed_text

DATABASE_URL = os.environ["DATABASE_URL"]


async def run() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL)
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT id, COALESCE(cleaned, text) AS t
                FROM episodes
                WHERE embed_vec IS NULL
                ORDER BY ts DESC
                LIMIT 5000
                """
            )
            for row in rows:
                text = row["t"] or ""
                vector = await embed_text(text)
                await connection.execute(
                    "UPDATE episodes SET embed_vec = $1 WHERE id = $2",
                    vector,
                    row["id"],
                )
    finally:
        await pool.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
