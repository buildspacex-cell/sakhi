#!/usr/bin/env python3
"""
Build 34 Rhythm Engine verification script.

Steps:
1. Log a synthetic breath session to provide calm/energy data.
2. Hit /v2/turn with a rhythm-heavy utterance (queues turn_rhythm_update).
3. Wait for the worker to finish.
4. Fetch /rhythm/state and /rhythm/curve APIs.
5. Inspect DB tables: rhythm_state, rhythm_daily_curve, rhythm_chronotype,
   rhythm_planner_alignment, and planner summary (to ensure rhythm alignment surfaced).
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
WORKER_WAIT_SECONDS = int(os.getenv("RHYTHM_WORKER_WAIT", "8"))
TURN_TEXT = os.getenv(
    "RHYTHM_TEST_TEXT",
    "I'm feeling a little tired lately. Help me pace my week wisely with good rest.",
)


def banner(text: str) -> None:
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


async def post_breath_session() -> None:
    payload = {
        "person_id": PERSON_ID,
        "duration_sec": 60,
        "rates": [6.2, 5.8, 6.0],
        "pattern": "equal",
        "notes": "Test calm session",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(f"{API_BASE.rstrip('/')}/breath/session", json=payload)
    if res.status_code != 200:
        raise SystemExit(f"Breath session failed status={res.status_code} body={res.text}")
    print("Logged breath session:", res.json())


async def trigger_turn(text: str) -> Dict[str, Any]:
    banner(f"STEP 2 → /v2/turn '{text}'")
    timeout = float(os.getenv("RHYTHM_HTTP_TIMEOUT", "90"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.post(
            f"{API_BASE.rstrip('/')}/v2/turn",
            json={"person_id": PERSON_ID, "text": text},
        )
    print("/v2/turn status:", res.status_code)
    body = {}
    try:
        body = res.json()
    except Exception:
        pass
    print(json.dumps(body, indent=2, ensure_ascii=False))
    if res.status_code != 200:
        raise SystemExit("Turn call failed; aborting rhythm check.")
    print(f"Waiting {WORKER_WAIT_SECONDS}s for worker rhythm job…")
    await asyncio.sleep(WORKER_WAIT_SECONDS)
    return body


async def fetch_api(path: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(f"{API_BASE.rstrip('/')}{path}")
    return {"status": res.status_code, "data": res.json() if res.content else {}}


async def inspect_tables() -> None:
    if not DB_URL:
        raise SystemExit("DATABASE_URL not set.")

    conn = await asyncpg.connect(DB_URL, statement_cache_size=0)
    try:
        sections: List[Dict[str, Any]] = [
            {
                "label": "rhythm_state",
                "sql": """
                    SELECT body_energy, mind_focus, emotion_tone,
                           fatigue_level, stress_level, next_peak, next_lull, updated_at
                    FROM rhythm_state
                    WHERE person_id = $1
                """,
            },
            {
                "label": "rhythm_chronotype",
                "sql": """
                    SELECT chronotype, score, evidence, updated_at
                    FROM rhythm_chronotype
                    WHERE person_id = $1
                """,
            },
            {
                "label": "rhythm_daily_curve",
                "sql": """
                    SELECT day_scope, confidence, created_at
                    FROM rhythm_daily_curve
                    WHERE person_id = $1
                    ORDER BY day_scope DESC
                    LIMIT 3
                """,
            },
            {
                "label": "rhythm_planner_alignment",
                "sql": """
                    SELECT horizon, recommendations, generated_at
                    FROM rhythm_planner_alignment
                    WHERE person_id = $1
                """,
            },
        ]
        for section in sections:
            rows = await conn.fetch(section["sql"], PERSON_ID)
            print(f"\n[{section['label']}] rows={len(rows)}")
            for idx, row in enumerate(rows, start=1):
                print(f"  #{idx}: {json.dumps(dict(row), default=str, ensure_ascii=False)}")
    finally:
        await conn.close()


async def planner_summary_check() -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(f"{API_BASE.rstrip('/')}/planner/{PERSON_ID}/summary")
    data = res.json()
    print("\n[Planner summary] status:", res.status_code)
    print(json.dumps(data, indent=2, ensure_ascii=False))


async def main() -> None:
    text = " ".join(sys.argv[1:]).strip() or TURN_TEXT
    banner(f"Build 34 Rhythm Engine Check for person_id={PERSON_ID}")
    await post_breath_session()
    await trigger_turn(text)

    banner("STEP 4 → Rhythm API responses")
    state_resp = await fetch_api(f"/rhythm/{PERSON_ID}/state")
    print("\n/rhythm/state:", json.dumps(state_resp, indent=2, ensure_ascii=False))
    curve_resp = await fetch_api(f"/rhythm/{PERSON_ID}/curve")
    print("\n/rhythm/curve:", json.dumps(curve_resp, indent=2, ensure_ascii=False))

    banner("STEP 5 → DB validation")
    await inspect_tables()

    banner("STEP 6 → Planner summary alignment")
    await planner_summary_check()
    print("\nRhythm verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
