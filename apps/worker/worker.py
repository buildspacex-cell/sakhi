from __future__ import annotations

import asyncio
import json
import os
import uuid

from redis import asyncio as aioredis
import asyncpg

from apps.worker.enrich.tags_enricher import handle_tags
from apps.worker.enrich.intent_goal_enricher import handle_intents_goals
from apps.worker.enrich.values_guardrail_enricher import handle_values
from apps.worker.enrich.aspect_writers import handle_aspects
from apps.worker.enrich.short_horizon_aggregator import update_short_horizon
from apps.worker.enrich.observations_self import write_self_observations_heuristic
from apps.worker.enrich.observations_object import write_object_observations_heuristic
from apps.worker.enrich.anchor_observations import write_anchor_observations
from apps.worker.enrich.llm_extract import run_extraction_llm
from apps.worker.enrich.state_vector import compute_state_vector
from sakhi.apps.api.core.llm import set_router as set_llm_router
from sakhi.apps.api.core.llm_schemas import ExtractionOutput
from sakhi.apps.worker.jobs import _get_router


async def _db_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(os.environ["DATABASE_URL"])


async def publish_event(redis, topic: str, payload: dict) -> None:
    await redis.lpush(f"queue:{topic}", json.dumps(payload, default=str))


async def _write_llm_observations(
    db: asyncpg.Connection,
    person_id: str,
    entry_id: str,
    extraction: ExtractionOutput,
) -> tuple[dict, list[float]]:
    counts = {"self_llm": 0, "object_llm": 0}
    confidences: list[float] = []

    for obs in extraction.self:
        payload = {
            key: value
            for key, value in {
                "score": obs.score,
                "labels": obs.labels or None,
                "notes": obs.notes or None,
            }.items()
            if value is not None
        }
        await db.execute(
            """
            insert into observations (person_id, entry_id, lens, kind, payload, method, confidence)
            values ($1,$2,'self',$3,$4,'llm',$5)
            """,
            person_id,
            entry_id,
            obs.kind,
            payload,
            float(obs.confidence),
        )
        counts["self_llm"] += 1
        confidences.append(float(obs.confidence))

    for obj in extraction.objects:
        object_id = obj.object_id or str(uuid.uuid4())
        payload = {
            key: value
            for key, value in {
                "type": obj.type,
                "domain": obj.domain,
                "status": obj.status,
                "actors": obj.actors or None,
                "timescale": obj.timescale,
                "polarity": obj.polarity,
                "needs": obj.needs or None,
                "values": obj.values or None,
                "signature": obj.signature,
                "notes": obj.notes or None,
            }.items()
            if value is not None
        }
        await db.execute(
            """
            insert into observations (person_id, entry_id, object_id, lens, kind, payload, method, confidence)
            values ($1,$2,$3,'object',$4,$5,'llm',$6)
            """,
            person_id,
            entry_id,
            object_id,
            obj.type,
            payload,
            float(obj.confidence),
        )
        counts["object_llm"] += 1
        confidences.append(float(obj.confidence))

    return counts, confidences


async def main() -> None:
    pool = await _db_pool()
    redis = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    queues = ["queue:journal.entry.created"]
    router = _get_router()
    set_llm_router(router)

    while True:
        item = await redis.brpop(queues, timeout=10)
        if not item:
            await asyncio.sleep(0.05)
            continue
        _, raw = item
        evt = json.loads(raw)
        pid = evt.get("person_id")
        eid = evt.get("entry_id")
        if not pid or not eid:
            continue

        async with pool.acquire() as db:
            entry_row = await db.fetchrow(
                "select content, tags, layer, created_at from journal_entries where id=$1",
                eid,
            )
            if not entry_row:
                continue

            await handle_tags(db, pid, eid)
            await handle_intents_goals(db, pid, eid)
            await handle_values(db, pid, eid)
            await handle_aspects(db, pid, eid)
            await update_short_horizon(db, pid)

            confidences: list[float] = []
            counts = {
                "self_llm": 0,
                "self_fallback": 0,
                "object_llm": 0,
                "object_fallback": 0,
                "self": 0,
                "object": 0,
                "anchor": 0,
            }

            text = entry_row["content"] or ""
            tags = entry_row["tags"] or []
            layer = entry_row["layer"]

            extraction, extraction_error = await run_extraction_llm(text, tags=tags, layer=layer)
            if extraction and (extraction.self or extraction.objects):
                llm_counts, llm_conf = await _write_llm_observations(db, pid, eid, extraction)
                for key, value in llm_counts.items():
                    counts[key] = counts.get(key, 0) + value
                counts["self"] += llm_counts.get("self_llm", 0)
                counts["object"] += llm_counts.get("object_llm", 0)
                confidences.extend(llm_conf)
            else:
                extraction_error = extraction_error or "no_llm_output"

            if counts["self_llm"] == 0:
                heur_self = await write_self_observations_heuristic(db, pid, eid)
                counts["self_fallback"] = len(heur_self)
                counts["self"] += len(heur_self)
                confidences.extend(heur_self)

            if counts["object_llm"] == 0:
                heur_obj = await write_object_observations_heuristic(db, pid, eid)
                counts["object_fallback"] = len(heur_obj)
                counts["object"] += len(heur_obj)
                confidences.extend(heur_obj)

            anchor_conf = await write_anchor_observations(db, pid, eid)
            counts["anchor"] = len(anchor_conf)
            confidences.extend(anchor_conf)

            avg_conf = sum(confidences) / len(confidences) if confidences else None

            await publish_event(
                redis,
                "observations.extracted",
                {
                    "person_id": pid,
                    "entry_id": eid,
                    "counts": counts,
                    "avg_confidence": avg_conf,
                    "llm_error": extraction_error,
                },
            )

            obs_rows = await db.fetch(
                """
                select lens, kind, payload, confidence, method
                from observations where entry_id=$1 and person_id=$2
                """,
                eid,
                pid,
            )
            obs_payload = []
            for row in obs_rows:
                payload = {
                    "lens": row["lens"],
                    "kind": row["kind"],
                    "payload": row["payload"],
                    "confidence": row["confidence"],
                    "method": row["method"],
                }
                obs_payload.append(payload)

            state_vector, state_error, state_method = await compute_state_vector(obs_payload, text)
            if state_vector:
                await db.execute(
                    """
                    insert into observations (person_id, entry_id, lens, kind, payload, method, confidence)
                    values ($1,$2,'anchor','state_vector',$3,$4,$5)
                    """,
                    pid,
                    eid,
                    state_vector.dict(),
                    state_method,
                    float(state_vector.confidence),
                )
                await publish_event(
                    redis,
                    "state_vector.updated",
                    {
                        "person_id": pid,
                        "entry_id": eid,
                        "confidence": float(state_vector.confidence),
                        "method": state_method,
                    },
                )
            else:
                await publish_event(
                    redis,
                    "state_vector.updated",
                    {
                        "person_id": pid,
                        "entry_id": eid,
                        "error": state_error,
                        "method": state_method,
                    },
                )


if __name__ == "__main__":
    asyncio.run(main())
