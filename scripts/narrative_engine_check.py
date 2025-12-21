"""
Build 42 Narrative Engine sanity check.

Prereqs: API running, worker running, migration applied: infra/sql/20251122_build42_narrative_engine.sql
Env: API_BASE, PERSON_ID
"""

import asyncio
import os
import time
import httpx

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
PERSON_ID = os.environ.get("PERSON_ID", "565bdb63-124b-4692-a039-846fddceff90")


async def send_turn(client: httpx.AsyncClient) -> None:
    text = "Give me a sense of the season I'm in and how my identity is evolving toward creativity and discipline."
    print("\nSTEP 1 → /v2/turn")
    resp = await client.post(f"{API_BASE}/v2/turn", json={"sessionId": PERSON_ID, "text": text}, timeout=40)
    print("/v2/turn status:", resp.status_code)
    try:
        print(resp.json())
    except Exception:
        print(resp.text)


async def fetch_narrative(client: httpx.AsyncClient) -> None:
    print("\nSTEP 2 → /narrative/{person}/summary")
    resp = await client.get(f"{API_BASE}/narrative/{PERSON_ID}/summary", timeout=20)
    print("/narrative summary status:", resp.status_code)
    try:
        print(resp.json())
    except Exception:
        print(resp.text)


async def main() -> None:
    async with httpx.AsyncClient() as client:
        await send_turn(client)
        print("Waiting 6s for worker narrative job…")
        time.sleep(6)
        await fetch_narrative(client)


if __name__ == "__main__":
    asyncio.run(main())
