#!/usr/bin/env python3
"""
Build 33 planner verification script.

Step 3: Trigger /v2/turn with a planner-rich utterance and allow the worker to run.
Step 4: Inspect planner_goals, planner_milestones, planned_items, planner_context_cache.
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

import asyncpg
import httpx

PERSON_ID = os.getenv("PERSON_ID", "565bdb63-124b-4692-a039-846fddceff90")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
DB_URL = os.getenv("DATABASE_URL")
TURN_TEXT = os.getenv(
    "PLANNER_TEST_TEXT",
    "Please help me plan weekly guitar practice, schedule a recording session next month, "
    "and remind me every Friday to review progress.",
)
WORKER_WAIT_SECONDS = int(os.getenv("PLANNER_WORKER_WAIT", "6"))


def banner(msg: str) -> None:
    print("\n" + "=" * 80)
    print(msg)
    print("=" * 80)


async def fire_turn(text: str) -> Dict[str, Any]:
    banner(f"STEP 3 → /v2/turn request text='{text}'")
    timeout = float(os.getenv("PLANNER_HTTP_TIMEOUT", "120"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            API_BASE.rstrip("/") + "/v2/turn",
            json={"person_id": PERSON_ID, "text": text},
        )
    print(f"/v2/turn status={response.status_code}")
    try:
        payload = response.json()
    except Exception:
        payload = {}
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if response.status_code != 200:
        raise SystemExit("Turn call failed; aborting planner check.")

    print(f"Waiting {WORKER_WAIT_SECONDS}s for worker pipelines to finish…")
    await asyncio.sleep(WORKER_WAIT_SECONDS)
    return payload


async def inspect_tables() -> None:
    if not DB_URL:
        raise SystemExit("DATABASE_URL not set; cannot query planner tables.")

    banner("STEP 4 → Planner tables snapshot")
    conn = await asyncpg.connect(DB_URL, statement_cache_size=0)
    try:
        sections: List[Dict[str, Any]] = [
            {
                "label": "planner_goals",
                "sql": """
                    SELECT id, title, horizon, priority, status, updated_at
                    FROM planner_goals
                    WHERE person_id = $1
                    ORDER BY updated_at DESC
                    LIMIT 10
                """,
            },
            {
                "label": "planner_milestones",
                "sql": """
                    SELECT id, goal_id, title, due_ts, horizon, status, sequence
                    FROM planner_milestones
                    WHERE person_id = $1
                    ORDER BY COALESCE(due_ts, NOW()) DESC
                    LIMIT 10
                """,
            },
            {
                "label": "planned_items",
                "sql": """
                    SELECT id, label, goal_id, milestone_id, due_ts, priority, status, energy, horizon, origin_id
                    FROM planned_items
                    WHERE person_id = $1
                    ORDER BY COALESCE(due_ts, NOW()) DESC
                    LIMIT 15
                """,
            },
            {
                "label": "planner_context_cache",
                "sql": """
                    SELECT payload, updated_at
                    FROM planner_context_cache
                    WHERE person_id = $1
                """,
            },
        ]

        for section in sections:
            rows = await conn.fetch(section["sql"], PERSON_ID)
            print(f"\n[{section['label']}] rows={len(rows)}")
            for idx, row in enumerate(rows, start=1):
                serialized = {k: row[k] for k in row.keys()}
                print(f"  #{idx}: {json.dumps(serialized, default=str, ensure_ascii=False)}")
    finally:
        await conn.close()


async def main() -> None:
    text = " ".join(sys.argv[1:]).strip() or TURN_TEXT
    banner(f"Planner pipeline check for person_id={PERSON_ID}")
    await fire_turn(text)
    await inspect_tables()
    print("\nPlanner verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
