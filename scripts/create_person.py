import asyncio
import uuid
import os
import asyncpg

PERSON_ID = os.environ.get("PERSON_ID", "565bdb63-124b-4692-a039-846fddceff90")

async def main():
    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn)
    await conn.execute(
        """
        INSERT INTO persons (id, created_at, updated_at, locale)
        VALUES ($1::uuid, now(), now(), 'en-US')
        ON CONFLICT (id) DO NOTHING
        """,
        PERSON_ID,
    )
    await conn.close()
    print("Ensured person", PERSON_ID)

if __name__ == "__main__":
    asyncio.run(main())
