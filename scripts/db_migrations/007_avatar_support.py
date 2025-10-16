#!/usr/bin/env python3
"""
Migration 007: Add avatar support to User and Organization tables.

Adds the following fields:
- User: avatar (BLOB), avatar_updated_at (DATETIME)
- Organization: avatar (BLOB), avatar_updated_at (DATETIME)
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
from _migration_utils import should_skip_due_to_future_migrations, check_column_exists

MIGRATION_NUMBER = 7


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if User.avatar column exists.
    """
    return check_column_exists(db, cfg, "user", "avatar")


def check_migration_needed():
    """Check if this migration needs to run.

    Returns True only if:
    - User table exists (schema version > 0)
    - AND User.avatar doesn't exist (schema version < 7)

    Returns False if:
    - User table doesn't exist (fresh install, version 0, will be created by init_db)
    - OR User.avatar exists (already at version 7+)
    """
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # First check if user table exists
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name='user'
        """
        )
        if cursor.fetchone() is None:
            # Fresh database, tables will be created by init_db() with final schema
            return False

        # Table exists, check if avatar column exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='user' AND column_name='avatar'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: First check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user'"
        )
        if cursor.fetchone() is None:
            # Fresh database, tables will be created by init_db() with final schema
            return False

        # Table exists, check via PRAGMA if avatar column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in cursor.fetchall()]
        return "avatar" not in columns


def migrate_sqlite():
    """Migrate SQLite database."""
    cursor = db.cursor()

    # User avatar fields
    for column, sql in [
        ("avatar", "ALTER TABLE user ADD COLUMN avatar BLOB DEFAULT NULL"),
        (
            "avatar_updated_at",
            "ALTER TABLE user ADD COLUMN avatar_updated_at DATETIME DEFAULT NULL",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added User.{column}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  - User.{column} already exists")
            else:
                raise

    # Organization avatar fields
    for column, sql in [
        ("avatar", "ALTER TABLE organization ADD COLUMN avatar BLOB DEFAULT NULL"),
        (
            "avatar_updated_at",
            "ALTER TABLE organization ADD COLUMN avatar_updated_at DATETIME DEFAULT NULL",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added Organization.{column}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  - Organization.{column} already exists")
            else:
                raise

    db.commit()


def migrate_postgres():
    """Migrate PostgreSQL database."""
    cursor = db.cursor()

    # User avatar fields
    for column, sql in [
        ("avatar", 'ALTER TABLE "user" ADD COLUMN avatar BYTEA DEFAULT NULL'),
        (
            "avatar_updated_at",
            'ALTER TABLE "user" ADD COLUMN avatar_updated_at TIMESTAMP DEFAULT NULL',
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added User.{column}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  - User.{column} already exists")
                db.rollback()
            else:
                raise

    # Organization avatar fields
    for column, sql in [
        ("avatar", "ALTER TABLE organization ADD COLUMN avatar BYTEA DEFAULT NULL"),
        (
            "avatar_updated_at",
            "ALTER TABLE organization ADD COLUMN avatar_updated_at TIMESTAMP DEFAULT NULL",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added Organization.{column}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  - Organization.{column} already exists")
                db.rollback()
            else:
                raise

    db.commit()


def run():
    """Run this migration."""
    db.connect(reuse_if_open=True)

    try:
        # Check if any future migration has been applied
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 007: Skipped (superseded by future migration)")
            return True

        migration_needed = check_migration_needed()
        if not migration_needed:
            # Check if table exists to provide better message
            cursor = db.cursor()
            if cfg.app.db_backend == "postgres":
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name='user'"
                )
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='user'"
                )
                table_exists = cursor.fetchone() is not None

            if not table_exists:
                print(
                    "Migration 007: Skipped (user table doesn't exist yet, will be created by init_db)"
                )
            else:
                print("Migration 007: Already applied (columns exist)")
            return True

        print("Migration 007: Adding avatar support to User and Organization tables...")

        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()

        print("Migration 007: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 007: ✗ Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
