from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.libs.embeddings import compute_direction_vector
from sakhi.libs.schemas.settings import get_settings

logger = logging.getLogger(__name__)


def aggregate_soul_signals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined: Dict[str, set] = {
        "core_values": set(),
        "longing": set(),
        "aversions": set(),
        "identity_themes": set(),
        "commitments": set(),
        "shadow_patterns": set(),
        "light_patterns": set(),
    }
    conflicts: List[Any] = []
    frictions: List[Any] = []
    confidences: List[float] = []
    for row in rows:
        soul = row.get("soul") or {}
        if not isinstance(soul, dict):
            continue
        for key in combined.keys():
            for item in soul.get(key, []):
                combined[key].add(item)
        if "confidence" in soul:
            try:
                confidences.append(float(soul["confidence"]))
            except Exception:
                pass
        if row.get("soul_conflict"):
            if isinstance(row["soul_conflict"], list):
                conflicts.extend(row["soul_conflict"])
        if row.get("soul_friction"):
            frictions.extend(row["soul_friction"]) if isinstance(row["soul_friction"], list) else frictions.append(
                row["soul_friction"]
            )
    aggregated = {k: list(v) for k, v in combined.items()}
    aggregated["confidence"] = min(0.9, max(confidences) if confidences else 0.0)
    aggregated["updated_at"] = dt.datetime.utcnow().isoformat()
    aggregated["conflicts"] = conflicts[:10]
    aggregated["friction"] = frictions[:10]
    return aggregated


async def soul_refresh_worker(person_id: str) -> Dict[str, Any]:
    """
    Aggregates all soul signals from episodic memory.
    Updates personal_model.soul_state and personal_model.soul_vector.
    """
    settings = get_settings()
    if not settings.enable_identity_workers:
        logger.info("Worker disabled by safety gate: ENABLE_IDENTITY_WORKERS=false")
        return {"person_id": person_id, "updated": False}

    rows = await q(
        """
        SELECT soul, vector_vec AS vector
        FROM memory_episodic
        WHERE person_id = $1 AND soul IS NOT NULL
        """,
        person_id,
    )
    if not rows:
        return {"person_id": person_id, "updated": False}

    aggregated = aggregate_soul_signals(rows)
    vectors = [r.get("vector") for r in rows if r.get("vector")]
    soul_vector = compute_direction_vector(vectors) if vectors else None

    await dbexec(
        """
        UPDATE personal_model
        SET soul_state = $2,
            soul_vector = $3,
            soul_shadow = $4,
            soul_light = $5,
            soul_conflicts = $6,
            soul_friction = $7,
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        aggregated,
        soul_vector,
        aggregated.get("shadow_patterns") or [],
        aggregated.get("light_patterns") or [],
        aggregated.get("conflicts") or [],
        aggregated.get("friction") or [],
    )

    return {"person_id": person_id, "updated": True}


__all__ = ["soul_refresh_worker", "aggregate_soul_signals"]
