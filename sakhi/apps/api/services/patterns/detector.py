from __future__ import annotations

import logging
import json
from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec, q

LOGGER = logging.getLogger(__name__)

WINDOWS: Dict[str, int] = {"7d": 7, "30d": 30}
THEME_EMOTION_WEIGHTS = {"sentiment": 0.6, "energy": 0.4}


async def _fetch_entries(person_id: str, days: int) -> List[Dict[str, Any]]:
    window_arg = str(days)
    return await q(
        """
        SELECT
            id,
            content,
            facets_v2,
            COALESCE(facets_v2->>'theme', 'general') AS theme,
            created_at
        FROM journal_entries
        WHERE user_id = $1
          AND created_at > NOW() - ($2 || ' days')::interval
        ORDER BY created_at DESC
        """,
        person_id,
        window_arg,
    )


async def _fetch_reflections(person_id: str, days: int) -> List[Dict[str, Any]]:
    window_arg = str(days)
    return await q(
        """
        SELECT id, content, theme, created_at
        FROM reflections
        WHERE user_id = $1
          AND created_at > NOW() - ($2 || ' days')::interval
        ORDER BY created_at DESC
        """,
        person_id,
        window_arg,
    )


async def _fetch_journal_themes(person_id: str, time_window: str) -> List[Dict[str, Any]]:
    return await q(
        """
        SELECT theme, metrics
        FROM journal_themes
        WHERE user_id = $1
          AND time_window = $2
        """,
        person_id,
        time_window,
    )


def _coerce_facets(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _collect_theme_emotion_signals(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[float]]]:
    signals: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        theme = (row.get("theme") or "general").lower()
        facets = _coerce_facets(row.get("facets_v2"))
        try:
            sentiment = float(facets.get("sentiment", 0.0))
        except (TypeError, ValueError):
            sentiment = 0.0
        try:
            energy = float(facets.get("energy_level", 0.0))
        except (TypeError, ValueError):
            energy = 0.0
        if theme not in signals:
            signals[theme] = {"sentiment": [], "energy": []}
        signals[theme]["sentiment"].append(sentiment)
        signals[theme]["energy"].append(energy)
    return signals


def _compute_trends(series: List[float]) -> tuple[float, float]:
    if not series:
        return 0.0, 0.0
    mean = sum(series) / len(series)
    return mean, (series[-1] - mean)


def _score_theme(data: Dict[str, List[float]]) -> Dict[str, float]:
    s_mean, s_mom = _compute_trends(data["sentiment"])
    e_mean, e_mom = _compute_trends(data["energy"])
    score = THEME_EMOTION_WEIGHTS["sentiment"] * s_mean + THEME_EMOTION_WEIGHTS["energy"] * e_mean
    momentum = THEME_EMOTION_WEIGHTS["sentiment"] * s_mom + THEME_EMOTION_WEIGHTS["energy"] * e_mom
    return {
        "score": float(score),
        "momentum": float(momentum),
        "sentiment_mean": float(s_mean),
        "energy_mean": float(e_mean),
    }


def _merge_journal_themes(
    theme_scores: Dict[str, Dict[str, float]], jthemes: List[Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    for row in jthemes:
        theme = (row.get("theme") or "").lower()
        metrics = row.get("metrics") or {}
        sal = float(metrics.get("salience", 0.0))
        sig = float(metrics.get("significance", 0.0))
        if theme not in theme_scores:
            theme_scores[theme] = {
                "score": 0.0,
                "momentum": 0.0,
                "sentiment_mean": 0.0,
                "energy_mean": 0.0,
            }
        theme_scores[theme]["salience"] = sal
        theme_scores[theme]["significance"] = sig
        theme_scores[theme]["score"] += sal * 0.15 + sig * 0.1
    return theme_scores


async def detect_patterns(person_id: str) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for window_name, days in WINDOWS.items():
        entries = await _fetch_entries(person_id, days)
        reflections = await _fetch_reflections(person_id, days)
        journal_themes = await _fetch_journal_themes(person_id, window_name)
        rows = entries + reflections
        emo_data = _collect_theme_emotion_signals(rows)
        theme_scores: Dict[str, Dict[str, float]] = {
            theme: _score_theme(values) for theme, values in emo_data.items()
        }
        theme_scores = _merge_journal_themes(theme_scores, journal_themes)
        sorted_themes = sorted(
            theme_scores.items(), key=lambda kv: kv[1].get("momentum", 0.0), reverse=True
        )
        results[window_name] = {
            "theme_scores": theme_scores,
            "top_emerging": sorted_themes[:3],
            "top_declining": sorted_themes[-3:],
        }
        for theme, data in theme_scores.items():
            await dbexec(
                """
                INSERT INTO pattern_stats (id, pattern_type, metric, value, confidence, created_at)
                VALUES (gen_random_uuid(), 'theme_emotion', $1, $2, 0.8, NOW())
                """,
                theme,
                float(data.get("momentum", 0.0)),
            )
    return results


async def build_patterns_context(person_id: str) -> str:
    data = await detect_patterns(person_id)
    lines: List[str] = []
    for window, payload in data.items():
        lines.append(f"Window {window}:")
        for theme, info in payload["theme_scores"].items():
            lines.append(f"- {theme}: score={info['score']:.2f}, momentum={info['momentum']:.2f}")
    preview = "\n".join(lines)
    return preview[:2000]


__all__ = ["detect_patterns", "build_patterns_context"]
