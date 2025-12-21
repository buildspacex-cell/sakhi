import logging
import os
from typing import List

from redis import Redis
from rq import Queue, Worker
from dotenv import load_dotenv

from sakhi.apps.api.core.llm import set_router as set_llm_router
from sakhi.apps.worker.jobs import _get_router

load_dotenv(".env.worker")
load_dotenv()


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger("sakhi.worker")


def get_redis() -> Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    LOGGER.info("Connecting to Redis at %s", url)
    return Redis.from_url(url)


def _build_queues(connection: Redis) -> List[Queue]:
    queue_env = {
        "embeddings": os.getenv("EMBEDDINGS_QUEUE", "embeddings"),
        "salience": os.getenv("SALIENCE_QUEUE", "salience"),
        "reflection": os.getenv("REFLECTION_QUEUE", "reflection"),
        "presence": os.getenv("PRESENCE_QUEUE", "presence"),
        "rhythm": os.getenv("RHYTHM_QUEUE", "rhythm"),
        "analytics": os.getenv("ANALYTICS_QUEUE", "analytics"),
        "patterns": os.getenv("PATTERNS_QUEUE", "patterns"),
        "learning": os.getenv("LEARNING_QUEUE", "learning"),
        "observe_pipeline": os.getenv("OBSERVE_PIPELINE_QUEUE", "observe"),
        "turn_updates": os.getenv("TURN_JOBS_QUEUE", "turn_updates"),
        "focus": os.getenv("FOCUS_QUEUE", "focus"),
        "environment": os.getenv("ENVIRONMENT_QUEUE", "environment"),
    }

    queues = []
    for label, name in queue_env.items():
        if not name:
            LOGGER.warning("Queue %s has empty name; skipping", label)
            continue
        queue = Queue(name, connection=connection)
        LOGGER.info("Registered queue: %s", queue.name)
        queues.append(queue)
    return queues


def run() -> None:
    conn = get_redis()
    queues = _build_queues(conn)
    if not queues:
        raise RuntimeError("No queues registered; check configuration.")

    try:
        router = _get_router()
        set_llm_router(router)
        LOGGER.info("LLM router initialised for worker context.")
    except Exception as exc:  # pragma: no cover - defensive log
        LOGGER.warning("Failed to initialise LLM router: %s", exc)

    worker = Worker(queues, connection=conn)
    LOGGER.info("Worker started; listening on %s queues.", len(queues))
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    run()
