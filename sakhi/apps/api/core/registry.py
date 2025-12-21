from __future__ import annotations

from typing import Dict, List

from .contracts import Aspect

ASPECTS: Dict[str, Aspect] = {}


def register(aspect: Aspect) -> None:
    ASPECTS[aspect.name] = aspect


def active_aspects_for(person_id: str) -> List[str]:
    return list(ASPECTS.keys())
