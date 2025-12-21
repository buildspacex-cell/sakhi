"""Apply SQL migrations sequentially using the shared asyncpg pool."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from sakhi.libs.schemas import get_async_pool

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_COMMENT_RE = re.compile(r"--.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)


def _split_sql(sql: str) -> list[str]:
    """Return individual statements stripped of comments and whitespace."""

    cleaned = _COMMENT_RE.sub("", sql)
    statements: list[str] = []
    for chunk in cleaned.split(";"):
        statement = chunk.strip()
        if statement:
            statements.append(statement)
    return statements


def _sorted_migration_paths() -> list[Path]:
    """Return migration files ordered lexicographically by filename."""

    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(p for p in MIGRATIONS_DIR.iterdir() if p.suffix == ".sql")


async def apply_migrations() -> None:
    """Acquire a pooled connection and execute all SQL migrations in order."""

    migration_files = _sorted_migration_paths()
    if not migration_files:
        return

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        for path in migration_files:
            statements = _split_sql(path.read_text(encoding="utf-8"))
            if not statements:
                continue
            async with connection.transaction():
                for statement in statements:
                    await connection.execute(statement)


def main() -> None:  # pragma: no cover - CLI entrypoint
    asyncio.run(apply_migrations())


if __name__ == "__main__":  # pragma: no cover
    main()

