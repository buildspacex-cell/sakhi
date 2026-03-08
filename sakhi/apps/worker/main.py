import logging
import os
import sys
from pathlib import Path
from typing import List

# Ensure project root is on sys.path so `sakhi.*` imports resolve
# regardless of how this module is launched (dev script, python -m, etc.)
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from redis import Redis
from rq import Queue, Worker
from dotenv import load_dotenv

from sakhi.apps.api.core.llm import set_router as set_llm_router
from sakhi.apps.api.core.monitoring import report_exception_sync, setup_monitoring
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
        "email_sync": os.getenv("EMAIL_SYNC_QUEUE", "email_sync"),
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


def _worker_exception_handler(job, exc_type, exc_value, tb) -> bool:
    """Report job failures to external monitoring sinks."""

    del exc_type, tb
    error = exc_value if isinstance(exc_value, BaseException) else RuntimeError(str(exc_value))
    report_exception_sync(
        error,
        where=f"worker:job:{job.origin}:{job.func_name}",
        severity="error",
        dedupe_key=f"worker-job:{job.id}:{error.__class__.__name__}",
        extra={"job_id": job.id, "queue": job.origin, "func_name": job.func_name},
    )
    return False


def run() -> None:
    setup_monitoring(service="sakhi-worker", environment=os.getenv("SAKHI_ENVIRONMENT") or os.getenv("ENV"))
    try:
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

        worker = Worker(queues, connection=conn, exception_handlers=[_worker_exception_handler])
        LOGGER.info("Worker started; listening on %s queues.", len(queues))
        worker.work(with_scheduler=False)
    except Exception as exc:
        report_exception_sync(
            exc,
            where="worker:main",
            severity="critical",
            dedupe_key=f"worker-main:{exc.__class__.__name__}:{str(exc)[:120]}",
            extra={"phase": "worker_boot_or_run_loop"},
        )
        LOGGER.exception("Worker crashed")
        raise


if __name__ == "__main__":
    run()
