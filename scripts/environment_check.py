import asyncio
import os
from typing import Any, Dict

import httpx
from redis import Redis
from rq import Queue


API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
PERSON_ID = os.environ.get("PERSON_ID")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ENV_QUEUE = os.environ.get("ENVIRONMENT_QUEUE", "environment")


async def main() -> None:
    if not PERSON_ID:
        raise SystemExit("PERSON_ID env var required")

    async with httpx.AsyncClient(timeout=40.0) as client:
        print("=" * 80)
        print("STEP 1 → /environment/update")
        payload: Dict[str, Any] = {
            "person_id": PERSON_ID,
            "weather": {"temp_c": 28, "condition": "Cloudy"},
            "calendar_blocks": [{"label": "meetings", "total_minutes": 180}],
            "day_cycle": "afternoon",
            "weekend_flag": False,
            "holiday_flag": False,
            "travel_flag": False,
            "environment_tags": ["cloudy", "indoor"],
        }
        resp = await client.post(f"{API_BASE}/environment/update", json=payload)
        print("/environment/update status:", resp.status_code)
        print(resp.json())

        print("\n" + "=" * 80)
        print("STEP 2 → /environment/get")
        resp = await client.get(f"{API_BASE}/environment/get", params={"person_id": PERSON_ID})
        print("/environment/get status:", resp.status_code)
        print(resp.json())

        print("\n" + "=" * 80)
        print("STEP 3 → enqueue environment_refresh job (RQ)")
        conn = Redis.from_url(REDIS_URL)
        queue = Queue(ENV_QUEUE, connection=conn)
        job = queue.enqueue(
            "sakhi.apps.worker.tasks.environment_refresh.refresh_environment",
            args=(PERSON_ID,),
            kwargs={
                "weather": {"temp_c": 28, "condition": "Cloudy"},
                "calendar_blocks": [{"label": "meetings", "total_minutes": 180}],
                "day_cycle": "afternoon",
                "weekend_flag": False,
                "holiday_flag": False,
                "travel_flag": False,
                "environment_tags": ["cloudy", "indoor", "queued"],
            },
        )
        print(f"Enqueued job id={job.id} queue={ENV_QUEUE}")

        print("\n" + "=" * 80)
        print("If you want to inspect via SQL:")
        print(
            'psql "$DATABASE_URL" -c "select person_id, weather, calendar_blocks, day_cycle, weekend_flag, holiday_flag, travel_flag, environment_tags, updated_at from environment_context where person_id=\'%s\';"'
            % PERSON_ID
        )


if __name__ == "__main__":
    asyncio.run(main())
