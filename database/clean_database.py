#!/usr/bin/env python3
"""
QAstra Database Cleanup Script

Drops ALL database objects (tables, sequences, functions, triggers, types, etc.)
from the 'qastra' database. Requires superuser credentials.

Usage:
    python database_clean.py
"""

import getpass
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))


def get_credentials() -> tuple[str, str]:
    """Prompt for PostgreSQL superuser credentials."""
    print("=" * 50)
    print("  QAstra Database Cleanup")
    print("=" * 50)
    print()
    print(f"This will DROP all objects in the '{DB_NAME}' database.")
    print("You need PostgreSQL superuser credentials.")
    print()
    username = input("PostgreSQL superuser username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        sys.exit(1)
    password = getpass.getpass("PostgreSQL superuser password: ")
    return username, password


def clean_database(username: str, password: str) -> None:
    """Drop all database objects from the qastra database."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=username,
            password=password,
        )
        conn.autocommit = True
        cur = conn.cursor()

        print()
        print(f"Connected to '{DB_NAME}' database.")
        print("Dropping all objects...")
        print()

        # 1. Drop all triggers
        cur.execute("""
            SELECT trigger_name, event_object_table
            FROM information_schema.triggers
            WHERE trigger_schema = 'public';
        """)
        triggers = cur.fetchall()
        for trigger_name, table_name in triggers:
            stmt = f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table_name}" CASCADE;'
            print(f"  Dropping trigger: {trigger_name} on {table_name}")
            cur.execute(stmt)

        # 2. Drop all views
        cur.execute("""
            SELECT table_name FROM information_schema.views
            WHERE table_schema = 'public';
        """)
        for (view_name,) in cur.fetchall():
            stmt = f'DROP VIEW IF EXISTS "{view_name}" CASCADE;'
            print(f"  Dropping view: {view_name}")
            cur.execute(stmt)

        # 3. Drop all tables
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public';
        """)
        tables = cur.fetchall()
        if tables:
            table_list = ", ".join(f'"{t[0]}"' for t in tables)
            print(f"  Dropping tables: {', '.join(t[0] for t in tables)}")
            cur.execute(f"DROP TABLE IF EXISTS {table_list} CASCADE;")

        # 4. Drop all sequences
        cur.execute("""
            SELECT sequence_name FROM information_schema.sequences
            WHERE sequence_schema = 'public';
        """)
        for (seq_name,) in cur.fetchall():
            stmt = f'DROP SEQUENCE IF EXISTS "{seq_name}" CASCADE;'
            print(f"  Dropping sequence: {seq_name}")
            cur.execute(stmt)

        # 5. Drop all functions and procedures
        cur.execute("""
            SELECT routines.routine_name, routines.routine_type,
                   pg_get_function_identity_arguments(p.oid) AS args
            FROM information_schema.routines
            JOIN pg_proc p ON p.proname = routines.routine_name
            JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public'
            WHERE routines.routine_schema = 'public';
        """)
        for routine_name, routine_type, args in cur.fetchall():
            kind = "FUNCTION" if routine_type == "FUNCTION" else "PROCEDURE"
            stmt = f'DROP {kind} IF EXISTS "{routine_name}"({args}) CASCADE;'
            print(f"  Dropping {kind.lower()}: {routine_name}({args})")
            cur.execute(stmt)

        # 6. Drop all custom types (enums, composites, etc.)
        cur.execute("""
            SELECT t.typname
            FROM pg_type t
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = 'public'
              AND t.typtype IN ('e', 'c')
              AND t.typname NOT LIKE E'\\_%%';
        """)
        for (type_name,) in cur.fetchall():
            stmt = f'DROP TYPE IF EXISTS "{type_name}" CASCADE;'
            print(f"  Dropping type: {type_name}")
            cur.execute(stmt)

        # 7. Drop all extensions in public schema (optional, usually skip)
        # Not dropping extensions as they are typically shared

        cur.close()
        print()
        print("All database objects dropped successfully!")
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


def main() -> None:
    username, password = get_credentials()

    confirm = input(f"\nAre you sure you want to DROP ALL objects in '{DB_NAME}'? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    clean_database(username, password)


if __name__ == "__main__":
    main()
