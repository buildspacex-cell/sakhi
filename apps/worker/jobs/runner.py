from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import List

import asyncpg

from apps.worker.enrich.short_horizon_aggregator import update_short_horizon
from apps.worker.jobs.consolidate import consolidate_person

LOGGER = logging.getLogger("worker.consolidator")
logging.basicConfig(level=logging.INFO)


async def _pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(os.environ["DATABASE_URL"])


async def _person_ids(pool: asyncpg.Pool) -> List[str]:
    async with pool.acquire() as connection:
        rows = await connection.fetch("select distinct user_id from journal_entries")
    return [row["user_id"] for row in rows]


async def run_once(pool: asyncpg.Pool | None = None) -> None:
    close_pool = False
    if pool is None:
        pool = await _pool()
        close_pool = True

    try:
        persons = await _person_ids(pool)
        LOGGER.info("consolidator_run_start", extra={"count": len(persons)})
        for pid in persons:
            async with pool.acquire() as connection:
                await consolidate_person(connection, pid)
                await update_short_horizon(connection, pid)
        LOGGER.info("consolidator_run_complete", extra={"count": len(persons)})
    finally:
        if close_pool:
            await pool.close()


async def main() -> None:
    pool = await _pool()
    interval_minutes = float(os.getenv("CONSOLIDATOR_INTERVAL_MINUTES", "1440"))
    if interval_minutes <= 0:
        await run_once(pool)
        return

    interval_seconds = interval_minutes * 60
    while True:
        start = time.perf_counter()
        try:
            await run_once(pool)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("consolidator_run_failed", exc_info=exc)
        elapsed = time.perf_counter() - start
        sleep_for = max(0, interval_seconds - elapsed)
        await asyncio.sleep(sleep_for or 0)


if __name__ == "__main__":
    asyncio.run(main())
