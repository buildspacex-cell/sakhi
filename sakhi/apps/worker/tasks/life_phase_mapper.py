from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert


async def run_life_phase_mapper(person_id: str) -> None:
    reflections = [
        row
        for row in db_find("reflections", {"user_id": person_id})
        if row.get("created_at")
    ]
    rhythm = [
        row
        for row in db_find("rhythm_insights", {"person_id": person_id})
        if row.get("created_at")
    ]
    themes = [
        row
        for row in db_find("journal_themes", {"user_id": person_id})
        if row.get("created_at")
    ]

    prompt = f"""
You are Sakhi’s longitudinal mapper.
Identify natural life phases from this 90-day data:
REFLECTIONS: {reflections}
RHYTHM: {rhythm}
THEMES: {themes}

Group experiences into distinct phases (1–3 max).
For each phase, output:
- phase_name
- phase_type (growth / recovery / creation / transition)
- start_date / end_date
- dominant_themes
- avg_energy_level (0–1)
- summary (human-readable insight)
Output JSON.
""".strip()

    response = await call_llm(messages=[{"role": "user", "content": prompt}])
    payload = response.get("message") if isinstance(response, dict) else response
    try:
        data = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return

    for phase in data.get("phases", []):
        db_insert(
            "life_phases",
            {
                "person_id": person_id,
                "phase_name": phase.get("phase_name"),
                "phase_type": phase.get("phase_type"),
                "start_date": phase.get("start_date"),
                "end_date": phase.get("end_date"),
                "summary": phase.get("summary"),
                "dominant_themes": phase.get("dominant_themes", []),
                "avg_energy_level": phase.get("avg_energy_level", 0.5),
            },
        )


__all__ = ["run_life_phase_mapper"]
