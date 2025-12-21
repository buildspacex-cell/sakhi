from __future__ import annotations

import itertools
import json
import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q

LOGGER = logging.getLogger(__name__)

VALUE_KEYWORDS = {
    "growth": {"grow", "learn", "curious", "improve"},
    "connection": {"family", "friend", "community", "support"},
    "creativity": {"create", "art", "music", "write"},
    "impact": {"help", "impact", "serve", "volunteer"},
    "stability": {"security", "safe", "stable", "calm"},
}

IDENTITY_PATTERNS = {
    "Builder": {"build", "project", "ship"},
    "Caregiver": {"care", "support", "nurture"},
    "Explorer": {"travel", "explore", "discover"},
}

PURPOSE_KEYWORDS = {
    "Guiding others": {"mentor", "coach", "guide"},
    "Craft mastery": {"craft", "detail", "artisan"},
    "Well-being": {"health", "balance", "wellbeing"},
}


async def run_soul_engine(person_id: str) -> Dict[str, Any]:
    if not person_id:
        raise ValueError("person_id required")

    journal_rows = await q(
        """
        SELECT created_at, content
        FROM journal_entries
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 120
        """,
        person_id,
    )
    if not journal_rows:
        LOGGER.info("[SoulEngine] no journals person=%s", person_id)
        return {}

    corpus = " ".join((row.get("content") or "") for row in journal_rows)
    tokens = _tokenize(corpus)

    values = _extract_values(tokens)
    identities = _build_identity_signatures(tokens)
    themes = _build_purpose_themes(tokens)
    arcs = _build_life_arcs(journal_rows)
    conflicts = _detect_conflicts(values, themes)
    evolution = _compute_persona_evolution(values, conflicts)

    await _replace_soul_values(person_id, values)
    await _replace_identity_signatures(person_id, identities)
    await _replace_purpose_themes(person_id, themes)
    await _replace_life_arcs(person_id, arcs)
    await _replace_conflicts(person_id, conflicts)
    await _upsert_persona_evolution(person_id, evolution)

    LOGGER.info("[SoulEngine] refreshed soul layers person=%s values=%s identities=%s", person_id, len(values), len(identities))
    return {
        "values": values,
        "identity_signatures": identities,
        "purpose_themes": themes,
        "life_arcs": arcs,
        "conflicts": conflicts,
        "persona_evolution": evolution,
    }


def _tokenize(text: str) -> List[str]:
    sanitized = "".join(ch.lower() if ch.isalpha() else " " for ch in text)
    return [token for token in sanitized.split() if token]


def _extract_values(tokens: List[str]) -> List[Dict[str, Any]]:
    counter = Counter(tokens)
    values: List[Dict[str, Any]] = []
    for value_name, keywords in VALUE_KEYWORDS.items():
        evidence_count = sum(counter[key] for key in keywords)
        if evidence_count == 0:
            continue
        confidence = min(1.0, 0.15 + evidence_count / 20.0)
        values.append(
            {
                "value_name": value_name,
                "description": f"Signals around {value_name}",
                "confidence": round(confidence, 3),
                "anchors": list(keywords),
                "evidence": {"hits": evidence_count},
            }
        )
    if not values:
        values.append(
            {
                "value_name": "balance",
                "description": "Default placeholder value",
                "confidence": 0.3,
                "anchors": [],
                "evidence": {},
            }
        )
    return values


def _build_identity_signatures(tokens: List[str]) -> List[Dict[str, Any]]:
    signatures: List[Dict[str, Any]] = []
    token_text = " ".join(tokens)
    for label, keywords in IDENTITY_PATTERNS.items():
        if any(word in token_text for word in keywords):
            signatures.append(
                {
                    "label": label,
                    "narrative": f"Shows tendencies of a {label.lower()}",
                    "coherence": 0.6 + len(keywords) * 0.02,
                    "supporting_memories": list(keywords),
                }
            )
    if not signatures:
        signatures.append(
            {
                "label": "Integrator",
                "narrative": "Blends multiple roles fluidly.",
                "coherence": 0.55,
                "supporting_memories": [],
            }
        )
    return signatures


def _build_purpose_themes(tokens: List[str]) -> List[Dict[str, Any]]:
    themes: List[Dict[str, Any]] = []
    token_text = " ".join(tokens)
    for theme, keywords in PURPOSE_KEYWORDS.items():
        if any(word in token_text for word in keywords):
            themes.append(
                {
                    "theme": theme,
                    "description": f"Emerging purpose around {theme.lower()}",
                    "anchors": list(keywords),
                    "momentum": 0.6,
                }
            )
    if not themes:
        themes.append(
            {
                "theme": "Self-discovery",
                "description": "Introspective phase focused on aligning actions with values.",
                "anchors": [],
                "momentum": 0.5,
            }
        )
    return themes


