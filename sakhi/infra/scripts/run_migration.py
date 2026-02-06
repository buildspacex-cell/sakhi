"""Run a SQL migration file against the database."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

from sakhi.libs.schemas import get_settings


async def run_migration(sql_file: Path) -> None:
    """Execute a SQL file against the database."""
    if not sql_file.exists():
        print(f"Error: File not found: {sql_file}")
        sys.exit(1)

    sql_content = sql_file.read_text()

    settings = get_settings()
    print(f"Connecting to database...")

    conn = await asyncpg.connect(
        settings.postgres_dsn,
        statement_cache_size=0,
    )

    try:
        print(f"Running migration: {sql_file.name}")
        # Execute the entire SQL file
        await conn.execute(sql_content)
        print(f"Migration completed successfully!")

        # Verify tables were created
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'ay_%'
            ORDER BY table_name
        """)

        if tables:
            print(f"\nAyurvedic tables created/verified:")
            for t in tables:
                print(f"  - {t['table_name']}")

        # Check ay_sources data
        sources = await conn.fetch("SELECT code, title FROM ay_sources ORDER BY code")
        if sources:
            print(f"\nSource texts registered:")
            for s in sources:
                print(f"  - {s['code']}: {s['title']}")

    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SQL migration")
    parser.add_argument("file", type=Path, help="SQL file to execute")
    args = parser.parse_args()

    asyncio.run(run_migration(args.file))


if __name__ == "__main__":
    main()
