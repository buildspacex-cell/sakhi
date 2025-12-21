from __future__ import annotations

import re
from typing import Tuple

from .models import AddListItem, CreateEvent, SetReminder

LIST_RE = re.compile(r"add (.+?) to (?:my )?(grocery|groceries|shopping|inbox|todo|to[- ]?do) list", re.IGNORECASE)
REMIND_RE = re.compile(r"remind me (?:to )?(.+?) (?:at|on) (.+)", re.IGNORECASE)
SCHED_RE = re.compile(r"schedule (.+?) (?:on|at) (.+)", re.IGNORECASE)


class ParsedIntent:
    def __init__(self, kind: str, slots: dict, conf: float = 0.9) -> None:
        self.kind = kind
        self.slots = slots
        self.conf = conf

    def to_actions(self):
        if self.kind == "add_list":
            return [
                AddListItem(
                    list_name=_norm_list(self.slots["list"]),
                    items=_split(self.slots["items"]),
                )
            ]
        if self.kind == "remind":
            return [
                SetReminder(
                    title=self.slots["title"],
                    time=self.slots["when"],
                )
            ]
        if self.kind == "schedule":
            return [
                CreateEvent(
                    title=self.slots["title"],
                    start=self.slots["when"],
                    duration_min=60,
                )
            ]
        return []


def _norm_list(name: str) -> str:
    n = name.lower()
    if n in {"grocery", "groceries", "shopping"}:
        return "Groceries"
    if n in {"todo", "to-do", "inbox"}:
        return "Inbox"
    return name.title()


def _split(items: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r",| and ", items) if chunk.strip()]


def fast_parse(text: str) -> Tuple[ParsedIntent, float]:
    match = LIST_RE.search(text)
    if match:
        return ParsedIntent("add_list", {"items": match.group(1), "list": match.group(2)}), 0.95

    match = REMIND_RE.search(text)
    if match:
        return ParsedIntent("remind", {"title": match.group(1), "when": match.group(2)}), 0.9

    match = SCHED_RE.search(text)
    if match:
        return ParsedIntent("schedule", {"title": match.group(1), "when": match.group(2)}), 0.85

    return ParsedIntent("none", {}), 0.0
