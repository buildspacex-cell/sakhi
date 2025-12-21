import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone

from redis import asyncio as aioredis
import asyncpg
from sakhi.apps.api.core.metrics import aw_events_written, derivatives_written, ingest_latency

REDIS_URL = os.environ["REDIS_URL"]
DATABASE_URL = os.environ["DATABASE_URL"]

GOAL_RE = re.compile(r"\b(i (want|plan|need|aim) to)\s+(?P<title>[^.!?\n]{3,120})", re.IGNORECASE)


async def pool() -> asyncpg.pool.Pool:
    return await asyncpg.create_pool(DATABASE_URL)


def _parse_event_ts(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
            result = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    return None


async def handle_aw_event(db: asyncpg.Connection, event: dict[str, object]) -> None:
    if event.get("modality") != "text" or event.get("payload_redacted"):
        return

    payload = event.get("payload") or {}
    if not isinstance(payload, dict):
        return

    person_id = event.get("person_id")
    event_id = event.get("id")
    if not isinstance(person_id, str) or not isinstance(event_id, str):
        return

    text = payload.get("text") if isinstance(payload.get("text"), str) else ""

    intents: list[dict[str, object]] = []
    match = GOAL_RE.search(text)
    if match:
        intents.append(
            {
                "label": "goal_statement",
                "confidence": 0.9,
                "title": match.group("title").strip(),
            }
        )

    open_loops: list[dict[str, object]] = []
    lowered = text.lower()
    if "finish" in lowered or "complete" in lowered:
        open_loops.append({"desc": "unspecified_task", "urgency": 0.5})

    mental_id = f"mi_{uuid.uuid4().hex}"
    await db.execute(
        """
        INSERT INTO mental_impression (
            id, person_id, source_event_ids, intents, beliefs, open_loops
        ) VALUES ($1, $2, $3, $4::jsonb, '[]'::jsonb, $5::jsonb)
        """,
        mental_id,
        person_id,
        [event_id],
        json.dumps(intents, ensure_ascii=False),
        json.dumps(open_loops, ensure_ascii=False),
    )
    derivatives_written.inc()
    await db.execute(
        "INSERT INTO aw_edge(src_id, dst_id, kind) VALUES ($1, $2, 'derives') ON CONFLICT DO NOTHING",
        event_id,
        mental_id,
    )

    affect = {"valence": 0.1 if "anxious" in lowered else 0.2, "arousal": 0.5, "certainty": 0.6}
    emotional_id = f"es_{uuid.uuid4().hex}"
    await db.execute(
        """
        INSERT INTO emotional_signature (
            id, person_id, from_mental_ids, affect, primary_emotions, needs
        ) VALUES ($1, $2, $3, $4::jsonb, $5, $6)
        """,
        emotional_id,
        person_id,
        [mental_id],
        json.dumps(affect, ensure_ascii=False),
        ["hopeful"] if intents else [],
        ["progress"],
    )
    derivatives_written.inc()
    await db.execute(
        "INSERT INTO aw_edge(src_id, dst_id, kind) VALUES ($1, $2, 'derives') ON CONFLICT DO NOTHING",
        mental_id,
        emotional_id,
    )

    if "calm" in lowered:
        quality = "grounded"
    elif "overwhelm" in lowered:
        quality = "scattered"
    else:
        quality = "expansive"

    energetic_id = f"en_{uuid.uuid4().hex}"
    await db.execute(
        """
        INSERT INTO energetic_state (
            id, person_id, from_emotional_ids, quality, rhythm_tags, stability
        ) VALUES ($1, $2, $3, $4, $5, $6)
        """,
        energetic_id,
        person_id,
        [emotional_id],
        quality,
        [],
        0.6,
    )
    derivatives_written.inc()
    await db.execute(
        "INSERT INTO aw_edge(src_id, dst_id, kind) VALUES ($1, $2, 'derives') ON CONFLICT DO NOTHING",
        emotional_id,
        energetic_id,
    )

    message = "Block 45 minutes for the most important step toward your stated goal."
    insight_id = f"ins_{uuid.uuid4().hex}"
    await db.execute(
        """
        INSERT INTO insight (
            id, person_id, from_ids, kind, message, why, actions, confidence
        ) VALUES ($1, $2, $3, 'nudge', $4, $5::jsonb, $6::jsonb, $7)
        """,
        insight_id,
        person_id,
        [mental_id, emotional_id, energetic_id],
        message,
        json.dumps({"features": ["goal_statement", "energy_ok"], "confidence": 0.65}, ensure_ascii=False),
        json.dumps([{"type": "schedule_block", "params": {"minutes": 45}}], ensure_ascii=False),
        0.65,
    )
    derivatives_written.inc()

    insight_event_id = f"evt_{uuid.uuid4().hex}"
    await db.execute(
        """
        INSERT INTO aw_event (
            id, actor, modality, person_id, payload, context_json, schema_version, hash
        ) VALUES ($1, 'sakhi', 'thought', $2, $3::jsonb, $4::jsonb, 'aw_1', $5)
        """,
        insight_event_id,
        person_id,
        json.dumps({"insight_id": insight_id, "message": message}, ensure_ascii=False),
        json.dumps({"tz": "Asia/Kolkata", "device": "server", "privacy_flags": ["no_xfer"]}, ensure_ascii=False),
        f"insight:{insight_id}",
    )
    aw_events_written.inc()
    await db.execute(
        "INSERT INTO aw_edge(src_id, dst_id, kind) VALUES ($1, $2, 'reflects') ON CONFLICT DO NOTHING",
        insight_id,
        insight_event_id,
    )

    event_ts = _parse_event_ts(event.get("ts"))
    if event_ts is not None:
        ingest_latency.observe(max(0.0, (datetime.now(timezone.utc) - event_ts).total_seconds()))


async def main() -> None:
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    pool_obj = await pool()
    try:
        while True:
            item = await redis.brpop(["queue:aw.events"], timeout=10)
            if not item:
                await asyncio.sleep(0.05)
                continue
            _, raw = item
            event = json.loads(raw)
            async with pool_obj.acquire() as connection:
                await handle_aw_event(connection, event)
    finally:
        await pool_obj.close()


if __name__ == "__main__":
    asyncio.run(main())
