from __future__ import annotations

from typing import List


async def write_anchor_observations(db, person_id: str, entry_id: str) -> List[float]:
    rows = await db.fetch(
        "select aspect, feature_key, value from aspect_features where person_id=$1",
        person_id,
    )
    if not rows:
        return []

    anchors = {"time": None, "energy": None, "finance": None, "values": None}
    for row in rows:
        aspect = row["aspect"]
        if aspect in anchors:
            try:
                score = row["value"].get("score")
            except Exception:
                score = None
            anchors[aspect] = score

    confidences = []
    confidence_map = {}
    for key, value in anchors.items():
        confidence_map[key] = 0.8 if value is not None else 0.3
        confidences.append(confidence_map[key])

    overall = sum(confidences) / len(confidences) if confidences else 0.0

    await db.execute(
        """
        insert into observations (person_id, entry_id, lens, kind, payload, method, confidence)
        values ($1,$2,'anchor','readiness',$3,'heuristic',$4)
        """,
        person_id,
        entry_id,
        {"anchors": anchors, "confidence": confidence_map},
        overall,
    )

    return confidences
