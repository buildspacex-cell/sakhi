from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(slots=True)
class IngestedEntry:
    entry_id: str
    person_id: str
    status: str
    created_at: dt.datetime
    tags: List[str]


@dataclass(slots=True)
class ObserveJobPayload:
    entry_id: str
    person_id: str
    text: str
    layer: str
    tags: List[str]
    created_at: dt.datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "person_id": self.person_id,
            "text": self.text,
            "layer": self.layer,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
        }


__all__ = ["IngestedEntry", "ObserveJobPayload"]
