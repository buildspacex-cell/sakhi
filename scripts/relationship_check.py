#!/usr/bin/env python3
"""
Build 44 Relationship Model smoke test.

Steps:
1) Send a turn to /v2/turn to trigger turn_persona_update worker.
2) Wait for the worker to run.
3) Inspect relationship_state and personal_model.relationship_state.

Env vars:
  API_BASE           (default http://localhost:8000)
  PERSON_ID          (user id)
  DATABASE_URL       (required for DB inspection)
  TURN_TIMEOUT       (seconds, default 90)
  REL_WAIT_SECONDS   (sleep between turn and DB read, default 15)
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict

import asyncpg
import httpx

API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
PERSON_ID = os.getenv("PERSON_ID", os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90"))
DB_URL = os.getenv("DATABASE_URL")
TURN_TIMEOUT = float(os.getenv("TURN_TIMEOUT", "90"))
REL_WAIT_SECONDS = int(os.getenv("REL_WAIT_SECONDS", "15"))
TURN_TEXT = os.getenv(
    "REL_TEST_TEXT",
    "Check in on how well we're syncing lately—keep it warm and light.",
)


def banner(msg: str) -> None:
    print("\n" + "=" * 80)
    print(msg)
    print("=" * 80)


async def send_turn(client: httpx.AsyncClient) -> None:
    banner(f"STEP 1 → /v2/turn '{TURN_TEXT[:64]}...'")
    resp = await client.post(
        f"{API_BASE}/v2/turn",
        json={"sessionId": PERSON_ID, "text": TURN_TEXT},
        timeout=TURN_TIMEOUT,
    )
    print("/v2/turn status:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(resp.text)
    if resp.status_code != 200:
        raise SystemExit("Turn call failed; aborting.")


async def inspect_relationship(conn: asyncpg.Connection) -> None:
    banner("STEP 2 → DB relationship_state + personal_model.relationship_state")
    row = await conn.fetchrow(
        """
        SELECT trust_score, attunement_score, emotional_safety, closeness_stage, updated_at
        FROM relationship_state
        WHERE person_id = $1
        """,
        PERSON_ID,
    )
    print("relationship_state:", dict(row) if row else "none")

    pm = await conn.fetchrow(
        """
        SELECT relationship_state
        FROM personal_model
        WHERE person_id = $1
        """,
        PERSON_ID,
    )
    try:
        print("personal_model.relationship_state:", dict(pm) if pm else "none")
    except Exception:
        print("personal_model.relationship_state:", pm)


async def main() -> None:
    if not DB_URL:
        raise SystemExit("DATABASE_URL not set; needed for inspection.")

    async with httpx.AsyncClient() as client:
        try:
            await send_turn(client)
        except httpx.ReadTimeout:
            print("Timed out calling /v2/turn. Increase TURN_TIMEOUT if needed.")
            return

    print(f"Waiting {REL_WAIT_SECONDS}s for worker jobs…")
    time.sleep(REL_WAIT_SECONDS)

    conn = await asyncpg.connect(DB_URL, statement_cache_size=0)
    try:
        await inspect_relationship(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
