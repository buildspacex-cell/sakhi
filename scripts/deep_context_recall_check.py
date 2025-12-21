"""
Build 41 Deep Context Recall smoke test.

Prereqs:
- API server running (API_BASE)
- DATABASE_URL set for live Postgres (read access)
- MIGRATION applied: infra/sql/20251122_build41_deep_context_recall.sql

What it does:
1) Sends a turn text to /v2/turn to create a new memory + recall.
2) Waits briefly for worker jobs.
3) Fetches /debug/deep_recall to inspect stored recalls/life events/threads.
"""

import asyncio
import os
import time
from typing import Any, Dict

import httpx

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
PERSON_ID = os.environ.get("PERSON_ID", "565bdb63-124b-4692-a039-846fddceff90")
TURN_TIMEOUT = float(os.environ.get("TURN_TIMEOUT", "90"))


def _ensure_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            import json

            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


async def send_turn(client: httpx.AsyncClient) -> None:
    text = "Link my current focus on guitar practice with past creative peaks, and remember the recent planning session."
    print("\nSTEP 1 → /v2/turn")
    resp = await client.post(f"{API_BASE}/v2/turn", json={"sessionId": PERSON_ID, "text": text}, timeout=TURN_TIMEOUT)
    print("/v2/turn status:", resp.status_code)
    try:
        print(resp.json())
    except Exception:
        print(resp.text)


async def fetch_deep_recall(client: httpx.AsyncClient) -> None:
    print("\nSTEP 2 → /debug/deep_recall")
    resp = await client.get(f"{API_BASE}/debug/deep_recall", params={"person_id": PERSON_ID, "limit": 3}, timeout=20)
    print("/debug/deep_recall status:", resp.status_code)
    try:
        payload = resp.json()
    except Exception:
        print(resp.text)
        return

    print("\nRecalls:")
    for idx, rec in enumerate(payload.get("recalls", []), start=1):
        print(f"  #{idx} summary: {rec.get('stitched_summary')}")
        compact = _ensure_mapping(rec.get("compact"))
        print(f"     compact keys: {list(compact.keys())}")
        print(f"     signals: {rec.get('signals')}")
        print(f"     confidence: {rec.get('confidence')}")
        print(f"     created_at: {rec.get('created_at')}")

    print("\nLife-event links:")
    for idx, ev in enumerate(payload.get("life_events", []), start=1):
        print(f"  #{idx} event: {ev.get('event_label')} weight={ev.get('weight')}")

    print("\nThreads:")
    for idx, th in enumerate(payload.get("threads", []), start=1):
        print(f"  #{idx} thread_id: {th.get('thread_id')} last_turn: {th.get('last_turn_id')} hint: {th.get('continuity_hint')}")


async def main() -> None:
    async with httpx.AsyncClient() as client:
        try:
            await send_turn(client)
        except httpx.ReadTimeout:
            print("Timed out calling /v2/turn. Ensure API_BASE is reachable and increase timeout if needed.")
            return
        print("Waiting 126s for worker jobs…")
        time.sleep(126)
        await fetch_deep_recall(client)


if __name__ == "__main__":
    asyncio.run(main())
