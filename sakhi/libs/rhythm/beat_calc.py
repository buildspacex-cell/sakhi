from __future__ import annotations

from datetime import time
from typing import Dict, List


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def calc_daily_beats(sleep_start: time = time(22, 30), wake: time = time(6, 0)) -> List[Dict]:
    """Return coarse circadian rhythm windows anchored to the wake time."""

    w = _to_minutes(wake)
    blocks = [
        ("morning-clarity", w, w + 240),
        ("midday-peak", w + 240, w + 420),
        ("afternoon-dip", w + 420, w + 600),
        ("evening-calm", w + 780, w + 900),
    ]
    out = []
    for label, start, end in blocks:
        start_hours, start_minutes = divmod(start % 1440, 60)
        end_hours, end_minutes = divmod(end % 1440, 60)
        out.append(
            {
                "label": label,
                "start": f"{start_hours:02d}:{start_minutes:02d}",
                "end": f"{end_hours:02d}:{end_minutes:02d}",
            }
        )
    return out
