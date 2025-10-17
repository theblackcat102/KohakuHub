#!/usr/bin/env python3
"""
Migration 001: Remove unique constraint from Repository.full_id

This allows the same repository name to exist across different types.
For example: user/myrepo can exist as both a model and dataset.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.db import db
from kohakuhub.config import cfg

# Import migration utilities
from _migration_utils import should_skip_due_to_future_migrations

# Migration number for this script
MIGRATION_NUMBER = 1


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if the unique constraint has been removed from Repository.full_id.
    """
    try:
        cursor = db.cursor()
        if cfg.app.db_backend == "postgres":
            cursor.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'repository' AND indexname = 'repository_full_id'
            """
            )
            result = cursor.fetchone()
            if result and len(result) > 1:
                # If UNIQUE is in the index definition, migration NOT applied
                return "UNIQUE" not in result[1].upper()
            # Index doesn't exist or can't check = assume applied
            return True
        else:
            # SQLite: Hard to detect constraint removal, assume applied if table exists
            return db.table_exists("repository")
    except Exception:
        # Error = treat as applied (skip migration)
        return True


def check_migration_needed():
    """Check if unique constraint exists on full_id."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        cursor.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'repository' AND indexname = 'repository_full_id'
        """
        )
        result = cursor.fetchone()
        if result and len(result) > 1:
            return "UNIQUE" in result[1].upper()
        return False
    else:
        # SQLite: Check if we can create duplicate full_id with different types
        cursor.execute(
            "SELECT COUNT(*) FROM repository WHERE full_id = '__test__/__test__'"
        )
        return True  # Always run for SQLite (hard to detect constraint)


def run():
    """Run this migration.

    IMPORTANT: Do NOT call db.close() in finally block!
    The db connection is managed by run_migrations.py and should stay open
    across all migrations to avoid stdout/stderr closure issues on Windows.

    NOTE: Migration 001 delegates to external script (migrate_repository_schema.py).
    Cannot easily add db.atomic() without modifying external script.
    """
    db.connect(reuse_if_open=True)

    try:
        # Pre-flight checks (outside transaction for performance)
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 001: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 001: Already applied (constraint removed)")
            return True

        print("Migration 001: Removing unique constraint from Repository.full_id...")

        # Import and run the existing migration logic (external script)
        from pathlib import Path
        import importlib.util

        parent_dir = Path(__file__).parent.parent
        spec_path = parent_dir / "migrate_repository_schema.py"

        if not spec_path.exists():
            print(f"  WARNING: External script not found: {spec_path}")
            print("  Skipping migration 001 (constraint likely already removed or N/A)")
            return True

        spec = importlib.util.spec_from_file_location("migrate_repo_schema", spec_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Run the migration (external script handles its own transactions)
        if cfg.app.db_backend == "postgres":
            module.migrate_postgres()
        else:
            module.migrate_sqlite()

        print("Migration 001: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 001: ✗ Failed - {e}")
        print("  WARNING: External script migration - may need manual rollback")
        import traceback

        traceback.print_exc()
        return False
    # NOTE: No finally block - db connection stays open


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
