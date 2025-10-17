#!/usr/bin/env python3
"""
Migration 003: Add Commit table for tracking user commits.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.db import db
from kohakuhub.config import cfg
from _migration_utils import should_skip_due_to_future_migrations, check_table_exists

MIGRATION_NUMBER = 3


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if Commit table exists.
    """
    return check_table_exists(db, "commit")


def check_migration_needed():
    """Check if Commit table exists."""
    return not db.table_exists("commit")


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
            print("Migration 003: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 003: Already applied (Commit table exists)")
            return True

        print("Migration 003: Creating Commit table...")

        # Run migration in a transaction - will auto-rollback on exception
        with db.atomic():
            cursor = db.cursor()
            if cfg.app.db_backend == "postgres":
                # PostgreSQL: Create Commit table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS commit (
                        id SERIAL PRIMARY KEY,
                        commit_id VARCHAR(255) NOT NULL,
                        repo_full_id VARCHAR(255) NOT NULL,
                        author_id INTEGER NOT NULL,
                        message TEXT,
                        created_at TIMESTAMP NOT NULL
                    )
                """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS commit_commit_id ON commit(commit_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS commit_repo_full_id ON commit(repo_full_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS commit_author_id ON commit(author_id)"
                )
            else:
                # SQLite: Create Commit table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS commit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commit_id VARCHAR(255) NOT NULL,
                        repo_full_id VARCHAR(255) NOT NULL,
                        author_id INTEGER NOT NULL,
                        message TEXT,
                        created_at DATETIME NOT NULL
                    )
                """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS commit_commit_id ON commit(commit_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS commit_repo_full_id ON commit(repo_full_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS commit_author_id ON commit(author_id)"
                )

        print("Migration 003: ✓ Completed")
        return True

    except Exception as e:
        # Transaction automatically rolled back if we reach here
        print(f"Migration 003: ✗ Failed - {e}")
        print("  All changes have been rolled back")
        import traceback

        traceback.print_exc()
        return False
    # NOTE: No finally block - db connection stays open


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
