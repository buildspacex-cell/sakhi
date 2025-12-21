#!/usr/bin/env python3
"""
Build 36 Tone Engine verification script.

1. Send a conversational turn.
2. Wait for worker updates.
3. Fetch /debug/tone_profile to inspect the Conversation Tone Engine output.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict

import httpx

PERSON_ID = os.getenv("PERSON_ID", "565bdb63-124b-4692-a039-846fddceff90")
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
TURN_TEXT = os.getenv(
    "TONE_TEST_TEXT",
    "I want to keep a warm tone even when I'm tired—can you help me find a supportive rhythm for tonight?",
)
WORKER_WAIT_SECONDS = int(os.getenv("TONE_WORKER_WAIT", "4"))


def banner(label: str) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)


async def fire_turn(text: str) -> Dict[str, Any]:
    banner(f"STEP 1 → /v2/turn '{text[:64]}...'")
    async with httpx.AsyncClient(timeout=float(os.getenv("TONE_HTTP_TIMEOUT", "60"))) as client:
        response = await client.post(
            f"{API_BASE}/v2/turn",
            json={"person_id": PERSON_ID, "text": text},
        )
    print(f"/v2/turn status: {response.status_code}")
    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if response.status_code != 200:
        raise SystemExit("Turn failed; aborting tone check.")
    if WORKER_WAIT_SECONDS > 0:
        print(f"Waiting {WORKER_WAIT_SECONDS}s for worker tone + persona jobs…")
        await asyncio.sleep(WORKER_WAIT_SECONDS)
    return payload


async def fetch_tone_profile() -> None:
    banner("STEP 2 → /debug/tone_profile snapshot")
    async with httpx.AsyncClient(timeout=float(os.getenv("TONE_HTTP_TIMEOUT", "60"))) as client:
        response = await client.get(
            f"{API_BASE}/debug/tone_profile",
            params={"person_id": PERSON_ID},
        )
    print(f"/debug/tone_profile status: {response.status_code}")
    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if response.status_code != 200:
        raise SystemExit("Tone profile fetch failed.")


async def main() -> None:
    text = " ".join(sys.argv[1:]).strip() or TURN_TEXT
    banner(f"Build 36 Tone Engine Check for person_id={PERSON_ID}")
    await fire_turn(text)
    await fetch_tone_profile()
    print("\nTone verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
