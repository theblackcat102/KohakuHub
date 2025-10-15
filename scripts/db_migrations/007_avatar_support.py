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

from kohakuhub.db import db
from kohakuhub.config import cfg


def check_migration_needed():
    """Check if this migration needs to run by checking if columns exist."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # Check if User.avatar exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='user' AND column_name='avatar'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check via PRAGMA
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
        if not check_migration_needed():
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
