#!/usr/bin/env python3
"""
Migration 002: Add storage quota fields to User and Organization models.

Adds the following fields:
- User: private_quota_bytes, public_quota_bytes, private_used_bytes, public_used_bytes
- Organization: private_quota_bytes, public_quota_bytes, private_used_bytes, public_used_bytes
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kohakuhub.db import db, User, Organization
from kohakuhub.config import cfg


def check_migration_needed():
    """Check if this migration needs to run by checking if columns exist."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # Check if User.private_quota_bytes exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='user' AND column_name='private_quota_bytes'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check via PRAGMA
        cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in cursor.fetchall()]
        return "private_quota_bytes" not in columns


def migrate_sqlite():
    """Migrate SQLite database."""
    cursor = db.cursor()

    # User table
    for column, sql in [
        (
            "private_quota_bytes",
            "ALTER TABLE user ADD COLUMN private_quota_bytes INTEGER DEFAULT NULL",
        ),
        (
            "public_quota_bytes",
            "ALTER TABLE user ADD COLUMN public_quota_bytes INTEGER DEFAULT NULL",
        ),
        (
            "private_used_bytes",
            "ALTER TABLE user ADD COLUMN private_used_bytes INTEGER DEFAULT 0",
        ),
        (
            "public_used_bytes",
            "ALTER TABLE user ADD COLUMN public_used_bytes INTEGER DEFAULT 0",
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

    # Organization table
    for column, sql in [
        (
            "private_quota_bytes",
            "ALTER TABLE organization ADD COLUMN private_quota_bytes INTEGER DEFAULT NULL",
        ),
        (
            "public_quota_bytes",
            "ALTER TABLE organization ADD COLUMN public_quota_bytes INTEGER DEFAULT NULL",
        ),
        (
            "private_used_bytes",
            "ALTER TABLE organization ADD COLUMN private_used_bytes INTEGER DEFAULT 0",
        ),
        (
            "public_used_bytes",
            "ALTER TABLE organization ADD COLUMN public_used_bytes INTEGER DEFAULT 0",
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

    # User table
    for column, sql in [
        (
            "private_quota_bytes",
            'ALTER TABLE "user" ADD COLUMN private_quota_bytes BIGINT DEFAULT NULL',
        ),
        (
            "public_quota_bytes",
            'ALTER TABLE "user" ADD COLUMN public_quota_bytes BIGINT DEFAULT NULL',
        ),
        (
            "private_used_bytes",
            'ALTER TABLE "user" ADD COLUMN private_used_bytes BIGINT DEFAULT 0',
        ),
        (
            "public_used_bytes",
            'ALTER TABLE "user" ADD COLUMN public_used_bytes BIGINT DEFAULT 0',
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

    # Organization table
    for column, sql in [
        (
            "private_quota_bytes",
            "ALTER TABLE organization ADD COLUMN private_quota_bytes BIGINT DEFAULT NULL",
        ),
        (
            "public_quota_bytes",
            "ALTER TABLE organization ADD COLUMN public_quota_bytes BIGINT DEFAULT NULL",
        ),
        (
            "private_used_bytes",
            "ALTER TABLE organization ADD COLUMN private_used_bytes BIGINT DEFAULT 0",
        ),
        (
            "public_used_bytes",
            "ALTER TABLE organization ADD COLUMN public_used_bytes BIGINT DEFAULT 0",
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
            print("Migration 002: Already applied (columns exist)")
            return True

        print("Migration 002: Adding User/Organization quota fields...")

        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()

        print("Migration 002: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 002: ✗ Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
