from __future__ import annotations

import logging

from .recall_scoring import *  # noqa: F401,F403

logging.warning(
    "[DEPRECATED] sakhi.apps.api.core.recall imported — use recall_scoring instead.",
)
