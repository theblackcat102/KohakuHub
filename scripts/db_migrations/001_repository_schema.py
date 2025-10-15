#!/usr/bin/env python3
"""
Migration 001: Remove unique constraint from Repository.full_id

This allows the same repository name to exist across different types.
For example: user/myrepo can exist as both a model and dataset.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kohakuhub.db import db
from kohakuhub.config import cfg


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
    """Run this migration."""
    db.connect(reuse_if_open=True)

    try:
        if not check_migration_needed():
            print("Migration 001: Already applied (constraint removed)")
            return True

        print("Migration 001: Removing unique constraint from Repository.full_id...")

        # Just import and run the existing migration logic
        from pathlib import Path

        parent_dir = Path(__file__).parent.parent
        spec_path = parent_dir / "migrate_repository_schema.py"

        import importlib.util

        spec = importlib.util.spec_from_file_location("migrate_repo_schema", spec_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Run the migration
        if cfg.app.db_backend == "postgres":
            module.migrate_postgres()
        else:
            module.migrate_sqlite()

        print("Migration 001: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 001: ✗ Failed - {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
