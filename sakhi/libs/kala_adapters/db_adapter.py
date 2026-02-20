"""Sakhi DatabaseAdapter — bridges kala to sakhi.apps.api.core.db."""

from __future__ import annotations

from typing import Any

from kala.adapters.base import DatabaseAdapter


class SakhiDatabaseAdapter(DatabaseAdapter):
    """Concrete database adapter using Sakhi's asyncpg pool."""

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        from sakhi.apps.api.core.db import q

        rows = await q(sql, *args)
        return rows or []

    async def fetch_one(self, sql: str, *args: Any) -> dict[str, Any] | None:
        from sakhi.apps.api.core.db import q

        return await q(sql, *args, one=True)

    async def execute(self, sql: str, *args: Any) -> str:
        from sakhi.apps.api.core.db import exec as dbexec

        return await dbexec(sql, *args)