def _build_life_arcs(journal_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not journal_rows:
        return []
    sorted_rows = sorted(journal_rows, key=lambda row: row.get("created_at") or datetime.utcnow())
    start = sorted_rows[0].get("created_at")
    end = sorted_rows[-1].get("created_at")
    mid = len(sorted_rows) // 2

    arcs = [
        {
            "arc_name": "Earlier Chapter",
            "start_scope": start,
            "end_scope": sorted_rows[mid].get("created_at"),
            "summary": "Laying foundations",
            "sentiment": 0.2,
            "tags": ["foundation"],
            "narrative": {"tone": "reflective"},
        },
        {
            "arc_name": "Current Chapter",
            "start_scope": sorted_rows[mid].get("created_at"),
            "end_scope": end,
            "summary": "Balancing growth and rest",
            "sentiment": 0.4,
            "tags": ["balance", "growth"],
            "narrative": {"tone": "emerging"},
        },
    ]
    return arcs


def _detect_conflicts(values: List[Dict[str, Any]], themes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    names = {value["value_name"] for value in values}
    conflicts: List[Dict[str, Any]] = []
    if "growth" in names and "stability" in names:
        conflicts.append(
            {
                "conflict_type": "growth_vs_rest",
                "description": "Tension between rest and high drive to grow.",
                "impact": 0.65,
                "tension_between": {"values": ["growth", "stability"]},
                "resolution_hint": "Schedule purposeful downtime.",
            }
        )
    if themes and len(values) > 2:
        conflicts.append(
            {
                "conflict_type": "purpose_alignment",
                "description": "Purpose themes spreading across domains.",
                "impact": 0.45,
                "tension_between": {"themes": [theme["theme"] for theme in themes]},
                "resolution_hint": "Pick one flagship theme per quarter.",
            }
        )
    return conflicts


def _compute_persona_evolution(values: List[Dict[str, Any]], conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    drift_score = min(1.0, 0.3 + len(conflicts) * 0.2)
    current_mode = "Integrator" if len(values) > 2 else values[0]["value_name"]
    path = [{"mode": current_mode, "at": datetime.utcnow().isoformat()}]
    return {"current_mode": current_mode, "drift_score": drift_score, "evolution_path": path}


async def _replace_soul_values(person_id: str, values: List[Dict[str, Any]]) -> None:
    await dbexec("DELETE FROM soul_values WHERE person_id = $1", person_id)
    for value in values:
        await dbexec(
            """
            INSERT INTO soul_values (person_id, value_name, description, confidence, anchors, evidence)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
            """,
            person_id,
            value["value_name"],
            value["description"],
            value["confidence"],
            json.dumps(value.get("anchors") or [], ensure_ascii=False),
            json.dumps(value.get("evidence") or {}, ensure_ascii=False),
        )


async def _replace_identity_signatures(person_id: str, signatures: List[Dict[str, Any]]) -> None:
    await dbexec("DELETE FROM identity_signatures WHERE person_id = $1", person_id)
    for signature in signatures:
        await dbexec(
            """
            INSERT INTO identity_signatures (person_id, label, narrative, coherence, supporting_memories)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            person_id,
            signature["label"],
            signature["narrative"],
            signature["coherence"],
            json.dumps(signature.get("supporting_memories") or [], ensure_ascii=False),
        )


async def _replace_purpose_themes(person_id: str, themes: List[Dict[str, Any]]) -> None:
    await dbexec("DELETE FROM purpose_themes WHERE person_id = $1", person_id)
    for theme in themes:
        await dbexec(
            """
            INSERT INTO purpose_themes (person_id, theme, description, anchors, momentum)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
            person_id,
            theme["theme"],
            theme["description"],
            json.dumps(theme.get("anchors") or [], ensure_ascii=False),
            theme.get("momentum", 0.0),
        )


async def _replace_life_arcs(person_id: str, arcs: List[Dict[str, Any]]) -> None:
    await dbexec("DELETE FROM life_arcs WHERE person_id = $1", person_id)
    for arc in arcs:
        await dbexec(
            """
            INSERT INTO life_arcs (person_id, arc_name, start_scope, end_scope, summary, sentiment, tags, narrative)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            """,
            person_id,
            arc["arc_name"],
            arc["start_scope"],
            arc["end_scope"],
            arc["summary"],
            arc["sentiment"],
            arc.get("tags") or [],
            json.dumps(arc.get("narrative") or {}, ensure_ascii=False),
        )


async def _replace_conflicts(person_id: str, conflicts: List[Dict[str, Any]]) -> None:
    await dbexec("DELETE FROM conflict_records WHERE person_id = $1", person_id)
    for conflict in conflicts:
        await dbexec(
            """
            INSERT INTO conflict_records (person_id, conflict_type, description, impact, tension_between, resolution_hint)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            """,
            person_id,
            conflict["conflict_type"],
            conflict["description"],
            conflict["impact"],
            json.dumps(conflict.get("tension_between") or {}, ensure_ascii=False),
            conflict.get("resolution_hint"),
        )


async def _upsert_persona_evolution(person_id: str, evolution: Dict[str, Any]) -> None:
    await dbexec(
        """
        INSERT INTO persona_evolution (person_id, current_mode, drift_score, evolution_path, updated_at)
        VALUES ($1, $2, $3, $4::jsonb, NOW())
        ON CONFLICT (person_id) DO UPDATE
        SET current_mode = EXCLUDED.current_mode,
            drift_score = EXCLUDED.drift_score,
            evolution_path = EXCLUDED.evolution_path,
            updated_at = NOW()
        """,
        person_id,
        evolution["current_mode"],
        evolution["drift_score"],
        json.dumps(evolution.get("evolution_path") or [], ensure_ascii=False),
    )


__all__ = ["run_soul_engine"]
