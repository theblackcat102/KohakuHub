#!/usr/bin/env python3
"""
Migration 009: Add LFS settings fields to Repository model.

Adds the following fields to allow per-repository LFS configuration:
- Repository: lfs_threshold_bytes (NULL = use server default)
- Repository: lfs_keep_versions (NULL = use server default)
- Repository: lfs_suffix_rules (NULL = no suffix rules)
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.db import db
from kohakuhub.config import cfg
from _migration_utils import should_skip_due_to_future_migrations, check_column_exists

MIGRATION_NUMBER = 9


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if Repository.lfs_threshold_bytes column exists.
    """
    return check_column_exists(db, cfg, "repository", "lfs_threshold_bytes")


def check_migration_needed():
    """Check if this migration needs to run by checking if columns exist."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # Check if Repository.lfs_threshold_bytes exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='repository' AND column_name='lfs_threshold_bytes'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check via PRAGMA
        cursor.execute("PRAGMA table_info(repository)")
        columns = [row[1] for row in cursor.fetchall()]
        return "lfs_threshold_bytes" not in columns


def migrate_sqlite():
    """Migrate SQLite database.

    Note: This function runs inside a transaction (db.atomic()).
    Do NOT call db.commit() or db.rollback() inside this function.
    """
    cursor = db.cursor()

    for column, sql in [
        (
            "lfs_threshold_bytes",
            "ALTER TABLE repository ADD COLUMN lfs_threshold_bytes INTEGER DEFAULT NULL",
        ),
        (
            "lfs_keep_versions",
            "ALTER TABLE repository ADD COLUMN lfs_keep_versions INTEGER DEFAULT NULL",
        ),
        (
            "lfs_suffix_rules",
            "ALTER TABLE repository ADD COLUMN lfs_suffix_rules TEXT DEFAULT NULL",
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


def migrate_postgres():
    """Migrate PostgreSQL database.

    Note: This function runs inside a transaction (db.atomic()).
    Do NOT call db.commit() or db.rollback() inside this function.
    """
    cursor = db.cursor()

    for column, sql in [
        (
            "lfs_threshold_bytes",
            "ALTER TABLE repository ADD COLUMN lfs_threshold_bytes INTEGER DEFAULT NULL",
        ),
        (
            "lfs_keep_versions",
            "ALTER TABLE repository ADD COLUMN lfs_keep_versions INTEGER DEFAULT NULL",
        ),
        (
            "lfs_suffix_rules",
            "ALTER TABLE repository ADD COLUMN lfs_suffix_rules TEXT DEFAULT NULL",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  ✓ Added Repository.{column}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  - Repository.{column} already exists")
                # Don't need to rollback - the exception will propagate and rollback the entire transaction
            else:
                raise


def run():
    """Run this migration.

    IMPORTANT: Do NOT call db.close() in finally block!
    The db connection is managed by run_migrations.py and should stay open
    across all migrations to avoid stdout/stderr closure issues on Windows.
    """
    db.connect(reuse_if_open=True)

    try:
        # Pre-flight checks (outside transaction for performance)
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 009: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 009: Already applied (columns exist)")
            return True

        print("Migration 009: Adding Repository LFS settings fields...")

        # Run migration in a transaction - will auto-rollback on exception
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                migrate_postgres()
            else:
                migrate_sqlite()

        print("Migration 009: ✓ Completed")
        return True

    except Exception as e:
        # Transaction automatically rolled back if we reach here
        print(f"Migration 009: ✗ Failed - {e}")
        print("  All changes have been rolled back")
        import traceback

        traceback.print_exc()
        return False
    # NOTE: No finally block - db connection stays open


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
