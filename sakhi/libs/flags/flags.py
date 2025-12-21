from __future__ import annotations

from sakhi.libs.schemas.db import get_async_pool


async def is_enabled(key: str) -> bool:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            "SELECT enabled FROM feature_flags WHERE key = $1",
            key,
        )
    return bool(row and row.get("enabled"))


async def set_flag(key: str, value: bool) -> None:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO feature_flags(key, enabled)
            VALUES ($1, $2)
            ON CONFLICT(key) DO UPDATE SET enabled = EXCLUDED.enabled
            """,
            key,
            value,
        )
