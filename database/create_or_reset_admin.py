"""
Utility script to reset admin password
Run from backend folder: python reset_admin.py
"""
import asyncio
import sys
from pathlib import Path

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


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
    
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        # Check existing users
        result = await conn.execute(text("SELECT id, email, hashed_password FROM users"))
        users = result.fetchall()
        
        print(f"\nExisting users in database:")
        for user in users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Hash: {user[2][:30]}...")
        
        if not users:
            print("\nNo users found! Creating admin user...")
            await conn.execute(text("""
                INSERT INTO users (email, hashed_password, full_name, role, is_active, is_superuser)
                VALUES (:email, :hash, 'QAstra Admin', 'admin', true, true)
            """), {"email": admin_email, "hash": hashed})
            print("Admin user created!")
        else:
            # Update first user's password
            user_id = users[0][0]
            user_email = users[0][1]
            print(f"\nUpdating password for user {user_email}...")
            await conn.execute(text("""
                UPDATE users SET hashed_password = :hash WHERE id = :id
            """), {"hash": hashed, "id": user_id})
            print(f"Password updated for {user_email}!")
    
    await engine.dispose()
    print(f"\n✓ Login with:")
    print(f"  Email: {users[0][1] if users else admin_email}")
    print(f"  Password: {admin_password}")

if __name__ == "__main__":
    asyncio.run(reset_admin())
