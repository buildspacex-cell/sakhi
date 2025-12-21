from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException

from apps.worker.jobs.runner import run_once

router = APIRouter(prefix="/worker", tags=["worker"])


async def _require_token(x_worker_token: str | None = Header(default=None, alias="X-Worker-Token")) -> None:
    token = os.getenv("WORKER_CONTROL_TOKEN")
    if not token:
        return
    if x_worker_token != token:
        raise HTTPException(status_code=403, detail="invalid worker control token")


@router.post("/consolidate/run")
async def consolidate_run(_: None = Depends(_require_token)) -> dict:
    await run_once()
    return {"ok": True}
