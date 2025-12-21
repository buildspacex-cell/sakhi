#!/usr/bin/env python3
"""
Sakhi MVP Test Runner v1.1 (Pinned User Version)

Runs all tests ONLY for one canonical person_id:
565bdb63-124b-4692-a039-846fddceff90
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import asyncpg
import httpx
from termcolor import colored

# -------------------------------------------------------------------
# HARD-PINNED USER ID (Primary identity from profiles)
# -------------------------------------------------------------------

PERSON_ID = "565bdb63-124b-4692-a039-846fddceff90"

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
DB_URL = os.getenv("DATABASE_URL")

# -------------------------------------------------------------------
# Helper printing
# -------------------------------------------------------------------

def banner(msg: str):
    print("\n" + "=" * 90)
    print(colored(msg, "cyan"))
    print("=" * 90)


def ok(msg: str):
    print(colored("✔ " + msg, "green"))


def fail(msg: str):
    print(colored("✘ " + msg, "red"))


def warn(msg: str):
    print(colored("⚠ " + msg, "yellow"))

# -------------------------------------------------------------------
# Step 1: Backend health
# -------------------------------------------------------------------

async def backend_health(client: httpx.AsyncClient) -> bool:
    banner("BACKEND HEALTH CHECK")
    print(colored(f"Using PERSON_ID = {PERSON_ID}", "yellow"))

    try:
        r = await client.get(API_BASE + "/docs")
        if r.status_code == 200:
            ok("FastAPI backend reachable.")
            return True
        else:
            fail(f"Backend returned status {r.status_code}.")
            return False
    except Exception as e:
        fail(f"Backend not reachable: {e}")
        return False

# -------------------------------------------------------------------
# Step 2: Worker check
# -------------------------------------------------------------------

async def worker_health() -> bool:
    banner("WORKER HEALTH CHECK")

    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0)
        r.ping()
        ok("Redis reachable — worker likely running.")
        return True
    except Exception as e:
        fail(f"Redis not reachable — worker may be down: {e}")
        return False

# -------------------------------------------------------------------
# Step 3: Observe
# -------------------------------------------------------------------

async def test_observe(client: httpx.AsyncClient) -> Dict[str, Any]:
    banner("OBSERVE PIPELINE TEST")

    payload = {
        "person_id": PERSON_ID,
        "text": "I started learning guitar today, felt motivated.",
        "tags": [],
        "layer": "conversation",
    }

    r = await client.post(API_BASE + "/memory/observe", json=payload)
    if r.status_code != 200:
        fail(f"/memory/observe failed [{r.status_code}]")
        return {}

    data = r.json()

    entry_id = data.get("entry_id")
    if entry_id:
        ok(f"Journal entry created: {entry_id}")
    else:
        fail("No entry_id returned.")

    if "triage" in data:
        ok("Triage extracted.")
    else:
        warn("Triage missing.")

    return data

# -------------------------------------------------------------------
# Step 4: Observe with web snippet enrichment
# -------------------------------------------------------------------

async def test_observe_web(client: httpx.AsyncClient) -> Dict[str, Any]:
    banner("OBSERVE ENRICHMENT TEST")

    payload = {
        "person_id": PERSON_ID,
        "text": "best guitar for beginners",
        "tags": [],
        "layer": "conversation",
    }

    r = await client.post(API_BASE + "/memory/observe", json=payload)
    data = r.json()

    if data.get("web"):
        ok("Web snippet enrichment applied.")
    else:
        warn("Web snippet not applied — ALLOW_WEB may be off.")

    return data

# -------------------------------------------------------------------
# Step 5: /v2/turn
# -------------------------------------------------------------------

async def test_turn(client: httpx.AsyncClient, text: str) -> Dict[str, Any]:
    banner(f"TURN PIPELINE TEST: '{text}'")

    payload = {
        "person_id": PERSON_ID,
        "text": text
    }

    r = await client.post(API_BASE + "/v2/turn", json=payload)
    if r.status_code != 200:
        fail(f"/v2/turn failed [{r.status_code}]")
        return {}

    data = r.json()

    if "reply" in data:
        ok("Reply generated.")
    else:
        fail("Reply missing.")

    if data.get("reasoning"):
        ok("Reasoning engine output present.")
    else:
        warn("Reasoning missing.")

    if data.get("memory_recall"):
        ok("Memory recall present.")
    else:
        warn("Memory recall missing.")

    if data.get("persona_update"):
        ok("Persona updated.")
    else:
        warn("Persona update missing.")

    if data.get("planner"):
        ok("Planner triggered.")
    else:
        warn("Planner missing — may be normal if no intents.")

    if data.get("narrative_trace"):
        ok("Narrative trace generated.")
    else:
        warn("Narrative trace missing.")

    return data

# -------------------------------------------------------------------
# Step 6: DB checks
# -------------------------------------------------------------------

async def db_checks(entry_id: str) -> bool:
    banner("DATABASE VALIDATION")

    try:
        conn = await asyncpg.connect(DB_URL, statement_cache_size=0)
    except Exception as e:
        fail(f"DB connection failed: {e}")
        return False

    row = await conn.fetchrow(
        "SELECT id, content FROM journal_entries WHERE id = $1", entry_id
    )
    if row:
        ok("journal_entries row exists.")
    else:
        fail("journal_entries missing row.")

    await conn.close()
    return True

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Backend
        if not await backend_health(client):
            return

        # 2. Worker
        await worker_health()

        # 3. Observe
        obs = await test_observe(client)
        entry_id = obs.get("entry_id")

        # 4. DB check
        if entry_id:
            await asyncio.sleep(1)
            await db_checks(entry_id)

        # 5. Observe with snippet
        await test_observe_web(client)

        # 6. Conversation flows
        await test_turn(client, "I'm feeling tired today.")
        await test_turn(client, "Help me plan my guitar practice.")

        banner("ALL TESTS COMPLETED")

if __name__ == "__main__":
    asyncio.run(main())
