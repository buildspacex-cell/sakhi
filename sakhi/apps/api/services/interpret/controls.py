from __future__ import annotations

import re
from typing import Optional, Dict

SWITCH_RE = re.compile(r"\b(switch|back)\s+(to|into)\s+(.*)", re.IGNORECASE)
NEW_RE = re.compile(r"\b(new topic|start (a )?new)\b", re.IGNORECASE)
TITLE_RE = re.compile(r"\btitle (this|thread) (as|to)\s+[\"“]?(.+?)[\"”?]?\b", re.IGNORECASE)
BOOKMARK_RE = re.compile(r"\bbookmark this\b", re.IGNORECASE)


def control_intent(text: str) -> Optional[Dict[str, str]]:
    if not text:
        return None
    if (match := SWITCH_RE.search(text)):
        return {"type": "switch", "hint": match.group(3).strip()}  # type: ignore[arg-type]
    if NEW_RE.search(text):
        return {"type": "new"}
    if (match := TITLE_RE.search(text)):
        return {"type": "title", "title": match.group(3).strip()}  # type: ignore[arg-type]
    if BOOKMARK_RE.search(text):
        return {"type": "bookmark"}
    return None
