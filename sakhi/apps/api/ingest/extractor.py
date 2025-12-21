from __future__ import annotations

import datetime as dt
import re

from dateutil import parser as dtp

ACTION_WORDS = {"schedule", "remind", "block", "book", "create", "plan", "buy", "pay"}
MOOD_LEX = {
    "overwhelmed": (-0.6, "tense"),
    "stressed": (-0.5, "tense"),
    "anxious": (-0.5, "tense"),
    "tired": (-0.3, "low"),
    "focused": (0.6, "calm"),
    "excited": (0.7, "vital"),
    "happy": (0.5, "calm"),
}


def try_parse_time(text: str, ref: dt.datetime | None = None) -> dt.datetime | None:
    ref = ref or dt.datetime.now()
    try:
        return dtp.parse(text, default=ref)
    except Exception:
        return None


def extract(message: str, now: dt.datetime | str | None = None) -> dict:
    if isinstance(now, str):
        try:
            now = dt.datetime.fromisoformat(now.replace("Z", ""))
        except Exception:
            now = dt.datetime.utcnow()
    if not isinstance(now, dt.datetime):
        now = dt.datetime.utcnow()
    out = {"triage": [], "slots": {}, "abstentions": []}
    lower = (message or "").lower()

    is_action = any(word in lower for word in ACTION_WORDS)
    is_reflect = any(phrase in lower for phrase in ["i feel", "feeling", "felt", "mood", "today i"])
    is_finance = any(token in lower for token in ["buy", "pay", "budget", "₹", "rs ", "inr", "emi", "down payment"])
    if is_action:
        out["triage"].append({"type": "intent_action", "confidence": 0.8})
    if is_reflect:
        out["triage"].append({"type": "reflection_observation", "confidence": 0.7})
    if is_finance:
        out["triage"].append({"type": "finance", "confidence": 0.6})

    goal_match = re.search(r"(for|to)\s+(the\s+)?([a-z0-9 _\-]{3,60})$", lower)
    if goal_match:
        out["slots"]["goal"] = {"text": goal_match.group(3).strip(), "confidence": 0.7}

    tw = None
    for pat in ["tomorrow", "today", "next week", "this week", "tonight", "this evening", "this morning"]:
        if pat in lower:
            tw = pat
    hhmm = re.search(r"(\d{1,2})(:\d{2})?\s*(am|pm)?", lower)
    if hhmm:
        t = try_parse_time(hhmm.group(0), now)
        if t:
            out["slots"]["time_window"] = {"start": t.isoformat(), "confidence": 0.8}
    elif tw:
        ref = now
        if isinstance(ref, str):
            try:
                ref = dt.datetime.fromisoformat(ref.replace("Z", ""))
            except Exception:
                ref = dt.datetime.utcnow()
        if not isinstance(ref, dt.datetime):
            ref = dt.datetime.utcnow()
        if tw == "tomorrow":
            ref = ref + dt.timedelta(days=1)
        elif tw == "today":
            ref = ref
        else:
            ref = ref
        out["slots"]["time_window"] = {"start": ref.isoformat(), "confidence": 0.6}

    for word, (score, tone) in MOOD_LEX.items():
        if word in lower:
            out["slots"]["mood_affect"] = {"label": word, "score": score, "confidence": 0.8}
            out["energy_tone_hint"] = {
                "calm": 0.7 if tone == "calm" else 0.3,
                "vital": 0.7 if tone == "vital" else 0.3,
                "agitated": 0.7 if tone == "tense" else 0.2,
            }
            break

    return out
