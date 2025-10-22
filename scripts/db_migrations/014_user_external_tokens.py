#!/usr/bin/env python3
"""
Migration 014: Add UserExternalToken table for user-specific external fallback tokens.

Allows users to provide their own tokens for external fallback sources (HuggingFace, etc.).
User tokens override admin-configured tokens for matching URLs.

Changes:
- Add UserExternalToken table with encrypted token storage
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.config import cfg
from kohakuhub.db import UserExternalToken, db
from _migration_utils import check_table_exists, should_skip_due_to_future_migrations

MIGRATION_NUMBER = 14


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if UserExternalToken table exists.
    """
    return check_table_exists(db, "userexternaltoken")


def migrate_postgres():
    """Create UserExternalToken table in PostgreSQL."""
    cursor = db.cursor()

    print("Creating UserExternalToken table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS userexternaltoken (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            url VARCHAR(255) NOT NULL,
            encrypted_token TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, url)
        )
        """
    )
    print("  ✓ Created UserExternalToken table")

    # Create index on user_id for faster lookups
    print("Creating index on user_id...")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS userexternaltoken_user_id
        ON userexternaltoken(user_id)
        """
    )
    print("  ✓ Created index on user_id")


def migrate_sqlite():
    """Create UserExternalToken table in SQLite."""
    cursor = db.cursor()

    print("Creating UserExternalToken table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS userexternaltoken (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            url VARCHAR(255) NOT NULL,
            encrypted_token TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, url)
        )
        """
    )
    print("  ✓ Created UserExternalToken table")

    # Create index on user_id for faster lookups
    print("Creating index on user_id...")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS userexternaltoken_user_id
        ON userexternaltoken(user_id)
        """
    )
    print("  ✓ Created index on user_id")


def run():
    """Run migration 014."""
    print("\n" + "=" * 60)
    print(f"Migration {MIGRATION_NUMBER}: Add UserExternalToken table")
    print("=" * 60)

    # Connect to database
    db.connect(reuse_if_open=True)

    # Check if should skip
    if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
        print(
            f"\n⚠️  Skipping migration {MIGRATION_NUMBER} - already applied or superseded by future migrations\n"
        )
        return

    # Check if already applied
    if is_applied(db, cfg):
        print(
            f"\n✓ Migration {MIGRATION_NUMBER} already applied (UserExternalToken table exists)\n"
        )
        return

    # Run migration in transaction
    print(f"\nApplying migration {MIGRATION_NUMBER}...\n")

    with db.atomic():
        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()

    print(f"\n✓ Migration {MIGRATION_NUMBER} completed successfully!\n")


if __name__ == "__main__":
    run()
