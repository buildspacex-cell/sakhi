from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Sequence
import json

import asyncpg

POOL: asyncpg.Pool | None = None
_POOL_LOOP_ID: int | None = None  # id() of the event loop that created POOL


async def reset_pool() -> None:
    """Close and discard the current pool.

    Must be called when the event loop changes (e.g. between successive
    ``asyncio.run()`` calls in the RQ worker).  The next ``get_pool()``
    call will create a fresh pool on the current loop.
    """
    global POOL, _POOL_LOOP_ID
    if POOL is not None:
        try:
            await POOL.close()
        except Exception:
            pass
        POOL = None
        _POOL_LOOP_ID = None


def _normalize_arg(val: Any) -> Any:
    if isinstance(val, uuid.UUID):
        return str(val)
    return val


async def get_pool() -> asyncpg.Pool:
    global POOL, _POOL_LOOP_ID

    # Detect stale pool: if the event loop changed (e.g. new asyncio.run()
    # in an RQ worker), the old pool's connections are unusable.
    current_loop_id = id(asyncio.get_running_loop())
    if POOL is not None and _POOL_LOOP_ID != current_loop_id:
        try:
            await POOL.close()
        except Exception:
            pass
        POOL = None
        _POOL_LOOP_ID = None

    if POOL is None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise RuntimeError("Missing required env var: DATABASE_URL")

        async def _register_codecs(connection: asyncpg.Connection) -> None:
            # Register pgvector codec only if the type exists in this DB.
            try:
                has_vector = await connection.fetchval(
                    "SELECT 1 FROM pg_type WHERE typname = 'vector' LIMIT 1"
                )
            except Exception:
                has_vector = False
            if not has_vector:
                return

            async def _encode_vector(value: Any) -> str:
                if value is None:
                    return "[]"
                try:
                    return "[" + ",".join(str(float(x)) for x in value) + "]"
                except Exception:
                    return "[]"

            async def _decode_vector(value: str) -> list[float]:
                if not value:
                    return []
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [float(x) for x in parsed]
                except Exception:
                    pass
                text = value.strip()
                if text.startswith("[") and text.endswith("]"):
                    text = text[1:-1]
                parts = [p.strip() for p in text.split(",") if p.strip()]
                try:
                    return [float(p) for p in parts]
                except Exception:
                    return []

            try:
                await connection.set_type_codec(
                    "vector",
                    schema="pg_catalog",
                    encoder=_encode_vector,
                    decoder=_decode_vector,
                    format="text",
                )
            except Exception:
                # If the type exists but is not accessible, continue without the codec.
                pass

        POOL = await asyncpg.create_pool(
            dsn,
            statement_cache_size=0,
            init=_register_codecs,
        )
        _POOL_LOOP_ID = current_loop_id
    return POOL


async def q(sql: str, *args: Any, one: bool = False) -> Any:
    pool = await get_pool()
    normalized_args = tuple(_normalize_arg(arg) for arg in args)
    async with pool.acquire() as connection:
        rows: Sequence[asyncpg.Record] = await connection.fetch(sql, *normalized_args)
    if one:
        record = rows[0] if rows else None
        return dict(record) if isinstance(record, asyncpg.Record) else record
    return [dict(record) if isinstance(record, asyncpg.Record) else record for record in rows]


async def exec(sql: str, *args: Any) -> str:
    pool = await get_pool()
    normalized_args = tuple(_normalize_arg(arg) for arg in args)
    async with pool.acquire() as connection:
        return await connection.execute(sql, *normalized_args)


async def dbfetchrow(sql: str, *args: Any) -> Any:
    """Fetch a single row and return it as a dict, or None if no row exists."""
    return await q(sql, *args, one=True)


async def dbfetchall(sql: str, *args: Any) -> list[dict[str, Any]]:
    """Fetch all rows and return them as a list of dicts."""
    return await q(sql, *args, one=False)


class DBSession:
    def __init__(self, pool: asyncpg.Pool, connection: asyncpg.Connection) -> None:
        self._pool = pool
        self._connection = connection

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        normalized_args = tuple(_normalize_arg(arg) for arg in args)
        rows = await self._connection.fetch(sql, *normalized_args)
        return [dict(row) for row in rows]

    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any] | None:
        normalized_args = tuple(_normalize_arg(arg) for arg in args)
        row = await self._connection.fetchrow(sql, *normalized_args)
        return dict(row) if row else None

    async def execute(self, sql: str, *args: Any) -> str:
        normalized_args = tuple(_normalize_arg(arg) for arg in args)
        return await self._connection.execute(sql, *normalized_args)

    async def close(self) -> None:
        await self._pool.release(self._connection)


async def get_db() -> DBSession:
    """Acquire a DB connection for direct fetch/execute usage."""
    pool = await get_pool()
    connection = await pool.acquire()
    return DBSession(pool, connection)
