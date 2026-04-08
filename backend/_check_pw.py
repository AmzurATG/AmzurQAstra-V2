import asyncio
import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        r = await conn.execute(text("SELECT hashed_password FROM users WHERE email='admin@qastra.dev'"))
        hp = r.scalar()
        print(f"Hash: {hp}")
        result = bcrypt.checkpw(b"admin123", hp.encode("utf-8"))
        print(f"Password matches: {result}")
    await engine.dispose()

asyncio.run(check())
