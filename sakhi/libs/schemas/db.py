"""Async database helpers backed by asyncpg connection pooling."""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg

from sakhi.libs.security.journal_crypto import hydrate_journal_row
from .settings import get_settings

_POOL: asyncpg.Pool | None = None
_POOL_LOCK = asyncio.Lock()


async def get_async_pool() -> asyncpg.Pool:
    """Return a shared asyncpg connection pool, creating it on demand."""

    global _POOL
    if _POOL is None:
        async with _POOL_LOCK:
            if _POOL is None:
                settings = get_settings()
                _POOL = await asyncpg.create_pool(
                    dsn=settings.database_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    statement_cache_size=0,
                    max_inactive_connection_lifetime=300,
                    max_cached_statement_lifetime=0,
                )
    return _POOL


def _normalize_record(record: asyncpg.Record | dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    if isinstance(record, asyncpg.Record):
        return hydrate_journal_row(dict(record))
    return hydrate_journal_row(record)


async def fetch_one(query: str, *args: Any) -> dict[str, Any] | None:
    """Run a parametrised query and return at most a single row."""

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(query, *args)
    return _normalize_record(row)


async def fetch_all(query: str, *args: Any) -> list[dict[str, Any]]:
    """Run a parametrised query and return all resulting rows."""

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        records = await connection.fetch(query, *args)
    return [hydrate_journal_row(dict(record)) for record in records]


async def execute(query: str, *args: Any) -> str:
    """Execute a data-modifying statement and return the asyncpg status."""

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        return await connection.execute(query, *args)


__all__ = ["execute", "fetch_all", "fetch_one", "get_async_pool"]
