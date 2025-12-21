from __future__ import annotations

import math
from typing import List

SENTIMENT_POSITIVE = {"great", "good", "confident", "relieved", "calm", "hopeful", "excited"}
SENTIMENT_NEGATIVE = {"worried", "anxious", "tired", "sad", "upset", "angry", "stressed"}
STRESS_WORDS = {"stressed", "overwhelmed", "pressure", "tense", "racing"}
ENERGY_LOW = {"tired", "drained", "exhausted", "sleepy", "heavy"}
ENERGY_HIGH = {"energized", "alert", "rested", "light"}


async def write_self_observations_heuristic(db, person_id: str, entry_id: str) -> List[float]:
    record = await db.fetchrow(
        "select content, mood_score, source_ref from journal_entries where id=$1",
        entry_id,
    )
    if not record:
        return []

    text = (record["content"] or "").lower()
    mood_score = record["mood_score"]
    triage = record.get("source_ref") or {}
    if isinstance(triage, str):
        try:
            import json

            triage = json.loads(triage)
        except Exception:
            triage = {}

    confidences: List[float] = []

    pos_hits = sum(1 for word in SENTIMENT_POSITIVE if word in text)
    neg_hits = sum(1 for word in SENTIMENT_NEGATIVE if word in text)
    total = pos_hits + neg_hits
    valence = None
    if total:
        valence = (pos_hits - neg_hits) / total
    elif mood_score is not None:
        valence = float(mood_score)

    if valence is not None:
        conf = 0.6 if total else 0.4
        await db.execute(
            """
            insert into observations (person_id, entry_id, lens, kind, payload, method, confidence)
            values ($1,$2,'self','valence',$3,'heuristic',$4)
            """,
            person_id,
            entry_id,
            {"valence": max(-1.0, min(1.0, float(valence)))},
            conf,
        )
        confidences.append(conf)

    stress_flag = any(word in text for word in STRESS_WORDS)
    stress_score = 0.7 if stress_flag else 0.3
    conf_stress = 0.5 if stress_flag else 0.3
    await db.execute(
        """
        insert into observations (person_id, entry_id, lens, kind, payload, method, confidence)
        values ($1,$2,'self','stress',$3,'heuristic',$4)
        """,
        person_id,
        entry_id,
        {"stress": stress_score},
        conf_stress,
    )
    confidences.append(conf_stress)

    energy = None
    if any(word in text for word in ENERGY_LOW):
        energy = 0.3
    elif any(word in text for word in ENERGY_HIGH):
        energy = 0.7
    elif mood_score is not None:
        energy = 0.5 + 0.4 * float(mood_score)

    if energy is not None:
        conf_energy = 0.4
        await db.execute(
            """
            insert into observations (person_id, entry_id, lens, kind, payload, method, confidence)
            values ($1,$2,'self','energy',$3,'heuristic',$4)
            """,
            person_id,
            entry_id,
            {"energy": max(0.0, min(1.0, float(energy)))},
            conf_energy,
        )
        confidences.append(conf_energy)

    return confidences
