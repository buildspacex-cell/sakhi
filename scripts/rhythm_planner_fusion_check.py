#!/usr/bin/env python3
"""
Build 40 Rhythm × Planner Fusion verification.

1) Send a /v2/turn with scheduling intent.
2) Wait for worker pipelines.
3) Fetch planner summary to view rhythm alignment + flow windows.
"""

import asyncio
import json
import os
from typing import Any, Dict

import httpx

PERSON_ID = os.getenv("PERSON_ID", "565bdb63-124b-4692-a039-846fddceff90")
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
TURN_TEXT = os.getenv(
    "RHYTHM_PLANNER_TEXT",
    "Schedule my deep work in the morning peaks and lighter admin when energy dips; keep guitar practice in a calm slot.",
)
WORKER_WAIT = int(os.getenv("RHYTHM_PLANNER_WAIT", "8"))


def banner(msg: str) -> None:
    print("\n" + "=" * 80)
    print(msg)
    print("=" * 80)


async def fire_turn(text: str) -> Dict[str, Any]:
    banner(f"STEP 1 → /v2/turn '{text[:72]}...'")
    async with httpx.AsyncClient(timeout=float(os.getenv("RHYTHM_PLANNER_HTTP_TIMEOUT", "120"))) as client:
        response = await client.post(
            f"{API_BASE}/v2/turn",
            json={"person_id": PERSON_ID, "text": text},
        )
    print(f"/v2/turn status: {response.status_code}")
    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if response.status_code != 200:
        raise SystemExit("Turn failed; aborting fusion check.")
    if WORKER_WAIT > 0:
        print(f"Waiting {WORKER_WAIT}s for worker pipelines…")
        await asyncio.sleep(WORKER_WAIT)
    return payload


async def fetch_planner_summary() -> None:
    banner("STEP 2 → Planner summary with rhythm alignment")
    async with httpx.AsyncClient(timeout=float(os.getenv("RHYTHM_PLANNER_HTTP_TIMEOUT", "90"))) as client:
        response = await client.get(f"{API_BASE}/planner/{PERSON_ID}/summary")
    print(f"/planner/summary status: {response.status_code}")
    data = response.json()
    # Focus on rhythm alignment
    alignment = data.get("rhythm_alignment")
    print("rhythm_alignment:")
    print(json.dumps(alignment, indent=2, ensure_ascii=False))
    return data


async def main() -> None:
    await fire_turn(TURN_TEXT)
    await fetch_planner_summary()
    print("\nRhythm × Planner fusion verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
