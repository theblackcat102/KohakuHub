#!/usr/bin/env python3
"""
Migration 005: Add profile fields and invitation system.

Adds the following:
- User: full_name, bio, website, social_media (profile fields)
- Organization: bio, website, social_media (profile fields)
- Invitation table (generic invitation system for org invites, etc.)
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
    """Check if this migration needs to run by checking if columns/tables exist."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # Check if User.full_name exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='user' AND column_name='full_name'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check via PRAGMA
        cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in cursor.fetchall()]
        return "full_name" not in columns


def migrate_sqlite():
    """Migrate SQLite database."""
    cursor = db.cursor()

    # User profile fields
    for column, sql in [
        (
            "full_name",
            "ALTER TABLE user ADD COLUMN full_name VARCHAR(255) DEFAULT NULL",
        ),
        ("bio", "ALTER TABLE user ADD COLUMN bio TEXT DEFAULT NULL"),
        ("website", "ALTER TABLE user ADD COLUMN website VARCHAR(255) DEFAULT NULL"),
        ("social_media", "ALTER TABLE user ADD COLUMN social_media TEXT DEFAULT NULL"),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added User.{column}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  - User.{column} already exists")
            else:
                raise

    # Organization profile fields
    for column, sql in [
        ("bio", "ALTER TABLE organization ADD COLUMN bio TEXT DEFAULT NULL"),
        (
            "website",
            "ALTER TABLE organization ADD COLUMN website VARCHAR(255) DEFAULT NULL",
        ),
        (
            "social_media",
            "ALTER TABLE organization ADD COLUMN social_media TEXT DEFAULT NULL",
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

    # Create Invitation table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS invitation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token VARCHAR(255) UNIQUE NOT NULL,
                action VARCHAR(255) NOT NULL,
                parameters TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                expires_at DATETIME NOT NULL,
                max_usage INTEGER DEFAULT NULL,
                usage_count INTEGER DEFAULT 0,
                used_at DATETIME DEFAULT NULL,
                used_by INTEGER DEFAULT NULL,
                created_at DATETIME NOT NULL
            )
        """
        )
        print("  ✓ Created Invitation table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_token ON invitation(token)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_action ON invitation(action)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_created_by ON invitation(created_by)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_action_created_by ON invitation(action, created_by)"
        )
        print("  ✓ Created Invitation indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - Invitation table already exists")
        else:
            raise

    db.commit()


def migrate_postgres():
    """Migrate PostgreSQL database."""
    cursor = db.cursor()

    # User profile fields
    for column, sql in [
        (
            "full_name",
            'ALTER TABLE "user" ADD COLUMN full_name VARCHAR(255) DEFAULT NULL',
        ),
        ("bio", 'ALTER TABLE "user" ADD COLUMN bio TEXT DEFAULT NULL'),
        ("website", 'ALTER TABLE "user" ADD COLUMN website VARCHAR(255) DEFAULT NULL'),
        (
            "social_media",
            'ALTER TABLE "user" ADD COLUMN social_media TEXT DEFAULT NULL',
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

    # Organization profile fields
    for column, sql in [
        ("bio", "ALTER TABLE organization ADD COLUMN bio TEXT DEFAULT NULL"),
        (
            "website",
            "ALTER TABLE organization ADD COLUMN website VARCHAR(255) DEFAULT NULL",
        ),
        (
            "social_media",
            "ALTER TABLE organization ADD COLUMN social_media TEXT DEFAULT NULL",
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

    # Create Invitation table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS invitation (
                id SERIAL PRIMARY KEY,
                token VARCHAR(255) UNIQUE NOT NULL,
                action VARCHAR(255) NOT NULL,
                parameters TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                max_usage INTEGER DEFAULT NULL,
                usage_count INTEGER DEFAULT 0,
                used_at TIMESTAMP DEFAULT NULL,
                used_by INTEGER DEFAULT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """
        )
        print("  ✓ Created Invitation table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_token ON invitation(token)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_action ON invitation(action)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_created_by ON invitation(created_by)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS invitation_action_created_by ON invitation(action, created_by)"
        )
        print("  ✓ Created Invitation indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - Invitation table already exists")
            db.rollback()
        else:
            raise

    db.commit()


def run():
    """Run this migration."""
    db.connect(reuse_if_open=True)

    try:
        if not check_migration_needed():
            print("Migration 005: Already applied (columns exist)")
            return True

        print("Migration 005: Adding profile fields and invitation system...")

        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()

        print("Migration 005: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 005: ✗ Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
