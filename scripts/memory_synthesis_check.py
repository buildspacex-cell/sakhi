#!/usr/bin/env python3
"""
Build 37 Memory Synthesis verification script.

Steps:
1. Trigger a conversational turn (optional, keeps pipeline context active).
2. Call /memory/{person}/synthesis for weekly + monthly horizons.
3. Fetch weekly/monthly summaries and key DB tables for drift + compression.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

import asyncpg
import httpx

PERSON_ID = os.getenv("PERSON_ID", os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90"))
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
DB_URL = os.getenv("DATABASE_URL")
TURN_TEXT = os.getenv(
    "MEMORY_SYNTHESIS_TEXT",
    "Could you help me reflect on this past week and what I should carry into next month?",
)


def banner(label: str) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)


async def fire_turn() -> None:
    banner(f"STEP 1 → /v2/turn '{TURN_TEXT[:64]}...'")
    async with httpx.AsyncClient(timeout=float(os.getenv("MEMORY_SYNTHESIS_HTTP_TIMEOUT", "90"))) as client:
        response = await client.post(
            f"{API_BASE}/v2/turn",
            json={"person_id": PERSON_ID, "text": TURN_TEXT},
        )
    print(f"/v2/turn status: {response.status_code}")
    try:
        payload = response.json()
    except Exception:
        payload = {}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if response.status_code != 200:
        raise SystemExit("Turn request failed; aborting.")


async def trigger_synthesis(horizon: str) -> Dict[str, Any]:
    banner(f"STEP 2 → Trigger memory synthesis horizon={horizon}")
    async with httpx.AsyncClient(timeout=float(os.getenv("MEMORY_SYNTHESIS_HTTP_TIMEOUT", "90"))) as client:
        response = await client.post(
            f"{API_BASE}/memory/{PERSON_ID}/synthesis",
            params={"horizon": horizon},
        )
    print(f"/memory/{PERSON_ID}/synthesis?horizon={horizon} status: {response.status_code}")
    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if response.status_code != 200:
        raise SystemExit("Synthesis trigger failed.")
    return payload


async def fetch_bundle() -> None:
    banner("STEP 3 → Fetch weekly + monthly bundles")
    async with httpx.AsyncClient(timeout=float(os.getenv("MEMORY_SYNTHESIS_HTTP_TIMEOUT", "90"))) as client:
        weekly_res, monthly_res = await asyncio.gather(
            client.get(f"{API_BASE}/memory/{PERSON_ID}/weekly"),
            client.get(f"{API_BASE}/memory/{PERSON_ID}/monthly"),
        )
    print(f"/memory/weekly status: {weekly_res.status_code}")
    print(json.dumps(weekly_res.json(), indent=2, ensure_ascii=False))
    print(f"/memory/monthly status: {monthly_res.status_code}")
    print(json.dumps(monthly_res.json(), indent=2, ensure_ascii=False))


async def inspect_tables() -> None:
    if not DB_URL:
        print("DATABASE_URL not set; skipping DB inspection.")
        return

    banner("STEP 4 → DB tables snapshot (weekly/monthly summaries)")
    conn = await asyncpg.connect(DB_URL, statement_cache_size=0)
    sections: List[Dict[str, Any]] = [
        {
            "label": "memory_weekly_summaries",
            "sql": """
                SELECT week_start, week_end, highlights, drift_score
                FROM memory_weekly_summaries
                WHERE person_id = $1
                ORDER BY week_start DESC
                LIMIT 5
            """,
        },
        {
            "label": "memory_monthly_recaps",
            "sql": """
                SELECT month_scope, highlights, chapter_hint, drift_score
                FROM memory_monthly_recaps
                WHERE person_id = $1
                ORDER BY created_at DESC
                LIMIT 5
            """,
        },
        {
            "label": "memory_theme_drift_events",
            "sql": """
                SELECT horizon, from_theme, to_theme, drift_score, created_at
                FROM memory_theme_drift_events
                WHERE person_id = $1
                ORDER BY created_at DESC
                LIMIT 5
            """,
        },
        {
            "label": "memory_semantic_rollups",
            "sql": """
                SELECT semantic_summary, strength, created_at
                FROM memory_semantic_rollups
                WHERE person_id = $1
                ORDER BY created_at DESC
                LIMIT 5
            """,
        },
    ]
    try:
        for section in sections:
            rows = await conn.fetch(section["sql"], PERSON_ID)
            print(f"\n[{section['label']}] rows={len(rows)}")
            for idx, row in enumerate(rows, start=1):
                serialized = {k: row[k] for k in row.keys()}
                print(f"  #{idx}: {json.dumps(serialized, default=str, ensure_ascii=False)}")
    finally:
        await conn.close()


async def main() -> None:
    banner(f"Build 37 Memory Synthesis Check for person_id={PERSON_ID}")
    await fire_turn()
    await trigger_synthesis("weekly")
    await trigger_synthesis("monthly")
    await fetch_bundle()
    await inspect_tables()
    print("\nMemory synthesis verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
