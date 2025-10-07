#!/usr/bin/env python3
"""
Migration script to add storage quota fields to User and Organization models.

Adds the following fields:
- User.storage_quota_bytes (BIGINT, nullable) - Maximum storage allowed (NULL = unlimited)
- User.storage_used_bytes (BIGINT, default 0) - Current storage usage
- Organization.storage_quota_bytes (BIGINT, nullable) - Maximum storage allowed (NULL = unlimited)
- Organization.storage_used_bytes (BIGINT, default 0) - Current storage usage
"""

import sys
import os

# Add src to path so we can import kohakuhub
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kohakuhub.db import db, User, Organization
from kohakuhub.config import cfg


def migrate_sqlite():
    """Migrate SQLite database - add quota columns."""
    print("Migrating SQLite database...")

    cursor = db.cursor()

    # Add storage quota columns to User table
    try:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN storage_quota_bytes INTEGER DEFAULT NULL"
        )
        print("✓ Added User.storage_quota_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  User.storage_quota_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN storage_used_bytes INTEGER DEFAULT 0"
        )
        print("✓ Added User.storage_used_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  User.storage_used_bytes already exists, skipping")
        else:
            raise

    # Add storage quota columns to Organization table
    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN storage_quota_bytes INTEGER DEFAULT NULL"
        )
        print("✓ Added Organization.storage_quota_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  Organization.storage_quota_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN storage_used_bytes INTEGER DEFAULT 0"
        )
        print("✓ Added Organization.storage_used_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  Organization.storage_used_bytes already exists, skipping")
        else:
            raise

    db.commit()
    print("✓ SQLite migration completed successfully")


def migrate_postgres():
    """Migrate PostgreSQL database - add quota columns."""
    print("Migrating PostgreSQL database...")

    cursor = db.cursor()

    # Add storage quota columns to User table
    try:
        cursor.execute(
            'ALTER TABLE "user" ADD COLUMN storage_quota_bytes BIGINT DEFAULT NULL'
        )
        print("✓ Added User.storage_quota_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  User.storage_quota_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            'ALTER TABLE "user" ADD COLUMN storage_used_bytes BIGINT DEFAULT 0'
        )
        print("✓ Added User.storage_used_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  User.storage_used_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    # Add storage quota columns to Organization table
    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN storage_quota_bytes BIGINT DEFAULT NULL"
        )
        print("✓ Added Organization.storage_quota_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Organization.storage_quota_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN storage_used_bytes BIGINT DEFAULT 0"
        )
        print("✓ Added Organization.storage_used_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Organization.storage_used_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    db.commit()
    print("✓ PostgreSQL migration completed successfully")


def verify_migration():
    """Verify the migration was successful."""
    print("\nVerifying migration...")

    # Check if columns exist by querying a record
    try:
        # Query a user (or get the first one)
        user = User.select().first()
        if user:
            # Try to access the new fields
            _ = user.storage_quota_bytes
            _ = user.storage_used_bytes
            print(
                f"✓ User quota fields verified (quota={user.storage_quota_bytes}, used={user.storage_used_bytes})"
            )
        else:
            print("  No users in database to verify, creating columns succeeded")

        # Query an organization (or get the first one)
        org = Organization.select().first()
        if org:
            # Try to access the new fields
            _ = org.storage_quota_bytes
            _ = org.storage_used_bytes
            print(
                f"✓ Organization quota fields verified (quota={org.storage_quota_bytes}, used={org.storage_used_bytes})"
            )
        else:
            print(
                "  No organizations in database to verify, creating columns succeeded"
            )

        print("✓ Migration verification successful!")
        return True

    except Exception as e:
        print(f"✗ Migration verification failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Storage Quota Migration")
    print("=" * 60)
    print(f"\nDatabase backend: {cfg.app.db_backend}")
    print(f"Database URL: {cfg.app.database_url}")
    print()

    # Connect to database
    db.connect(reuse_if_open=True)

    try:
        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()

        # Verify migration
        if verify_migration():
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("Migration verification failed - please check manually")
            print("=" * 60)
            return 1

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
