#!/usr/bin/env python3
"""
Migration 003: Add Commit table for tracking user commits.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kohakuhub.db import db, Commit


def check_migration_needed():
    """Check if Commit table exists."""
    return not db.table_exists("commit")


def run():
    """Run this migration."""
    db.connect(reuse_if_open=True)

    try:
        if not check_migration_needed():
            print("Migration 003: Already applied (Commit table exists)")
            return True

        print("Migration 003: Creating Commit table...")
        db.create_tables([Commit], safe=True)
        print("Migration 003: ✓ Completed")
        return True

    except Exception as e:
        print(f"Migration 003: ✗ Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
