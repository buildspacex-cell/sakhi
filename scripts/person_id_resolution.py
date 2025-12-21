"""
Utility to resolve person/profile IDs and report presence in core tables.

Usage:
    PERSON_ID=<uuid> poetry run python scripts/person_id_resolution.py
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sakhi.apps.api.core.db import q


async def resolve_person_id(person_id: str) -> Dict[str, Any]:
    resolution = {"input": person_id, "profile_exists": False, "mapped_person_id": None}
    profile = await q("SELECT user_id FROM profiles WHERE user_id = $1", person_id, one=True)
    if profile:
        resolution["profile_exists"] = True
        resolution["mapped_person_id"] = person_id
        return resolution

    mapping = await q(
        "SELECT person_id FROM person_profile_map WHERE person_id = $1 OR profile_user_id = $1",
        person_id,
        one=True,
    )
    if mapping:
        resolution["mapped_person_id"] = mapping.get("person_id")
    return resolution


async def main() -> None:
    pid = os.environ.get("PERSON_ID")
    if not pid:
        raise SystemExit("PERSON_ID env var is required.")
    resolved = await resolve_person_id(pid)
    print("Resolution:", resolved)
    if resolved.get("mapped_person_id"):
        mapped = resolved["mapped_person_id"]
        checks = {}
        for tbl, col in [
            ("journal_entries", "person_id"),
            ("planned_items", "person_id"),
            ("focus_sessions", "person_id"),
            ("relationship_state", "person_id"),
            ("rhythm_state", "person_id"),
        ]:
            row = await q(f"SELECT count(*) AS c FROM {tbl} WHERE {col} = $1", mapped, one=True)
            checks[tbl] = row.get("c") if row else 0
        print("Presence:", checks)


if __name__ == "__main__":
    asyncio.run(main())
