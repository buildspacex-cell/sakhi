#!/usr/bin/env python3
"""
Build 38 Journaling AI / Listening Intelligence verification script.

Steps:
1. Send a journaling-focused /v2/turn request.
2. Inspect journaling_ai + tone blueprint from the response.
3. Fetch /journal/guide to view smart prompts and layer cues.
"""

import asyncio
import json
import os
from typing import Any, Dict

import httpx

API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
PERSON_ID = os.getenv("PERSON_ID", os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90"))
JOURNAL_TEXT = os.getenv(
    "JOURNAL_AI_TEXT",
    "I'm journaling tonight to understand my body, mind, and goals—can you help me go deeper?",
)


def banner(label: str) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)


async def fire_turn(text: str) -> Dict[str, Any]:
    banner(f"STEP 1 → /v2/turn '{text[:64]}...'")
    async with httpx.AsyncClient(timeout=float(os.getenv("JOURNAL_AI_HTTP_TIMEOUT", "90"))) as client:
        response = await client.post(
            f"{API_BASE}/v2/turn",
            json={"text": text},
        )
    print(f"/v2/turn status: {response.status_code}")
    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if response.status_code != 200:
        raise SystemExit("Journaling turn failed.")
    return payload


async def fetch_guide() -> None:
    banner("STEP 2 → /journal/guide smart prompts")
    async with httpx.AsyncClient(timeout=float(os.getenv("JOURNAL_AI_HTTP_TIMEOUT", "90"))) as client:
        response = await client.get(f"{API_BASE}/journal/guide")
    print(f"/journal/guide status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


async def main() -> None:
    payload = await fire_turn(JOURNAL_TEXT)
    journaling_ai = payload.get("journaling_ai") or payload.get("JournalingAI")
    tone_blueprint = payload.get("toneBlueprint")
    banner("STEP 1b → Extracted journaling AI + tone blueprint")
    print("journaling_ai:", json.dumps(journaling_ai, indent=2, ensure_ascii=False))
    print("tone_blueprint:", json.dumps(tone_blueprint, indent=2, ensure_ascii=False))
    await fetch_guide()
    print("\nJournaling AI verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
