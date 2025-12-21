import os
import httpx
from fastapi import Header, HTTPException


def _get_env(*keys: str) -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    raise RuntimeError(f"Missing required environment variable. Checked: {', '.join(keys)}")


SUPABASE_URL = _get_env("SUPABASE_URL", "SAKHI_SUPABASE_URL")
SUPABASE_ANON_KEY = _get_env("SUPABASE_ANON_KEY", "SAKHI_SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY", "SAKHI_SUPABASE_SERVICE_KEY")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_USER_ID = os.getenv("DEMO_USER_ID")


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY},
                timeout=10,
            )
        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, dict) and "id" in payload:
                return payload["id"]

    if DEMO_MODE and DEMO_USER_ID:
        return DEMO_USER_ID

    raise HTTPException(status_code=401, detail="Unauthenticated")
