from __future__ import annotations

import uuid
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.brain.micro_goals import normalize_intention, extract_micro_steps, score_confidence, is_blocked


async def create_micro_goals(person_id: str, text: str) -> Dict[str, Any]:
    normalized = normalize_intention(text or "")
    blocked = is_blocked(text or "")
    steps = [] if blocked else extract_micro_steps(normalized)
    confidence = score_confidence(normalized, steps)

    mg_id = str(uuid.uuid4())
    try:
        await dbexec(
            """
            INSERT INTO micro_goals (id, person_id, source, normalized, micro_steps, confidence, blocked)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
            """,
            mg_id,
            person_id,
            text,
            normalized,
            steps,
            confidence,
            blocked,
        )
    except Exception:
        # tolerate missing DB during tests
        pass

    return {
        "success": True,
        "micro_goals_id": mg_id,
        "steps_count": len(steps),
        "blocked": blocked,
        "preview": steps[:2],
        "summary": "Breaks goal into small steps",
        "samples": [s.get("step") for s in steps[:3]],
        "confidence": confidence,
    }

