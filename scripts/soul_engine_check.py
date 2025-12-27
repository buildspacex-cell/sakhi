#!/usr/bin/env python3
"""
Build 35 Soul Layer verification.

Steps:
1. Run /v2/turn with a soul-revealing utterance to enqueue the reflection pipeline.
2. Wait for worker jobs to finish (reflect_person_memory -> soul engine).
3. Query /soul/{id}/summary to ensure values/identity/purpose/life arcs/conflicts are populated.
4. Inspect DB tables for soul_values, identity_signatures, purpose_themes, life_arcs,
   conflict_records, persona_evolution.
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

import asyncpg
import httpx

PERSON_ID = os.getenv("PERSON_ID", os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90"))
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
DB_URL = os.getenv("DATABASE_URL")
WORKER_WAIT_SECONDS = int(os.getenv("SOUL_WORKER_WAIT", "12"))
TURN_TEXT = os.getenv(
    "SOUL_TEST_TEXT",
    "I've been thinking about balancing creativity, family commitments, and personal growth lately.",
)


def banner(text: str) -> None:
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


async def trigger_turn(text: str) -> Dict[str, Any]:
    banner(f"STEP 1 → /v2/turn '{text}'")
    timeout = float(os.getenv("SOUL_HTTP_TIMEOUT", "120"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.post(
            f"{API_BASE.rstrip('/')}/v2/turn",
            json={"person_id": PERSON_ID, "text": text},
        )
    print("/v2/turn status:", res.status_code)
    payload = {}
    try:
        payload = res.json()
    except Exception:
        pass
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if res.status_code != 200:
        raise SystemExit("Turn call failed; aborting soul check.")
    print(f"Waiting {WORKER_WAIT_SECONDS}s for soul engine job…")
    await asyncio.sleep(WORKER_WAIT_SECONDS)
    return payload


async def fetch_soul_summary() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(f"{API_BASE.rstrip('/')}/soul/{PERSON_ID}/summary")
    data = res.json()
    return {"status": res.status_code, "data": data}


async def inspect_tables() -> None:
    if not DB_URL:
        raise SystemExit("DATABASE_URL not set.")
    conn = await asyncpg.connect(DB_URL, statement_cache_size=0)
    try:
        sections: List[Dict[str, Any]] = [
            {"label": "soul_values", "sql": "SELECT value_name, confidence, created_at FROM soul_values WHERE person_id = $1 ORDER BY confidence DESC LIMIT 5"},
            {"label": "identity_signatures", "sql": "SELECT label, coherence, created_at FROM identity_signatures WHERE person_id = $1 ORDER BY created_at DESC LIMIT 5"},
            {"label": "purpose_themes", "sql": "SELECT theme, momentum, created_at FROM purpose_themes WHERE person_id = $1"},
            {"label": "life_arcs", "sql": "SELECT arc_name, start_scope, end_scope FROM life_arcs WHERE person_id = $1"},
            {"label": "conflict_records", "sql": "SELECT conflict_type, impact, created_at FROM conflict_records WHERE person_id = $1"},
            {"label": "persona_evolution", "sql": "SELECT current_mode, drift_score, updated_at FROM persona_evolution WHERE person_id = $1"},
        ]
        for section in sections:
            rows = await conn.fetch(section["sql"], PERSON_ID)
            print(f"\n[{section['label']}] rows={len(rows)}")
            for idx, row in enumerate(rows, start=1):
                print(f"  #{idx}: {json.dumps(dict(row), default=str, ensure_ascii=False)}")
    finally:
        await conn.close()


async def main() -> None:
    text = " ".join(sys.argv[1:]).strip() or TURN_TEXT
    banner(f"Build 35 Soul Engine Check for person_id={PERSON_ID}")
    await trigger_turn(text)

    banner("STEP 3 → /soul summary API")
    summary_resp = await fetch_soul_summary()
    print(json.dumps(summary_resp, indent=2, ensure_ascii=False))

    banner("STEP 4 → DB tables")
    await inspect_tables()
    print("\nSoul verification complete.")


if __name__ == "__main__":
    asyncio.run(main())
