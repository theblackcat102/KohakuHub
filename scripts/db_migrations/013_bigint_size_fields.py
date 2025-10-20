#!/usr/bin/env python3
"""
Migration 013: Change size fields from INTEGER to BIGINT.

This fixes the "integer out of range" error when uploading large files (>2GB).
PostgreSQL INTEGER is limited to 2,147,483,647 (~2.1GB), but LFS files
can be much larger.

Changes:
- File.size: INTEGER → BIGINT
- StagingUpload.size: INTEGER → BIGINT
- LFSObjectHistory.size: INTEGER → BIGINT
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.db import db
from kohakuhub.config import cfg
from _migration_utils import should_skip_due_to_future_migrations, check_table_exists

MIGRATION_NUMBER = 13


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if all size columns are already BIGINT.
    """
    try:
        cursor = db.cursor()
        if cfg.app.db_backend == "postgres":
            # Check File.size
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name='file' AND column_name='size'
                """
            )
            result = cursor.fetchone()
            if not result or result[0] != "bigint":
                return False

            # Check StagingUpload.size
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name='stagingupload' AND column_name='size'
                """
            )
            result = cursor.fetchone()
            if not result or result[0] != "bigint":
                return False

            # Check LFSObjectHistory.size
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name='lfsobjecthistory' AND column_name='size'
                """
            )
            result = cursor.fetchone()
            if not result or result[0] != "bigint":
                return False

            return True
        else:
            # SQLite uses INTEGER for both int and bigint, no distinction needed
            # SQLite INTEGER can store up to 8 bytes (64-bit), so no migration needed
            return True
    except Exception:
        # Error = treat as applied (safe fallback)
        return True


def migrate_postgres():
    """Change size fields to BIGINT in PostgreSQL."""
    cursor = db.cursor()

    print("Changing size fields from INTEGER to BIGINT...")

    # File.size
    print("  1. File.size...")
    try:
        cursor.execute("ALTER TABLE file ALTER COLUMN size TYPE BIGINT")
        print("    ✓ Changed File.size to BIGINT")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print(f"    - Table/column doesn't exist: {e}")
        else:
            raise

    # StagingUpload.size
    print("  2. StagingUpload.size...")
    try:
        cursor.execute("ALTER TABLE stagingupload ALTER COLUMN size TYPE BIGINT")
        print("    ✓ Changed StagingUpload.size to BIGINT")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print(f"    - Table/column doesn't exist: {e}")
        else:
            raise

    # LFSObjectHistory.size
    print("  3. LFSObjectHistory.size...")
    try:
        cursor.execute("ALTER TABLE lfsobjecthistory ALTER COLUMN size TYPE BIGINT")
        print("    ✓ Changed LFSObjectHistory.size to BIGINT")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print(f"    - Table/column doesn't exist: {e}")
        else:
            raise

    return True


def migrate_sqlite():
    """No migration needed for SQLite.

    SQLite INTEGER can store up to 8 bytes (64-bit signed), which is
    equivalent to BIGINT. No schema change is needed.
    """
    print("SQLite migration not needed:")
    print("  SQLite INTEGER already supports 64-bit values (same as BIGINT)")
    print(
        "  ✓ All size fields can already store values up to 9,223,372,036,854,775,807"
    )
    return True


def run():
    """Run this migration.

    Returns:
        True if successful, False otherwise
    """
    db.connect(reuse_if_open=True)

    try:
        # Check if should skip due to future migrations
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 013: Skipped (superseded by future migration)")
            return True

        # Check if tables exist
        required_tables = ["file", "stagingupload", "lfsobjecthistory"]
        for table_name in required_tables:
            if not check_table_exists(db, table_name):
                print(f"Migration 013: Skipped ({table_name} table doesn't exist yet)")
                return True

        # Check if already applied
        if is_applied(db, cfg):
            print("Migration 013: Already applied (all size fields are BIGINT)")
            return True

        print("=" * 70)
        print("Migration 013: Change size fields to BIGINT")
        print("=" * 70)

        # Run migration in transaction
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                result = migrate_postgres()
            else:
                result = migrate_sqlite()

        if result:
            print("\n" + "=" * 70)
            print("Migration 013: ✓ Completed Successfully")
            print("=" * 70)
            print("\nSummary:")
            print("  • File.size: INTEGER → BIGINT")
            print("  • StagingUpload.size: INTEGER → BIGINT")
            print("  • LFSObjectHistory.size: INTEGER → BIGINT")
            print("\nFiles larger than 2GB can now be stored without errors.")

        return result

    except Exception as e:
        print(f"\nMigration 013: ✗ Failed - {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
