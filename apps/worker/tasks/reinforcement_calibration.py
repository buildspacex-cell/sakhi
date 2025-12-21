from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert, db_update


async def run_reinforcement_calibration(person_id: str) -> None:
    reflections = db_find("reflections", {"user_id": person_id})[:10]
    feedback_rows = db_find("reflection_feedback", {"person_id": person_id})
    tones = db_find("emotional_tone_shift", {"person_id": person_id})[:10]

    tone_map = {row.get("reflection_id"): row for row in tones}

    for reflection in reflections:
        ref_id = reflection.get("id")
        feedback = next((fb for fb in feedback_rows if fb.get("reflection_id") == ref_id), {})
        relevance = float(feedback.get("relevance_score", 0.5))
        feedback_type = feedback.get("feedback_type", "neutral")
        feedback_factor = 1.0 if feedback_type == "positive" else 0.5 if feedback_type == "neutral" else 0.2
        tone_entry = tone_map.get(ref_id, {})
        sentiment_shift = float(tone_entry.get("after_sentiment", 0.0)) - float(tone_entry.get("before_sentiment", 0.0))

        reward = (relevance * 0.5) + (feedback_factor * 0.3) + (max(sentiment_shift, 0.0) * 0.2)
        db_insert(
            "reflection_scores",
            {
                "person_id": person_id,
                "reflection_id": ref_id,
                "sentiment_shift": sentiment_shift,
                "engagement_delta": 0.5,
                "reward_score": reward,
            },
        )

    rewards = db_find("reflection_scores", {"person_id": person_id})
    avg_reward = (
        sum(float(row.get("reward_score", 0.5)) for row in rewards) / len(rewards)
        if rewards
        else 0.5
    )

    prompt = f"""
You are Sakhi's calibration system.
The average reflection reward is {avg_reward:.2f}.
Adjust the following traits slightly (-0.1 to +0.1 each) to optimize engagement and empathy:
- reflection_depth
- tone_warmth
- conciseness
- adaptability
- confidence
Output JSON of new calibrated weights (0–1 scale).
""".strip()

    response = await call_llm(messages=[{"role": "user", "content": prompt}])
    payload = response.get("message") if isinstance(response, dict) else response
    try:
        traits = json.loads(payload or "{}")
    except json.JSONDecodeError:
        traits = {}

    db_update(
        "calibration_profile",
        {"person_id": person_id},
        {
            "reflection_depth": traits.get("reflection_depth", 0.5),
            "tone_warmth": traits.get("tone_warmth", 0.7),
            "conciseness": traits.get("conciseness", 0.6),
            "adaptability": traits.get("adaptability", 0.5),
            "confidence": traits.get("confidence", 0.7),
            "last_calibrated": "now",
        },
    )


__all__ = ["run_reinforcement_calibration"]
