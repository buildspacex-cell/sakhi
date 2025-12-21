from __future__ import annotations

import os
from functools import lru_cache

import yaml


@lru_cache(maxsize=1)
def policy() -> dict:
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "policy",
        "conversation.yaml",
    )
    with open(os.path.abspath(path), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
