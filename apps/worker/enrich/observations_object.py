from __future__ import annotations

import uuid
from typing import List

import re

GOAL_RE = re.compile(r"\b(i (want|plan|aim|need) to)\s+(?P<title>[^.!?\n]{3,160})", re.I)

DOMAIN_MAP = {
    "health": {"health", "workout", "gym", "diet", "sleep", "meditation"},
    "career": {"career", "job", "interview", "promotion", "office"},
    "finance": {"budget", "emi", "loan", "money", "savings", "pay"},
    "relationships": {"partner", "family", "friend", "spouse"},
}


async def write_object_observations_heuristic(db, person_id: str, entry_id: str) -> List[float]:
    record = await db.fetchrow(
        "select content, tags from journal_entries where id=$1",
        entry_id,
    )
    if not record:
        return []

    text = record["content"] or ""
    tags = set(record["tags"] or [])

    confidences: List[float] = []
    for match in GOAL_RE.finditer(text):
        title = match.group("title").strip()
        lowered = title.lower()
        domain = "general"
        for dom, keywords in DOMAIN_MAP.items():
            if any(k in lowered for k in keywords) or dom in tags:
                domain = dom
                break

        object_id = uuid.uuid4()
        payload = {
            "title": title,
            "domain": domain,
            "status": "proposed",
            "polarity": "toward",
        }
        conf = 0.6
        await db.execute(
            """
            insert into observations (person_id, entry_id, object_id, lens, kind, payload, method, confidence)
            values ($1,$2,$3,'object','goal',$4,'heuristic',$5)
            """,
            person_id,
            entry_id,
            object_id,
            payload,
            conf,
        )
        confidences.append(conf)

    return confidences
