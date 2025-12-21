from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Dict, Any, List, Tuple

from sakhi.apps.api.core.db import q

PLANNING_TOKENS = ["plan", "schedule", "organize", "figure out", "decide", "goal"]
CONFUSION_TOKENS = ["confused", "stuck", "not sure", "unclear", "overwhelmed"]
REFLECTION_TOKENS = ["reflect", "thinking about", "considering"]
INTENT_TOKENS = ["help me plan", "need to figure", "need clarity", "confused", "stuck", "urgent", "must"]
UNRESOLVED_TYPES = {"task", "plan_needed", "decision_needed", "info_needed"}
TOPIC_CLUSTERS = {
    "guitar practice": ["guitar", "music"],
    "health": ["health", "workout", "exercise", "sleep"],
    "work": ["work", "office", "meeting", "project"],
    "relationships": ["friend", "partner", "relationship"],
    "finance": ["budget", "money", "finance"],
    "planning": ["plan", "schedule", "week", "today", "tomorrow"],
}
URGENCY_TOKENS = ["need", "must", "urgent", "figure out", "today", "this week", "by tomorrow"]


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def _category(text: str, triage_type: str | None) -> str | None:
    if any(token in text for token in PLANNING_TOKENS):
        return "planning"
    if any(token in text for token in CONFUSION_TOKENS):
        return "confusion"
    if triage_type == "reflection_observation" or any(token in text for token in REFLECTION_TOKENS):
        return "exploration"
    return None


def _topic_hits(text: str) -> List[str]:
    hits = []
    for topic, keywords in TOPIC_CLUSTERS.items():
        if any(keyword in text for keyword in keywords):
            hits.append(topic)
    return hits


def _compute_topic_switch_rate(topic_sequence: List[str]) -> float:
    if len(topic_sequence) <= 1:
        return 0.0
    switches = 0
    for prev, curr in zip(topic_sequence, topic_sequence[1:]):
        if prev != curr:
            switches += 1
    return switches / max(1, len(topic_sequence) - 1)


def _intent_density(intents: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return min(1.0, intents / total)


def _unresolved_weight(unresolved: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return min(1.0, unresolved / total)


def _negative_markers_count(texts: List[str]) -> int:
    markers = ["confused", "stuck", "uncertain", "overwhelm", "lost"]
    count = 0
    for t in texts:
        if any(m in t for m in markers):
            count += 1
    return count


def _weighted_load(intent_density: float, topic_switch: float, negative: float, unresolved: float) -> float:
    score = (
        intent_density * 0.35
        + topic_switch * 0.25
        + negative * 0.20
        + unresolved * 0.20
    )
    return min(1.0, max(0.0, score))


def _priority_state(texts: List[str]) -> Tuple[str | None, List[str]]:
    counter = Counter()
    for text in texts:
        hits = _topic_hits(text)
        if not hits:
            continue
        urgency_boost = 2 if any(token in text for token in URGENCY_TOKENS) else 1
        for topic in hits:
            counter[topic] += urgency_boost
    if not counter:
        return None, []
    top_topic, _ = counter.most_common(1)[0]
    ranked = [item for item, _ in counter.most_common(3)]
    return top_topic, ranked


async def compute(person_id: str, days: int = 30) -> Dict[str, Any]:
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
    rows = await q(
        """
        SELECT triage, text, updated_at
        FROM memory_short_term
        WHERE person_id = $1 AND updated_at >= $2
        ORDER BY updated_at DESC
        LIMIT 200
        """,
        person_id,
        cutoff,
    )

    topics_sequence: List[str] = []
    normalized_texts: List[str] = []
    intents = 0
    unresolved = 0
    negative_markers = 0

    for row in rows:
        triage = row.get("triage") or {}
        if isinstance(triage, str):
            triage = {}
        triage_type = triage.get("type")
        text = _normalize_text(row.get("text") or "")
        if not text:
            continue
        normalized_texts.append(text)

        if any(token in text for token in INTENT_TOKENS):
            intents += 1
        if triage_type in UNRESOLVED_TYPES:
            unresolved += 1

        topic_hit = _topic_hits(text)
        if topic_hit:
            topics_sequence.append(topic_hit[0])

    topic_switch_rate = _compute_topic_switch_rate(topics_sequence)
    negative_markers = _negative_markers_count(normalized_texts)
    total = max(1, len(normalized_texts))

    intent_density_val = _intent_density(intents, total)
    negative_rate = min(1.0, negative_markers / total)
    unresolved_weight_val = _unresolved_weight(unresolved, total)

    load_score = _weighted_load(intent_density_val, topic_switch_rate, negative_rate, unresolved_weight_val)

    priority, priority_topics = _priority_state(normalized_texts)

    if load_score > 0.7:
        base_summary = "mentally overloaded; juggling multiple themes"
    elif load_score >= 0.4:
        base_summary = "managing several things; moderate load"
    else:
        base_summary = "mind relatively clear; focused"

    if priority:
        base_summary = f"{base_summary}. Current top concern: {priority}."

    confidence = min(1.0, 0.4 + 0.05 * len(normalized_texts))

    return {
        "summary": base_summary,
        "confidence": float(confidence),
        "metrics": {
            "cognitive_load": float(load_score),
            "top_priority": priority,
            "priority_topics": priority_topics,
        },
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["compute"]
