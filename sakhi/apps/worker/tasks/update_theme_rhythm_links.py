from __future__ import annotations

import logging
import numpy as np

from sakhi.apps.api.core.db import get_db

LOGGER = logging.getLogger(__name__)


async def update_theme_rhythm_links() -> None:
    """Compute per-theme rhythm correlations for each person."""

    db = await get_db()
    try:
        LOGGER.info("[Rhythm] Updating theme–rhythm correlations")
        rows = await db.fetch(
            """
            SELECT f.person_id,
                   ts.theme,
                   ts.clarity_score,
                   f.predicted_energy AS energy_score
            FROM theme_states AS ts
            JOIN rhythm_forecasts AS f
              ON f.person_id = ts.person_id
            WHERE ts.updated_at >= now() - interval '21 days'
              AND f.created_at >= now() - interval '21 days'
              AND ts.clarity_score IS NOT NULL
              AND f.predicted_energy IS NOT NULL
            """
        )
        if not rows:
            LOGGER.info("[Rhythm] No reflections available for correlation update")
            return

        # person_id, theme → clarity & energy series
        grouped: dict[tuple[str, str], dict[str, list[float]]] = {}
        for row in rows:
            key = (row["person_id"], row.get("theme") or "general")
            grouped.setdefault(key, {"clarity": [], "energy": []})
            grouped[key]["clarity"].append(float(row["clarity_score"]))
            grouped[key]["energy"].append(float(row["energy_score"]))

        for (person_id, theme), series in grouped.items():
            clarity = series["clarity"]
            energy = series["energy"]
            if len(clarity) > 2:
                try:
                    correlation = float(np.corrcoef(clarity, energy)[0, 1])
                except Exception:
                    correlation = 0.0
            else:
                correlation = 0.0
            clarity_trend = float(np.mean(np.diff(clarity))) if len(clarity) > 1 else 0.0
            energy_trend = float(np.mean(np.diff(energy))) if len(energy) > 1 else 0.0
            samples = len(clarity)

            await db.execute(
                """
                INSERT INTO theme_rhythm_links(
                    person_id, theme, correlation, clarity_trend, energy_trend, samples, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, now())
                ON CONFLICT (person_id, theme) DO UPDATE
                  SET correlation = EXCLUDED.correlation,
                      clarity_trend = EXCLUDED.clarity_trend,
                      energy_trend = EXCLUDED.energy_trend,
                      samples = EXCLUDED.samples,
                      updated_at = now()
                """,
                person_id,
                theme,
                correlation,
                clarity_trend,
                energy_trend,
                samples,
            )

        LOGGER.info("[Rhythm] Updated %s theme-rhythm links", len(grouped))
    finally:
        await db.close()


__all__ = ["update_theme_rhythm_links"]
