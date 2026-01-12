from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, List
import json

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.libs.embeddings import compute_direction_vector, to_pgvector
from sakhi.libs.schemas.settings import get_settings

logger = logging.getLogger(__name__)
WINDOW_DAYS = 1500  # TODO: reduce to a tighter window before production deployment
CORE_VALUE_HINTS = {"family", "health", "growth", "consistency"}
SHADOW_HINTS = {"guilt", "overwhelm", "avoidance", "stress"}
LIGHT_HINTS = {"grounding", "optimism", "connection"}


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
    list_to_dict = 0
    dict_native = 0

    def _normalize_friction_item(item: Any) -> Any:
        if isinstance(item, str):
            try:
                return json.loads(item)
            except Exception:
                return item
        return item

    for row in rows:
        raw_soul = row.get("soul") or {}
        if isinstance(raw_soul, str):
            try:
                raw_soul = json.loads(raw_soul)
            except Exception:
                raw_soul = {}
        if isinstance(raw_soul, dict):
            structured = raw_soul
            dict_native += 1
        elif isinstance(raw_soul, list):
            structured = map_flat_soul_to_buckets([str(x) for x in raw_soul if isinstance(x, (str, int, float))])
            list_to_dict += 1
        else:
            structured = {}

        for key in combined.keys():
            for item in structured.get(key, []):
                combined[key].add(item)
        if "confidence" in structured:
            try:
                confidences.append(float(structured["confidence"]))
            except Exception:
                pass
        # Fallback to top-level columns if present.
        shadow = row.get("soul_shadow") or []
        light = row.get("soul_light") or []
        for item in shadow if isinstance(shadow, list) else []:
            combined["shadow_patterns"].add(item)
        for item in light if isinstance(light, list) else []:
            combined["light_patterns"].add(item)

        if row.get("soul_conflict"):
            if isinstance(row["soul_conflict"], list):
                conflicts.extend(row["soul_conflict"])
        if row.get("soul_friction"):
            if isinstance(row["soul_friction"], list):
                frictions.extend(_normalize_friction_item(f) for f in row["soul_friction"])
            else:
                frictions.append(_normalize_friction_item(row["soul_friction"]))
    aggregated = {k: list(v) for k, v in combined.items()}
    aggregated["confidence"] = min(0.9, max(confidences) if confidences else 0.0)
    aggregated["updated_at"] = dt.datetime.utcnow().isoformat()
    aggregated["conflicts"] = conflicts[:10]
    aggregated["friction"] = frictions[:10]
    logger.info(
        "[soul_refresh] normalized episodic soul",
        extra={"list_to_dict": list_to_dict, "dict_native": dict_native},
    )
    return aggregated


async def soul_refresh_worker(person_id: str) -> Dict[str, Any]:
    """
    Aggregates all soul signals from episodic memory.
    Updates personal_model.soul_state and personal_model.soul_vector.
    """
    try:
        settings = get_settings()
        if not settings.enable_identity_workers:
            logger.info("Worker disabled by safety gate: ENABLE_IDENTITY_WORKERS=false")
            return {"person_id": person_id, "updated": False}

        logger.info(
            "[soul_refresh] start",
            extra={"person_id": person_id, "window_days": WINDOW_DAYS},
        )

        rows = await q(
            """
            SELECT
                soul,
                soul_shadow,
                soul_light,
                soul_conflict,
                soul_friction,
                vector_vec AS vector
            FROM memory_episodic
            WHERE person_id = $1
              AND soul IS NOT NULL
              AND ts >= NOW() - ($2::text || ' days')::interval
            """,
            person_id,
            str(WINDOW_DAYS),
        )
        logger.info(
            "[soul_refresh] rows fetched",
            extra={"person_id": person_id, "rows": len(rows or [])},
        )
        if not rows:
            empty_state = {
                "core_values": [],
                "longing": [],
                "aversions": [],
                "identity_themes": [],
                "commitments": [],
                "shadow_patterns": [],
                "light_patterns": [],
                "confidence": 0.0,
                "updated_at": dt.datetime.utcnow().isoformat(),
                "conflicts": [],
                "friction": [],
            }
            await dbexec(
                """
                UPDATE personal_model
                SET soul_state = $2::jsonb,
                    soul_vector = NULL,
                    soul_shadow = $3::jsonb,
                    soul_light = $4::jsonb,
                    soul_conflicts = $5::jsonb,
                    soul_friction = $6::jsonb,
                    updated_at = NOW()
                WHERE person_id = $1
                """,
                person_id,
                json.dumps(empty_state, ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
            )
            logger.info(
                "[soul_refresh] soul_state updated",
                extra={"person_id": person_id, "episodes_considered": 0, "window_days": WINDOW_DAYS},
            )
            return {"person_id": person_id, "updated": True, "episodes_considered": 0}

        aggregated = aggregate_soul_signals(rows)
        logger.info(
            "[soul_refresh] aggregated signals",
            extra={
                "person_id": person_id,
                "aggregated_keys": list(aggregated.keys()),
                "aggregated_counts": {k: len(v) if isinstance(v, list) else 0 for k, v in aggregated.items()},
                "confidence": aggregated.get("confidence"),
            },
        )
        vectors = [r.get("vector") for r in rows if r.get("vector")]
        logger.info(
            "[soul_refresh] vectors collected",
            extra={"person_id": person_id, "vector_count": len(vectors)},
        )
        soul_vector = compute_direction_vector(vectors) if vectors else None
        soul_vector_literal = None
        if soul_vector:
            try:
                soul_vector_literal = to_pgvector(soul_vector, length=len(soul_vector))
            except Exception:
                soul_vector_literal = None

        def _json(val: Any) -> str:
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return "{}"

        await dbexec(
            """
            UPDATE personal_model
            SET soul_state = $2::jsonb,
                soul_vector = CASE
                    WHEN $3::text IS NULL THEN NULL::vector
                    ELSE ($3::text)::vector
                END,
                soul_shadow = $4::jsonb,
                soul_light = $5::jsonb,
                soul_conflicts = $6::jsonb,
                soul_friction = $7::jsonb,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            _json(aggregated),
            soul_vector_literal,
            _json(aggregated.get("shadow_patterns") or []),
            _json(aggregated.get("light_patterns") or []),
            _json(aggregated.get("conflicts") or []),
            _json(aggregated.get("friction") or []),
        )

        logger.info(
            "[soul_refresh] soul_state updated",
            extra={"person_id": person_id, "episodes_considered": len(rows), "window_days": WINDOW_DAYS},
        )

        return {"person_id": person_id, "updated": True, "episodes_considered": len(rows)}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "[soul_refresh] error",
            extra={"person_id": person_id, "error": str(exc)},
            exc_info=True,
        )
        return {"person_id": person_id, "updated": False, "error": str(exc)}


def map_flat_soul_to_buckets(items: List[str]) -> Dict[str, List[str]]:
    buckets = {
        "core_values": [],
        "identity_themes": [],
        "light_patterns": [],
        "shadow_patterns": [],
        "longing": [],
        "aversions": [],
    }
    for item in items:
        token = str(item).strip().lower()
        if not token:
            continue
        if token in CORE_VALUE_HINTS:
            buckets["core_values"].append(item)
        elif token in SHADOW_HINTS:
            buckets["shadow_patterns"].append(item)
        elif token in LIGHT_HINTS:
            buckets["light_patterns"].append(item)
        else:
            buckets["identity_themes"].append(item)
    return buckets


__all__ = ["soul_refresh_worker", "aggregate_soul_signals"]
