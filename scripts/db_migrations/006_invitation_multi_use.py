#!/usr/bin/env python3
"""
Migration 006: Add multi-use support to Invitation table.

Adds the following fields to existing Invitation table:
- max_usage: Maximum number of times invitation can be used (NULL=one-time, -1=unlimited, N=max)
- usage_count: Track actual number of uses
"""

import sys
import os

# Fix Windows encoding issues
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.db import db
from kohakuhub.config import cfg
from _migration_utils import (
    should_skip_due_to_future_migrations,
    check_column_exists,
    check_table_exists,
)

MIGRATION_NUMBER = 6


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if Invitation.max_usage column exists.
    """
    # First check if invitation table exists
    if not check_table_exists(db, "invitation"):
        # Table doesn't exist, migration not applicable
        return True
    return check_column_exists(db, cfg, "invitation", "max_usage")


def check_migration_needed():
    """Check if this migration needs to run by checking if columns exist."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # First check if invitation table exists
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name='invitation'
        """
        )
        if cursor.fetchone() is None:
            # Table doesn't exist - skip this migration (will be created by 005)
            return False

        # Check if Invitation.max_usage exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='invitation' AND column_name='max_usage'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='invitation'"
        )
        if cursor.fetchone() is None:
            # Table doesn't exist - skip this migration (will be created by 005)
            return False

        # Check via PRAGMA
        cursor.execute("PRAGMA table_info(invitation)")
        columns = [row[1] for row in cursor.fetchall()]
        return "max_usage" not in columns


def migrate_sqlite():
    """Migrate SQLite database."""
    cursor = db.cursor()

    # Invitation multi-use fields
    for column, sql in [
        (
            "max_usage",
            "ALTER TABLE invitation ADD COLUMN max_usage INTEGER DEFAULT NULL",
        ),
        (
            "usage_count",
            "ALTER TABLE invitation ADD COLUMN usage_count INTEGER DEFAULT 0",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added Invitation.{column}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  - Invitation.{column} already exists")
            else:
                raise

    # Migrate existing data: Set usage_count=1 for used invitations
    try:
        cursor.execute(
            """
            UPDATE invitation
            SET usage_count = 1
            WHERE used_at IS NOT NULL AND usage_count = 0
        """
        )
        updated = cursor.rowcount
        if updated > 0:
            print(f"  ✓ Migrated {updated} existing invitation(s) usage data")
    except Exception as e:
        print(f"  - Warning: Could not migrate existing data: {e}")

    db.commit()


def migrate_postgres():
    """Migrate PostgreSQL database."""
    cursor = db.cursor()

    # Invitation multi-use fields
    for column, sql in [
        (
            "max_usage",
            "ALTER TABLE invitation ADD COLUMN max_usage INTEGER DEFAULT NULL",
        ),
        (
            "usage_count",
            "ALTER TABLE invitation ADD COLUMN usage_count INTEGER DEFAULT 0",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added Invitation.{column}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  - Invitation.{column} already exists")
                db.rollback()
            else:
                raise

    # Migrate existing data: Set usage_count=1 for used invitations
    try:
        cursor.execute(
            """
            UPDATE invitation
            SET usage_count = 1
            WHERE used_at IS NOT NULL AND usage_count = 0
        """
        )
        updated = cursor.rowcount
        if updated > 0:
            print(f"  ✓ Migrated {updated} existing invitation(s) usage data")
    except Exception as e:
        print(f"  - Warning: Could not migrate existing data: {e}")
        db.rollback()

    db.commit()


def run():
    """Run this migration."""
    db.connect(reuse_if_open=True)

    try:
        # Check if any future migration has been applied
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 006: Skipped (superseded by future migration)")
            return True

        migration_needed = check_migration_needed()
        if not migration_needed:
            # Check if table exists to provide better message
            cursor = db.cursor()
            if cfg.app.db_backend == "postgres":
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name='invitation'"
                )
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='invitation'"
                )
                table_exists = cursor.fetchone() is not None

            if not table_exists:
                print(
                    "Migration 006: Skipped (invitation table doesn't exist yet, will be created by init_db)"
                )
            else:
                print("Migration 006: Already applied (columns exist)")
            return True

        print("Migration 006: Adding multi-use support to Invitation table...")

        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()

        print("Migration 006: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 006: ✗ Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
