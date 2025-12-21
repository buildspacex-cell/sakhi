from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Callable

from sakhi.apps.worker.scheduler import (
    schedule_presence_jobs,
    schedule_reflection_jobs,
)

LOGGER = logging.getLogger("sakhi.scheduler")
logging.basicConfig(
    level=os.getenv("SCHEDULER_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def _parse_interval(name: str, default_seconds: int) -> int:
    value = os.getenv(name)
    if not value:
        return default_seconds
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except ValueError:
        LOGGER.warning("Invalid interval %s=%s, using default %s", name, value, default_seconds)
    return default_seconds


def _bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _run_with_logging(label: str, func: Callable[[], None]) -> None:
    LOGGER.info("Enqueueing %s jobs", label)
    try:
        func()
    except Exception:  # pragma: no cover - defensive logging
        LOGGER.exception("Scheduler failed running %s jobs", label)
        raise
    else:
        LOGGER.info("Finished enqueuing %s jobs", label)


def _run_once(enable_presence: bool) -> None:
    _run_with_logging("reflection", schedule_reflection_jobs)
    if enable_presence:
        _run_with_logging("presence", schedule_presence_jobs)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Background scheduler loop for Sakhi jobs.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the schedulers a single time and exit.",
    )
    args = parser.parse_args(argv)

    enable_presence = _bool_env("ENABLE_PRESENCE_JOBS", default=True)

    if args.once:
        _run_once(enable_presence)
        return

    reflection_interval = _parse_interval("SCHED_REFLECTION_INTERVAL_SEC", 24 * 60 * 60)
    presence_interval = _parse_interval("SCHED_PRESENCE_INTERVAL_SEC", 6 * 60 * 60)

    next_reflection = time.time()
    next_presence = time.time()

    LOGGER.info(
        "Scheduler loop started reflection_interval=%ss presence_interval=%ss presence_enabled=%s",
        reflection_interval,
        presence_interval,
        enable_presence,
    )

    while True:
        now = time.time()
        ran = False

        if now >= next_reflection:
            _run_with_logging("reflection", schedule_reflection_jobs)
            next_reflection = now + reflection_interval
            ran = True

        if enable_presence and now >= next_presence:
            _run_with_logging("presence", schedule_presence_jobs)
            next_presence = now + presence_interval
            ran = True

        if not ran:
            sleep_for = min(next_reflection, next_presence if enable_presence else next_reflection) - now
            sleep_for = max(sleep_for, 1.0)
            time.sleep(sleep_for)
        else:
            LOGGER.debug(
                "Next runs reflection=%s presence=%s",
                datetime.fromtimestamp(next_reflection, tz=timezone.utc).isoformat(),
                datetime.fromtimestamp(next_presence, tz=timezone.utc).isoformat()
                if enable_presence
                else "disabled",
            )


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.info("Scheduler loop interrupted; shutting down.")
        sys.exit(0)
