"""Ayurvedic diagnosis endpoint using the shared LLM router."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status

from sakhi.libs.llm_router import LLMRouter
from sakhi.libs.schemas import get_settings

router_diag = APIRouter()

DOSHAS: List[str] = ["vata", "pitta", "kapha"]

_DIAGNOSE_SYS = (
    "You are an Ayurvedic reasoning assistant. Infer dosha tendencies from user description. "
    "Return JSON with fields: dosha_vector (vata,pitta,kapha in [0,1]), primary, rationale, 3 lifestyle suggestions."
)


def _get_router(request: Request) -> LLMRouter:
    router = getattr(request.app.state, "llm_router", None)
    if router is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM router unavailable")
    return router


@router_diag.post("/diagnose")
async def diagnose(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Return a dosha vector and rationale based on the provided description."""

    description = (body.get("description") or "").strip()
    if not description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="description is required")

    messages = [
        {"role": "system", "content": _DIAGNOSE_SYS},
        {"role": "user", "content": f"User description:\n{description}\nOutput JSON only."},
    ]

    router = _get_router(request)
    settings = get_settings()
    response = await router.chat(messages=messages, model=settings.model_chat)

    try:
        payload = json.loads(response.text or "{}")
    except json.JSONDecodeError:
        payload = {"raw": response.text}

    return payload
