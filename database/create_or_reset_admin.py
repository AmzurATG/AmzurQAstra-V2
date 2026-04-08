"""
Utility script to reset admin password
Run from backend folder: python reset_admin.py
"""
import asyncio
import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Generate a fresh hash for 'admin123'
password = "admin123"
password_bytes = password.encode('utf-8')
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

print(f"Generated hash for '{password}': {hashed}")

# Verify it works
print(f"Verification: {bcrypt.checkpw(password_bytes, hashed.encode('utf-8'))}")

async def reset_admin():
    # Get database URL from config
    try:
        from config import settings
        db_url = settings.DATABASE_URL
    except:
        db_url = "postgresql+asyncpg://qastra:qastra123@localhost:5432/qastra"
    
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
            """), {"email": "admin@qastra.dev", "hash": hashed})
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
    print(f"  Email: {users[0][1] if users else 'admin@qastra.dev'}")
    print(f"  Password: admin123")

if __name__ == "__main__":
    asyncio.run(reset_admin())
