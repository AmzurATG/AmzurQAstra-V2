#!/usr/bin/env python3
"""
QAstra Admin User Setup Script

Creates the default admin user in the database. Reads DATABASE_URL from
the backend/.env file and generates a fresh bcrypt hash at runtime.

Usage:
    python create_admin.py

Run this after 'alembic upgrade head' to create the initial admin user.
"""

import getpass
import os
import sys
from pathlib import Path

import bcrypt
import psycopg2


def load_env() -> dict:
    """Load key=value pairs from backend/.env file."""
    env_file = Path(__file__).resolve().parent.parent / "backend" / ".env"
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    return env_vars


def parse_database_url(url: str) -> dict:
    """Parse a PostgreSQL URL into connection parameters."""
    # Remove driver prefix variations
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgresql+psycopg2://", "postgresql://")

    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": (parsed.path or "/qastra").lstrip("/"),
        "user": parsed.username or "qastra",
        "password": parsed.password or "qastra123",
    }


def create_admin() -> None:
    """Create the admin user with a fresh bcrypt hash."""
    print()
    print("=" * 50)
    print("  QAstra Admin User Setup")
    print("=" * 50)
    print()

    # Load .env
    env_vars = load_env()
    db_url = env_vars.get("DATABASE_URL", "postgresql://qastra:qastra123@localhost:5432/qastra")
    db_params = parse_database_url(db_url)

    # Collect admin details
    email = input("  Admin email [admin@qastra.dev]: ").strip() or "admin@qastra.dev"
    full_name = input("  Admin full name [QAstra Admin]: ").strip() or "QAstra Admin"
    password = getpass.getpass("  Admin password [admin123]: ") or "admin123"

    # Generate bcrypt hash
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        cur = conn.cursor()

        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
        existing = cur.fetchone()

        if existing:
            update = input(f"\n  User '{email}' already exists. Update password? (yes/no) [no]: ").strip().lower()
            if update == "yes":
                cur.execute(
                    "UPDATE users SET hashed_password = %s, full_name = %s WHERE email = %s;",
                    (hashed, full_name, email),
                )
                print(f"\n  Password updated for '{email}'.")
            else:
                print("\n  Skipped — no changes made.")
        else:
            cur.execute(
                """INSERT INTO users (email, hashed_password, full_name, role, is_active, is_superuser)
                   VALUES (%s, %s, %s, 'admin', TRUE, TRUE);""",
                (email, hashed, full_name),
            )
            print(f"\n  Admin user '{email}' created.")

        cur.close()
        print()
        print("  Login with:")
        print(f"    Email:    {email}")
        print(f"    Password: {'*' * len(password)}")
        print()

    except psycopg2.OperationalError as e:
        print(f"\nError: Could not connect to database.\n{e}")
        sys.exit(1)
    except psycopg2.Error as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_admin()
