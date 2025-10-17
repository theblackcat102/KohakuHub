#!/usr/bin/env python3
"""
Migration 011: Add soft delete support for File model.

Changes:
1. Add File.is_deleted column (default FALSE)
2. Change LFSObjectHistory.file FK: on_delete CASCADE → SET NULL

This allows:
- File deletion to mark as deleted instead of removing from database
- LFSObjectHistory to persist for quota tracking even after file deletion
- Only squash/move/delete repo will actually delete File entries
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.config import cfg
from kohakuhub.db import db
from _migration_utils import check_column_exists, should_skip_due_to_future_migrations

MIGRATION_NUMBER = 11


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if File.is_deleted column exists.
    """
    return check_column_exists(db, cfg, "file", "is_deleted")


def check_migration_needed():
    """Check if this migration needs to run by checking if column exists."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # Check if File.is_deleted exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='file' AND column_name='is_deleted'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check via PRAGMA
        cursor.execute("PRAGMA table_info(file)")
        columns = [row[1] for row in cursor.fetchall()]
        return "is_deleted" not in columns


def migrate_sqlite():
    """Migrate SQLite database.

    Note: This function runs inside a transaction (db.atomic()).
    Do NOT call db.commit() or db.rollback() inside this function.
    """
    cursor = db.cursor()

    # Step 1: Add is_deleted column to File table
    try:
        cursor.execute(
            "ALTER TABLE file ADD COLUMN is_deleted INTEGER DEFAULT 0 NOT NULL"
        )
        print("  [OK] Added File.is_deleted column")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  - File.is_deleted already exists")
        else:
            raise

    # Step 2: Update LFSObjectHistory FK constraint (CASCADE -> SET NULL)
    # SQLite doesn't support ALTER COLUMN for FK, so we need to:
    # 1. Create new table with correct FK
    # 2. Copy data
    # 3. Drop old table
    # 4. Rename new table

    print("  [INFO] Updating LFSObjectHistory.file FK constraint...")

    # Check if lfsobjecthistory_new exists from a previous failed migration
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='lfsobjecthistory_new'"
    )
    if cursor.fetchone():
        cursor.execute("DROP TABLE lfsobjecthistory_new")
        print("    - Dropped stale lfsobjecthistory_new table")

    # Create new table with SET NULL constraint
    cursor.execute(
        """
        CREATE TABLE lfsobjecthistory_new (
            id INTEGER NOT NULL PRIMARY KEY,
            repository_id INTEGER NOT NULL,
            path_in_repo VARCHAR(255) NOT NULL,
            sha256 VARCHAR(255) NOT NULL,
            size INTEGER NOT NULL,
            commit_id VARCHAR(255) NOT NULL,
            file_id INTEGER,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repository (id) ON DELETE CASCADE,
            FOREIGN KEY (file_id) REFERENCES file (id) ON DELETE SET NULL
        )
    """
    )
    print("    [OK] Created lfsobjecthistory_new table with SET NULL constraint")

    # Copy data
    cursor.execute(
        """
        INSERT INTO lfsobjecthistory_new (id, repository_id, path_in_repo, sha256, size, commit_id, file_id, created_at)
        SELECT id, repository_id, path_in_repo, sha256, size, commit_id, file_id, created_at
        FROM lfsobjecthistory
    """
    )
    rows_copied = cursor.rowcount
    print(f"    [OK] Copied {rows_copied} rows to new table")

    # Drop old table
    cursor.execute("DROP TABLE lfsobjecthistory")
    print("    [OK] Dropped old lfsobjecthistory table")

    # Rename new table
    cursor.execute("ALTER TABLE lfsobjecthistory_new RENAME TO lfsobjecthistory")
    print("    [OK] Renamed lfsobjecthistory_new -> lfsobjecthistory")

    # Recreate indexes
    cursor.execute(
        "CREATE INDEX lfsobjecthistory_repository_id ON lfsobjecthistory (repository_id)"
    )
    cursor.execute(
        "CREATE INDEX lfsobjecthistory_file_id ON lfsobjecthistory (file_id)"
    )
    cursor.execute(
        "CREATE INDEX lfsobjecthistory_commit_id ON lfsobjecthistory (commit_id)"
    )
    cursor.execute("CREATE INDEX lfsobjecthistory_sha256 ON lfsobjecthistory (sha256)")
    cursor.execute(
        "CREATE INDEX lfsobjecthistory_path_in_repo ON lfsobjecthistory (path_in_repo)"
    )
    cursor.execute(
        "CREATE INDEX lfsobjecthistory_repository_id_path_in_repo ON lfsobjecthistory (repository_id, path_in_repo)"
    )
    print("    [OK] Recreated indexes on lfsobjecthistory")


def migrate_postgres():
    """Migrate PostgreSQL database.

    Note: This function runs inside a transaction (db.atomic()).
    Do NOT call db.commit() or db.rollback() inside this function.
    """
    cursor = db.cursor()

    # Step 1: Add is_deleted column to File table
    try:
        cursor.execute(
            "ALTER TABLE file ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL"
        )
        print("  [OK] Added File.is_deleted column")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - File.is_deleted already exists")
        else:
            raise

    # Step 2: Update LFSObjectHistory FK constraint (CASCADE -> SET NULL)
    print("  [INFO] Updating LFSObjectHistory.file FK constraint...")

    try:
        # Drop existing FK constraint
        cursor.execute(
            """
            ALTER TABLE lfsobjecthistory
            DROP CONSTRAINT IF EXISTS lfsobjecthistory_file_id_fkey
        """
        )
        print("    [OK] Dropped old FK constraint")

        # Add new FK constraint with SET NULL
        cursor.execute(
            """
            ALTER TABLE lfsobjecthistory
            ADD CONSTRAINT lfsobjecthistory_file_id_fkey
            FOREIGN KEY (file_id) REFERENCES file (id) ON DELETE SET NULL
        """
        )
        print("    [OK] Added new FK constraint with ON DELETE SET NULL")

    except Exception as e:
        if "does not exist" in str(e).lower():
            print("    - FK constraint already correct or doesn't need updating")
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
            print("Migration 011: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 011: Already applied (File.is_deleted exists)")
            return True

        print("Migration 011: Adding File soft delete support...")

        # Run migration in a transaction - will auto-rollback on exception
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                migrate_postgres()
            else:
                migrate_sqlite()

        print("Migration 011: [DONE] Completed")
        return True

    except Exception as e:
        # Transaction automatically rolled back if we reach here
        print(f"Migration 011: [FAILED] {e}")
        print("  All changes have been rolled back")
        import traceback

        traceback.print_exc()
        return False
    # NOTE: No finally block - db connection stays open


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
