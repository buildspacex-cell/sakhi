from __future__ import annotations

from typing import Dict, List

from sakhi.apps.worker.utils.db import db_find, db_upsert


async def update_prompt_profile(person_id: str) -> None:
    feedback: List[Dict[str, object]] = db_find("reflection_feedback", {"person_id": person_id})
    if not feedback:
        return

    tone = {"warm": 0.5, "direct": 0.5}
    for entry in feedback:
        comment = str(entry.get("comment") or "").lower()
        if "too blunt" in comment:
            tone["warm"] += 0.1
            tone["direct"] -= 0.1
        if "too soft" in comment:
            tone["direct"] += 0.1
            tone["warm"] -= 0.1

    # Clamp values between 0 and 1
    tone["warm"] = max(0.0, min(1.0, tone["warm"]))
    tone["direct"] = max(0.0, min(1.0, tone["direct"]))

    db_upsert(
        "prompt_profiles",
        {
            "person_id": person_id,
            "tone_weights": tone,
        },
    )


__all__ = ["update_prompt_profile"]
