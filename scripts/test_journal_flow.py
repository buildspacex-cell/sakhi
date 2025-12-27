import asyncio
import asyncpg
import json
import os
from datetime import datetime, timedelta

DB_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:6543/sakhi")

PERSON_ID = os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90")
LOOKBACK_MIN = 5  # check last 5 minutes


async def main() -> None:
    conn = await asyncpg.connect(DB_URL)
    since = datetime.utcnow() - timedelta(minutes=LOOKBACK_MIN)

    tables = [
        ("journal_entries", "created_at"),
        ("journal_embeddings", "created_at"),
        ("journal_links", "created_at"),
        ("reflections", "created_at"),
        ("reflection_scores", "created_at"),
        ("rhythm_forecasts", "created_at"),
        ("analytics_cache", "computed_at"),
        ("system_events", "ts"),
    ]

    print(f"\n=== Checking recent updates since {since.isoformat()} ===\n")

    for table, column in tables:
        rows = await conn.fetch(
            f"""
            SELECT *
            FROM {table}
            WHERE {column} > $1
              AND person_id = $2::uuid
            ORDER BY {column} DESC
            LIMIT 3
            """,
            since,
            PERSON_ID,
        )
        print(f"🗂 {table}: {len(rows)} new/updated rows")
        for row in rows:
            snippet = {key: row[key] for key in list(row.keys())[:5]}
            print(json.dumps(snippet, default=str, indent=2))
        print()

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
