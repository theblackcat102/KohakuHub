#!/usr/bin/env python3
"""
Migration 004: Add storage quota fields to Repository model.

Adds the following fields:
- Repository: quota_bytes, used_bytes
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kohakuhub.db import db, Repository
from kohakuhub.config import cfg


def check_migration_needed():
    """Check if this migration needs to run by checking if columns exist."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # Check if Repository.quota_bytes exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='repository' AND column_name='quota_bytes'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check via PRAGMA
        cursor.execute("PRAGMA table_info(repository)")
        columns = [row[1] for row in cursor.fetchall()]
        return "quota_bytes" not in columns


def migrate_sqlite():
    """Migrate SQLite database."""
    cursor = db.cursor()

    for column, sql in [
        (
            "quota_bytes",
            "ALTER TABLE repository ADD COLUMN quota_bytes INTEGER DEFAULT NULL",
        ),
        (
            "used_bytes",
            "ALTER TABLE repository ADD COLUMN used_bytes INTEGER DEFAULT 0",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added Repository.{column}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  - Repository.{column} already exists")
            else:
                raise

    db.commit()


def migrate_postgres():
    """Migrate PostgreSQL database."""
    cursor = db.cursor()

    for column, sql in [
        (
            "quota_bytes",
            "ALTER TABLE repository ADD COLUMN quota_bytes BIGINT DEFAULT NULL",
        ),
        ("used_bytes", "ALTER TABLE repository ADD COLUMN used_bytes BIGINT DEFAULT 0"),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added Repository.{column}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  - Repository.{column} already exists")
                db.rollback()
            else:
                raise

    db.commit()


def run():
    """Run this migration."""
    db.connect(reuse_if_open=True)

    try:
        if not check_migration_needed():
            print("Migration 004: Already applied (columns exist)")
            return True

        print("Migration 004: Adding Repository quota fields...")

        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()

        print("Migration 004: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 004: ✗ Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
