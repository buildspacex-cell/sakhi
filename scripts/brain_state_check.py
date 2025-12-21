"""
Quick harness to validate Personal OS Brain (Build 47).

Requires:
- API server running (default http://localhost:8000)
- DATABASE_URL set
- PERSON_ID env var

Usage:
    PERSON_ID=<uuid> poetry run python scripts/brain_state_check.py
Optional:
    BASE_URL=http://localhost:9000 PERSON_ID=<uuid> poetry run python scripts/brain_state_check.py
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict

import httpx

# Ensure local package imports resolve when running via plain `python`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sakhi.apps.logic.brain import brain_engine

BASE_URL = os.getenv("BASE_URL") or os.getenv("API_BASE", "http://localhost:8000")
PERSON_ID = os.environ.get("PERSON_ID")


async def call(path: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}{path}", params={"person_id": PERSON_ID, "force_refresh": True})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            raise SystemExit(f"API {path} failed: {exc} Body: {body}") from exc
        return resp.json()


async def main() -> None:
    if not PERSON_ID:
        raise SystemExit("PERSON_ID env var is required.")

    print(f"Running brain refresh for {PERSON_ID} ...")
    state = await brain_engine.refresh_brain(PERSON_ID, refresh_journey=False)
    print("Persisted brain snapshot (truncated):")
    keys = [
        "goals_state",
        "rhythm_state",
        "emotional_state",
        "relationship_state",
        "environment_state",
        "habits_state",
        "focus_state",
        "top_priorities",
        "life_chapter",
    ]
    for key in keys:
        print(f"- {key}: {str(state.get(key))[:280]}")

    print("\nAPI check:")
    state_resp = await call("/brain/state")
    summary_resp = await call("/brain/summary")
    priorities_resp = await call("/brain/priorities")
    print(f"- /brain/state keys: {list((state_resp.get('data') or {}).keys())}")
    print(f"- /brain/summary: {summary_resp.get('data')}")
    print(f"- /brain/priorities: {priorities_resp.get('data')}")


if __name__ == "__main__":
    asyncio.run(main())
