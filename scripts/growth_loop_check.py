#!/usr/bin/env python3
"""
Build 39 Growth Loop verification script.

1. Send a /v2/turn with habit-oriented text.
2. Trigger planner worker wait, then call /growth/{person}/summary.
3. Optionally log a daily check-in.
"""

import asyncio
import json
import os
import time
from typing import Any, Dict

import httpx

PERSON_ID = os.getenv("PERSON_ID", "565bdb63-124b-4692-a039-846fddceff90")
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
TURN_TEXT = os.getenv(
    "GROWTH_LOOP_TEXT",
    "Help me track my morning focus habit and adjust my guitar practice schedule with micro steps.",
)
WORKER_WAIT = int(os.getenv("GROWTH_WORKER_WAIT", "6"))


def banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


async def fire_turn(text: str) -> Dict[str, Any]:
    banner(f"STEP 1 → /v2/turn '{text[:64]}...'")
    async with httpx.AsyncClient(timeout=float(os.getenv("GROWTH_HTTP_TIMEOUT", "120"))) as client:
        response = await client.post(
            f"{API_BASE}/v2/turn",
            json={"person_id": PERSON_ID, "text": text},
        )
    print(f"/v2/turn status: {response.status_code}")
    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if response.status_code != 200:
        raise SystemExit("Turn failed; aborting growth check.")
    if WORKER_WAIT > 0:
        print(f"Waiting {WORKER_WAIT}s for worker pipelines…")
        await asyncio.sleep(WORKER_WAIT)
    return payload


async def fetch_growth_summary() -> None:
    banner("STEP 2 → Growth summary API")
    async with httpx.AsyncClient(timeout=float(os.getenv("GROWTH_HTTP_TIMEOUT", "60"))) as client:
        response = await client.get(f"{API_BASE}/growth/{PERSON_ID}/summary")
    print(f"/growth summary status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


async def log_checkin() -> None:
    banner("STEP 3 → Record daily check-in")
    payload = {
        "energy": 0.7,
        "mood": "steady",
        "reflection": "Staying consistent with my focus habit after today's planning session.",
        "plan_adjustment": {"notes": "Shift guitar practice to evenings"},
    }
    async with httpx.AsyncClient(timeout=float(os.getenv("GROWTH_HTTP_TIMEOUT", "60"))) as client:
        response = await client.post(f"{API_BASE}/growth/{PERSON_ID}/checkin", json=payload)
    print(f"/growth checkin status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


async def main() -> None:
    await fire_turn(TURN_TEXT)
    await fetch_growth_summary()
    await log_checkin()
    await fetch_growth_summary()
    print("\nGrowth loop verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
