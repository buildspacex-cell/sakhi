from __future__ import annotations

import math
import re
from typing import Dict, List

from sakhi.libs.embeddings import embed_text

MARKERS = re.compile(r"\b(btw|by the way|unrelated|separate|also,|another thing)\b", re.IGNORECASE)


def _cos(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 1.0
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 1.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


async def topic_shift_score(user_text: str, summary: str, last_user_texts: List[str]) -> Dict[str, float]:
    embeddings = []
    e_now = await embed_text(user_text)
    if summary:
        embeddings.append(_cos(e_now, await embed_text(summary[:600])))
    for turn_text in last_user_texts[-3:]:
        embeddings.append(_cos(e_now, await embed_text(turn_text)))

    sem_sim = sum(embeddings) / len(embeddings) if embeddings else 1.0
    marker_bonus = 0.15 if MARKERS.search(user_text) else 0.0
    shift = max(0.0, min(1.0, (1.0 - sem_sim) + marker_bonus))
    return {"semantic_sim": sem_sim, "shift": shift}
