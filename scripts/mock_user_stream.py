#!/usr/bin/env python3
import asyncio
import httpx

API = "http://localhost:8000"
PERSON = "11111111-1111-1111-1111-111111111111"
SESSION = "mock-session"
MESSAGES = [f"Message {i} — testing end-to-end flow" for i in range(1, 101)]


async def main() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        for index, text in enumerate(MESSAGES, start=1):
            resp = await client.post(
                f"{API}/memory/observe",
                json={
                    "person_id": PERSON,
                    "text": text,
                    "session_id": SESSION,
                },
            )
            print(f"{index:03} | {resp.status_code} | {text[:40]}")
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
