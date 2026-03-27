#!/usr/bin/env python3
"""
QAstra Local Database Setup Script

Creates the 'qastra' database, the 'qastra' application user, and grants
the required privileges. Requires PostgreSQL superuser credentials.

Usage:
    python database_setup_local.py
"""

import getpass
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# Application database / user defaults
APP_DB = "qastra"
APP_USER = "qastra"
APP_PASSWORD = "qastra123"


def get_credentials() -> tuple[str, str]:
    """Prompt for PostgreSQL superuser credentials."""
    print("=" * 50)
    print("  QAstra Local Database Setup")
    print("=" * 50)
    print()
    print("This will create the database, app user, and grant privileges.")
    print("You need PostgreSQL superuser credentials (e.g. 'postgres').")
    print()
    username = input("PostgreSQL superuser username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        sys.exit(1)
    password = getpass.getpass("PostgreSQL superuser password: ")
    return username, password


def setup_database(su_user: str, su_password: str) -> None:
    """Create database, application user, and grant privileges."""
    conn = None
    try:
        # Connect to the default 'postgres' database as superuser
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="postgres",
            user=su_user,
            password=su_password,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print()
        print("Connected to PostgreSQL as superuser.")
        print()

        # 1. Create application role if it doesn't exist
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", (APP_USER,))
        if cur.fetchone() is None:
            cur.execute(
                f"CREATE ROLE {APP_USER} WITH LOGIN PASSWORD %s;",
                (APP_PASSWORD,),
            )
            print(f"  Created role '{APP_USER}' with password '{APP_PASSWORD}'.")
        else:
            print(f"  Role '{APP_USER}' already exists — skipping.")

        # 2. Create application database if it doesn't exist
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (APP_DB,))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{APP_DB}" OWNER {APP_USER};')
            print(f"  Created database '{APP_DB}' with owner '{APP_USER}'.")
        else:
            print(f"  Database '{APP_DB}' already exists — skipping.")

        # 3. Grant privileges
        cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {APP_DB} TO {APP_USER};")
        print(f"  Granted ALL PRIVILEGES on '{APP_DB}' to '{APP_USER}'.")

        cur.close()
        conn.close()

        # 4. Connect to the new database and grant schema privileges
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname=APP_DB,
            user=su_user,
            password=su_password,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute(f"GRANT ALL ON SCHEMA public TO {APP_USER};")
        cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {APP_USER};")
        cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {APP_USER};")
        cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO {APP_USER};")
        print(f"  Granted schema-level privileges to '{APP_USER}'.")

        cur.close()
        print()
        print("=" * 50)
        print("  Setup complete!")
        print("=" * 50)
        print()
        print("Next steps:")
        print(f"  1. Run Alembic migrations:  cd backend && alembic upgrade head")
        print(f"  2. Or apply SQL manually:   psql -U {APP_USER} -d {APP_DB} -f create_db.sql")
        print()

    except psycopg2.OperationalError as e:
        print(f"\nError: Could not connect to PostgreSQL.\n{e}")
        sys.exit(1)
    except psycopg2.Error as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


def main() -> None:
    su_user, su_password = get_credentials()
    setup_database(su_user, su_password)


if __name__ == "__main__":
    main()
