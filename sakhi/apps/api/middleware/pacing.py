"""Attach pacing metadata headers to responses based on circadian beats."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence

from starlette.middleware.base import BaseHTTPMiddleware

from sakhi.libs.rhythm.beat_calc import calc_daily_beats


def _phase(now_hm: str, beats: Sequence[Mapping[str, str]]) -> str:
    """Return the label of the beat whose interval contains `now_hm`."""

    for beat in beats:
        start = beat.get("start")
        end = beat.get("end")
        label = beat.get("label", "any")
        if isinstance(start, str) and isinstance(end, str) and start <= now_hm <= end:
            return label
    return "any"


class ReplyPacingMiddleware(BaseHTTPMiddleware):
    """Set response headers indicating recommended pacing for clients."""

    _DELAYS: Mapping[str, str] = {
        "morning-clarity": "250",
        "midday-peak": "150",
        "afternoon-dip": "400",
        "evening-calm": "300",
        "any": "250",
    }

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        now = datetime.now()
        beats = calc_daily_beats()
        phase = _phase(now.strftime("%H:%M"), beats)
        response.headers["X-Sakhi-Pacing-ms"] = self._DELAYS.get(phase, "250")
        response.headers["X-Sakhi-Phase"] = phase
        return response
