"""Worker package exports so RQ can import job callables easily."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so `sakhi.*` imports resolve
# MUST happen before importing jobs (which loads jobs.py via importlib)
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# NOTE: Deliberately NOT importing jobs/tasks here at module load time.
# jobs.py imports sakhi.apps.worker.tasks.memory_synthesis, which would
# trigger this __init__.py, causing a circular import where sakhi.apps.worker.jobs
# gets registered in sys.modules before it's fully initialized.
# RQ can still import job callables directly via sakhi.apps.worker.jobs.func_name.

__all__ = ["jobs", "tasks"]


def __getattr__(name: str):
    """Lazy import for jobs and tasks to avoid circular import."""
    if name == "jobs":
        from . import jobs as _jobs
        return _jobs
    if name == "tasks":
        from . import tasks as _tasks
        return _tasks
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
