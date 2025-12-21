from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec, q as dbq

LOGGER = logging.getLogger(__name__)


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


async def _load_context(person_id: str) -> Dict[str, Any]:
    soul_values = await dbq(
        """
        SELECT value_name, description, confidence
        FROM soul_values
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 5
        """,
        person_id,
    )
    soul_identities = await dbq(
        """
        SELECT label, narrative, coherence
        FROM identity_signatures
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 3
        """,
        person_id,
    )
    soul_purpose = await dbq(
        """
        SELECT theme, description, momentum
        FROM purpose_themes
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 3
        """,
        person_id,
    )
    persona_evo = await dbq(
        """
        SELECT current_mode, drift_score, evolution_path, updated_at
        FROM persona_evolution
        WHERE person_id = $1
        """,
        person_id,
    )
    rhythm = await dbq(
        """
        SELECT body_energy, fatigue_level, stress_level
        FROM rhythm_state
        WHERE person_id = $1
        """,
        person_id,
    )
    memory_weekly = await dbq(
        """
        SELECT week_start, week_end, top_themes, highlights
        FROM memory_weekly_summaries
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
    )
    growth = await dbq(
        """
        SELECT label, streak_count, micro_progress, confidence
        FROM growth_habits
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 3
        """,
        person_id,
    )
    return {
        "soul": {
            "values": soul_values,
            "identity_signatures": soul_identities,
            "purpose_themes": soul_purpose,
            "persona_evolution": persona_evo[0] if persona_evo else {},
        },
        "rhythm": rhythm[0] if rhythm else {},
        "weekly": memory_weekly[0] if memory_weekly else {},
        "growth": growth,
    }


def _pick_season(ctx: Dict[str, Any]) -> str:
    energy = ctx.get("rhythm", {}).get("body_energy")
    streaks = ctx.get("growth") or []
    has_habit = bool(streaks)
    if energy is not None:
        try:
            e = float(energy)
            if e > 0.75 and has_habit:
                return "building momentum"
            if e < 0.35:
                return "recovery"
        except Exception:
            pass
    return "exploration"


def _build_patterns(ctx: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    growth = ctx.get("growth") or []
    successes: List[Dict[str, Any]] = []
    struggles: List[Dict[str, Any]] = []
    for habit in growth:
        label = habit.get("label")
        confidence_raw = habit.get("confidence")
        streak_raw = habit.get("streak_count")
        try:
            confidence = float(confidence_raw) if confidence_raw is not None else None
        except Exception:
            confidence = None
        try:
            streak = float(streak_raw) if streak_raw is not None else None
        except Exception:
            streak = None
        if confidence is not None and confidence >= 0.6:
            successes.append({"pattern": f"Progress on {label}", "signal": confidence})
        elif streak is not None and streak < 1:
            struggles.append({"pattern": f"Restart {label}", "signal": streak})
    themes = _coerce_list(ctx.get("weekly", {}).get("top_themes"))
    if themes:
        successes.append({"pattern": f"Themes: {', '.join(t.get('theme') if isinstance(t, dict) else str(t) for t in themes[:3])}", "signal": 0.5})
    return successes, struggles


def _build_narrative_text(ctx: Dict[str, Any], season: str, successes: List[Dict[str, Any]], struggles: List[Dict[str, Any]]) -> str:
    values = _coerce_list(ctx.get("soul", {}).get("values"))
    value_names = [v.get("value_name") for v in values if isinstance(v, dict) and v.get("value_name")]
    identity_labels = [i.get("label") for i in _coerce_list(ctx.get("soul", {}).get("identity_signatures")) if isinstance(i, dict) and i.get("label")]
    themes = ctx.get("weekly", {}).get("highlights")

    parts: List[str] = []
    parts.append(f"Season: {season}.")
    if value_names:
        parts.append(f"Values in play: {', '.join(value_names[:3])}.")
    if identity_labels:
        parts.append(f"Evolving identity: {identity_labels[0]}.")
    if themes:
        parts.append(f"Recent focus: {themes}")
    if successes:
        parts.append(f"Success patterns: {', '.join(p.get('pattern') for p in successes if p.get('pattern'))}.")
    if struggles:
        parts.append(f"Watchouts: {', '.join(p.get('pattern') for p in struggles if p.get('pattern'))}.")
    if not parts:
        parts.append("Continuing your journey with gentle momentum.")
    return " ".join(parts)


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    try:
        # Cast decimals to float; leave other primitives alone.
        from decimal import Decimal

        if isinstance(obj, Decimal):
            return float(obj)
    except Exception:
        pass
    return obj


async def run_narrative_engine(person_id: str) -> Dict[str, Any]:
    ctx = await _load_context(person_id)
    season = _pick_season(ctx)
    successes, struggles = _build_patterns(ctx)
    narrative_text = _build_narrative_text(ctx, season, successes, struggles)

    identity_snapshot = {
        "values": ctx.get("soul", {}).get("values"),
        "identity_signatures": ctx.get("soul", {}).get("identity_signatures"),
        "purpose_themes": ctx.get("soul", {}).get("purpose_themes"),
    }

    story_id = str(uuid.uuid4())
    try:
        await dbexec(
            """
            INSERT INTO narrative_stories (id, person_id, narrative, season, patterns_success, patterns_struggle, identity_snapshot)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb)
            """,
            story_id,
            person_id,
            narrative_text,
            season,
            json.dumps(_sanitize(successes), ensure_ascii=False),
            json.dumps(_sanitize(struggles), ensure_ascii=False),
            json.dumps(_sanitize(identity_snapshot), ensure_ascii=False),
        )
    except Exception as exc:
        LOGGER.warning("[Narrative] failed to insert story for %s: %s", person_id, exc)

    try:
        await dbexec(
            """
            INSERT INTO narrative_seasons (person_id, season, hints)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (person_id)
            DO UPDATE SET season = EXCLUDED.season, hints = EXCLUDED.hints, updated_at = NOW()
            """,
            person_id,
            season,
            json.dumps({"successes": successes, "struggles": struggles}, ensure_ascii=False),
        )
    except Exception as exc:
        LOGGER.warning("[Narrative] failed to upsert season for %s: %s", person_id, exc)

    # Optional identity evolution event when label changes
    if identity_snapshot.get("identity_signatures"):
        label = identity_snapshot["identity_signatures"][0].get("label")
        if label:
            try:
                await dbexec(
                    """
                    INSERT INTO identity_evolution_events (id, person_id, label, summary, evidence)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    """,
                    str(uuid.uuid4()),
                    person_id,
                    label,
                    f"Identity mode noted: {label}",
                    json.dumps({"season": season}, ensure_ascii=False),
                )
            except Exception as exc:
                LOGGER.warning("[Narrative] failed to insert identity event for %s: %s", person_id, exc)

    return {
        "story_id": story_id,
        "season": season,
        "narrative": narrative_text,
        "successes": successes,
        "struggles": struggles,
    }


async def get_narrative_summary(person_id: str) -> Dict[str, Any]:
    story = await dbq(
        """
        SELECT narrative, season, patterns_success, patterns_struggle, identity_snapshot, created_at
        FROM narrative_stories
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
    )
    season_row = await dbq(
        """
        SELECT season, hints, updated_at
        FROM narrative_seasons
        WHERE person_id = $1
        """,
        person_id,
    )
    return {
        "story": story[0] if story else None,
        "season": season_row[0] if season_row else None,
    }


__all__ = ["run_narrative_engine", "get_narrative_summary"]
