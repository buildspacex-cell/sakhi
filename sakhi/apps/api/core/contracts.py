from __future__ import annotations

from typing import Any, Dict, Protocol, TypedDict


class Context(TypedDict, total=False):
    intent: Dict[str, Any]
    constraints: Dict[str, Any]
    timeline: Dict[str, Any]
    aspects: Dict[str, Dict[str, Any]]
    support: Dict[str, Any]


class Aspect(Protocol):
    name: str

    async def fetch(self, msg: str, person_id: str, horizon: str) -> Dict[str, Any]:
        ...

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def score(self, candidate: Dict[str, Any], ctx: Context) -> Dict[str, float]:
        ...

    def adjust(self, candidate: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
        ...

    def explain(self, candidate: Dict[str, Any], scores: Dict[str, float]) -> str:
        ...
