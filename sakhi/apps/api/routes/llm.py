from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from sakhi.libs.llm_router import LLMRouter

router = APIRouter(prefix="/llm", tags=["llm"])


class ChatMessageIn(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequestIn(BaseModel):
    messages: List[ChatMessageIn]
    model: Optional[str] = None
    force_json: bool = False


def _get_router(request: Request) -> LLMRouter:
    router = getattr(request.app.state, "llm_router", None)
    if router is None:
        raise HTTPException(status_code=503, detail="LLM router unavailable")
    return router


@router.post("/chat")
async def llm_chat(body: ChatRequestIn, request: Request) -> dict:
    router = _get_router(request)
    response = await router.chat(
        messages=[msg.dict() for msg in body.messages],
        model=body.model,
        force_json=body.force_json,
    )
    return {
        "id": getattr(response, "id", None),
        "text": response.text,
        "provider": response.provider,
        "model": response.model,
        "usage": response.usage,
    }
