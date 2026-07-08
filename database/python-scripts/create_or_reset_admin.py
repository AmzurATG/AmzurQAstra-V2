"""
Utility script to reset admin password
Run from backend folder: python reset_admin.py
"""
import asyncio
import sys
from pathlib import Path

# Ensure the backend package is importable
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_BACKEND_DIR))

# Enforce .env existence before importing config
_ENV_FILE = _BACKEND_DIR / ".env"
if not _ENV_FILE.is_file():
    print(f"ERROR: Required .env file not found at: {_ENV_FILE}")
    print("Copy backend/.env.example to backend/.env and configure it.")
    sys.exit(1)

import bcrypt
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine


async def reset_admin():
    # Get config from backend/.env
    from config import settings

    db_url = settings.DATABASE_URL
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set. Please configure it in backend/.env")

    admin_email = settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD

    # Generate password hash
    password_bytes = admin_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    print(f"Admin email: {admin_email}")
    print(f"Password hash generated successfully")
    print(f"Verification: {bcrypt.checkpw(password_bytes, hashed.encode('utf-8'))}")
    print(f"\nConnecting to: {db_url}")
    print(f"Configured schema: {settings.DB_SCHEMA}")

    def _quoted_ident(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'
    
    users = []

    async def _run_async() -> list:
        engine = create_async_engine(db_url)
        try:
            async with engine.begin() as conn:
                schema_result = await conn.execute(text("""
                    SELECT table_schema
                    FROM information_schema.tables
                    WHERE table_name = 'users'
                    ORDER BY
                        CASE
                            WHEN table_schema = :preferred_schema THEN 0
                            WHEN table_schema = 'public' THEN 1
                            ELSE 2
                        END,
                        table_schema
                    LIMIT 1
                """), {"preferred_schema": settings.DB_SCHEMA})
                users_schema = schema_result.scalar_one_or_none()

                if not users_schema:
                    raise RuntimeError(
                        "users table not found in any schema. Run migrations first: "
                        "cd backend && alembic upgrade head"
                    )

                print(f"Using users table schema: {users_schema}")
                await conn.execute(text(f"SET search_path TO {_quoted_ident(users_schema)}"))

                # Check existing users
                result = await conn.execute(text("SELECT id, email, hashed_password FROM users"))
                current_users = result.fetchall()

                print(f"\nExisting users in database:")
                for user in current_users:
                    print(f"  ID: {user[0]}, Email: {user[1]}, Hash: {user[2][:30]}...")

                if not current_users:
                    print("\nNo users found! Creating admin user...")
                    await conn.execute(text("""
                        INSERT INTO users (email, hashed_password, full_name, role, is_active, is_superuser)
                        VALUES (:email, :hash, 'QAstra Admin', 'admin', true, true)
                    """), {"email": admin_email, "hash": hashed})
                    print("Admin user created!")
                else:
                    # Update first user's password
                    user_id = current_users[0][0]
                    user_email = current_users[0][1]
                    print(f"\nUpdating password for user {user_email}...")
                    await conn.execute(text("""
                        UPDATE users SET hashed_password = :hash WHERE id = :id
                    """), {"hash": hashed, "id": user_id})
                    print(f"Password updated for {user_email}!")

                return current_users
        finally:
            await engine.dispose()

    def _run_sync() -> list:
        sync_url = db_url.replace("+asyncpg", "+psycopg2")
        print("Using sync SQLAlchemy engine fallback (psycopg2).")
        print(f"Fallback URL: {sync_url}")
        engine = create_engine(sync_url)
        try:
            with engine.begin() as conn:
                schema_result = conn.execute(text("""
                    SELECT table_schema
                    FROM information_schema.tables
                    WHERE table_name = 'users'
                    ORDER BY
                        CASE
                            WHEN table_schema = :preferred_schema THEN 0
                            WHEN table_schema = 'public' THEN 1
                            ELSE 2
                        END,
                        table_schema
                    LIMIT 1
                """), {"preferred_schema": settings.DB_SCHEMA})
                users_schema = schema_result.scalar_one_or_none()

                if not users_schema:
                    raise RuntimeError(
                        "users table not found in any schema. Run migrations first: "
                        "cd backend && alembic upgrade head"
                    )

                print(f"Using users table schema: {users_schema}")
                conn.execute(text(f"SET search_path TO {_quoted_ident(users_schema)}"))

                result = conn.execute(text("SELECT id, email, hashed_password FROM users"))
                current_users = result.fetchall()

                print(f"\nExisting users in database:")
                for user in current_users:
                    print(f"  ID: {user[0]}, Email: {user[1]}, Hash: {user[2][:30]}...")

                if not current_users:
                    print("\nNo users found! Creating admin user...")
                    conn.execute(text("""
                        INSERT INTO users (email, hashed_password, full_name, role, is_active, is_superuser)
                        VALUES (:email, :hash, 'QAstra Admin', 'admin', true, true)
                    """), {"email": admin_email, "hash": hashed})
                    print("Admin user created!")
                else:
                    user_id = current_users[0][0]
                    user_email = current_users[0][1]
                    print(f"\nUpdating password for user {user_email}...")
                    conn.execute(text("""
                        UPDATE users SET hashed_password = :hash WHERE id = :id
                    """), {"hash": hashed, "id": user_id})
                    print(f"Password updated for {user_email}!")

                return current_users
        finally:
            engine.dispose()

    try:
        users = await _run_async()
    except ImportError as exc:
        message = str(exc)
        if "_ctypes" in message or "asyncpg" in message:
            print(f"Async driver import failed ({message}).")
            users = _run_sync()
        else:
            raise

    print(f"\n✓ Login with:")
    print(f"  Email: {users[0][1] if users else admin_email}")
    print(f"  Password: {admin_password}")

if __name__ == "__main__":
    asyncio.run(reset_admin())
