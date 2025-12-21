from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import logging

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]

from sakhi.apps.worker.utils.db import db_find, db_insert
from sakhi.libs.rhythm.engine import detect_circadian_pattern, detect_infradian_cycle

LOGGER = logging.getLogger(__name__)


def run_rhythm_inference(person_id: str) -> None:
    """Analyze stored rhythm samples and persist insights."""
    if pd is None:
        LOGGER.warning("pandas not installed; skipping run_rhythm_inference")
        return
    samples: List[Dict[str, Any]] = db_find("rhythm_samples", {"person_id": person_id})
    if not samples:
        return

    df = pd.DataFrame(samples)
    insights: List[Dict[str, Any]] = []

    if "phase" in df.columns and "energy_level" in df.columns:
        try:
            circadian = detect_circadian_pattern(df)
            if circadian:
                insights.append(circadian)
        except Exception:
            pass

    infradian = detect_infradian_cycle(df)
    if infradian:
        insights.append(infradian)

    for insight in insights:
        payload = dict(insight)
        payload["person_id"] = person_id
        payload["created_at"] = datetime.now(timezone.utc).isoformat()
        db_insert("rhythm_insights", payload)


__all__ = ["run_rhythm_inference"]
