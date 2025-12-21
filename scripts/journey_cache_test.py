"""
Quick integration test for Journey Renderer cache (Build 46).

Requires:
- API server running (default http://localhost:8000)
- DATABASE_URL set (reused by sakhi.apps.api.core.db)
- PERSON_ID env var pointing to an existing person in your DB

Usage:
    PERSON_ID=<uuid> poetry run python scripts/journey_cache_test.py
Optional:
    BASE_URL=http://localhost:9000 PERSON_ID=<uuid> poetry run python scripts/journey_cache_test.py
"""

import asyncio
import json
import os
from typing import Dict, Tuple

import httpx

from sakhi.apps.api.core.db import q

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
PERSON_ID = os.environ.get("PERSON_ID")


async def call_endpoint(path: str, force: bool) -> Dict:
    params = {"person_id": PERSON_ID, "force_refresh": force}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


async def fetch_cache_rows() -> list[Dict]:
    return await q(
        """
        SELECT scope, updated_at, payload
        FROM journey_cache
        WHERE person_id = $1
        ORDER BY updated_at DESC
        """,
        PERSON_ID,
    )


async def run() -> None:
    if not PERSON_ID:
        raise SystemExit("PERSON_ID env var is required.")

    routes: Tuple[Tuple[str, str], ...] = (
        ("/journey/today", "today"),
        ("/journey/week", "week"),
        ("/journey/month", "month"),
        ("/journey/life-chapters", "life"),
    )

    print(f"Base URL: {BASE_URL}")
    print(f"Person:   {PERSON_ID}")
    print("\nHitting endpoints with force_refresh=true (build + write cache)...")
    fresh_payloads = {}
    for path, scope in routes:
        payload = await call_endpoint(path, True)
        fresh_payloads[scope] = payload
        print(f"  ✅ {path} (force_refresh=true)")

    print("\nHitting endpoints without force_refresh (should hit cache)...")
    for path, scope in routes:
        payload = await call_endpoint(path, False)
        if payload != fresh_payloads[scope]:
            print(f"  ⚠️  {path} returned different payload than cached build.")
        else:
            print(f"  ✅ {path} (cache hit matches)")

    print("\nInspecting journey_cache rows...")
    rows = await fetch_cache_rows()
    if not rows:
        print("  ⚠️  No cache rows found for this person.")
    else:
        for row in rows:
            scope = row.get("scope")
            ts = row.get("updated_at")
            sample = json.dumps(row.get("payload", {}), indent=2)[:300]
            print(f"\n--- scope={scope} updated_at={ts} ---")
            print(sample)


if __name__ == "__main__":
    asyncio.run(run())
