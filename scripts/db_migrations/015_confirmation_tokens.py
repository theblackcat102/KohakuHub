#!/usr/bin/env python3
"""
Migration 015: Add ConfirmationToken table for two-step dangerous operations.

Provides general-purpose confirmation system for operations like:
- S3 prefix deletion
- Bulk repository deletion
- Any operation requiring explicit user confirmation

Changes:
- Add ConfirmationToken table with expiration and auto-cleanup
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.config import cfg
from kohakuhub.db import ConfirmationToken, db
from _migration_utils import check_table_exists, should_skip_due_to_future_migrations

MIGRATION_NUMBER = 15


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if ConfirmationToken table exists.
    """
    return check_table_exists(db, "confirmationtoken")


def migrate_postgres():
    """Create ConfirmationToken table in PostgreSQL."""
    cursor = db.cursor()

    print("Creating ConfirmationToken table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS confirmationtoken (
            id SERIAL PRIMARY KEY,
            token VARCHAR(255) UNIQUE NOT NULL,
            action_type VARCHAR(255) NOT NULL,
            action_data TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
        """
    )
    print("  ✓ Created ConfirmationToken table")

    # Create indexes
    print("Creating indexes...")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_token
        ON confirmationtoken(token)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_action_type
        ON confirmationtoken(action_type)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_expires_at
        ON confirmationtoken(expires_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_action_type_expires_at
        ON confirmationtoken(action_type, expires_at)
        """
    )
    print("  ✓ Created indexes")


def migrate_sqlite():
    """Create ConfirmationToken table in SQLite."""
    cursor = db.cursor()

    print("Creating ConfirmationToken table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS confirmationtoken (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token VARCHAR(255) UNIQUE NOT NULL,
            action_type VARCHAR(255) NOT NULL,
            action_data TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
        """
    )
    print("  ✓ Created ConfirmationToken table")

    # Create indexes
    print("Creating indexes...")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_token
        ON confirmationtoken(token)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_action_type
        ON confirmationtoken(action_type)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_expires_at
        ON confirmationtoken(expires_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS confirmationtoken_action_type_expires_at
        ON confirmationtoken(action_type, expires_at)
        """
    )
    print("  ✓ Created indexes")


def run():
    """Run migration 015.

    Returns:
        True if successful or already applied, False otherwise
    """
    db.connect(reuse_if_open=True)

    try:
        # Check if should skip due to future migrations
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print(
                f"Migration {MIGRATION_NUMBER}: Skipped (superseded by future migration)"
            )
            return True

        # Check if already applied
        if is_applied(db, cfg):
            print(
                f"Migration {MIGRATION_NUMBER}: Already applied (ConfirmationToken table exists)"
            )
            return True

        print("=" * 70)
        print(f"Migration {MIGRATION_NUMBER}: Add ConfirmationToken table")
        print("=" * 70)

        # Run migration in transaction
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                migrate_postgres()
            else:
                migrate_sqlite()

        print("\n" + "=" * 70)
        print(f"Migration {MIGRATION_NUMBER}: ✓ Completed Successfully")
        print("=" * 70)
        print("\nSummary:")
        print("  • Added ConfirmationToken table for two-step confirmations")
        print("  • Supports: S3 deletion, bulk operations, dangerous actions")
        print("  • Auto-expiration with TTL")
        print("  • Works across multiple workers")
        return True

    except Exception as e:
        print(f"\n✗ Migration {MIGRATION_NUMBER} failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    run()
