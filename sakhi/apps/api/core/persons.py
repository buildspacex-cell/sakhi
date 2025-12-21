from __future__ import annotations

import re
from typing import Optional

from sakhi.apps.api.core.db import q

UUID_RE = re.compile(r"^[0-9a-fA-F-]{32,36}$")


async def ensure_person_id(person_ref: Optional[str]) -> str:
    ref = (person_ref or "").strip()
    if ref and UUID_RE.match(ref):
        existing = await q("SELECT 1 FROM persons WHERE id = $1", ref, one=True)
        if existing:
            return ref
        await q("INSERT INTO persons (id) VALUES ($1)", ref)
        return ref

    new_person = await q("INSERT INTO persons DEFAULT VALUES RETURNING id", one=True)
    if not new_person or "id" not in new_person:
        raise RuntimeError("Failed to create person record")
    return str(new_person["id"])
