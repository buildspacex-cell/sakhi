from __future__ import annotations

import importlib.util
import pathlib
import sys


def _load_legacy_jobs_module():
    """
    Load the original `sakhi.apps.worker.jobs` module (the sibling jobs.py file)
    so imports like `from sakhi.apps.worker.jobs import enqueue_embedding_and_salience`
    continue to work even though this directory now exists for helpers.
    """

    module_name = "sakhi.apps.worker._jobs_impl"
    if module_name in sys.modules:
        return sys.modules[module_name]

    jobs_py = pathlib.Path(__file__).resolve().parent.parent / "jobs.py"
    spec = importlib.util.spec_from_file_location(module_name, jobs_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load worker jobs module from {jobs_py}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_LEGACY = _load_legacy_jobs_module()

# Re-export everything (except dunders) from the legacy module
for _name in dir(_LEGACY):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_LEGACY, _name)


# --- Missing vector literal helper ---
def _to_vector_literal(vec):
    """
    Convert a Python list of floats into a Postgres vector literal
    formatted as: '[1.0, 2.0, 3.0]'.

    Handles:
    - None → returns NULL
    - Already a valid string → returns as-is
    - List/tuple → converts properly
    """

    if vec is None:
        return None

    if isinstance(vec, str):
        # assume it's already a formatted vector literal
        return vec

    if isinstance(vec, (list, tuple)):
        return "[" + ", ".join(f"{float(x):.6f}" for x in vec) + "]"

    raise TypeError(f"Unsupported vector type for literal conversion: {type(vec)}")


__all__ = [name for name in globals().keys() if not name.startswith("_")]
