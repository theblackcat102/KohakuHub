#!/usr/bin/env python3
"""
Comprehensive migration script to add storage quota fields to User and Organization models.

Adds the following fields:
- User: private_quota_bytes, public_quota_bytes, private_used_bytes, public_used_bytes
- Organization: private_quota_bytes, public_quota_bytes, private_used_bytes, public_used_bytes

All quota fields default to NULL (unlimited) and used_bytes default to 0.
"""

import sys
import os

# Add src to path so we can import kohakuhub
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kohakuhub.db import db, User, Organization
from kohakuhub.config import cfg


def migrate_sqlite():
    """Migrate SQLite database - add all quota columns."""
    print("Migrating SQLite database...")

    cursor = db.cursor()

    # === User table ===
    print("\nMigrating User table...")

    # Add private quota columns
    try:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN private_quota_bytes INTEGER DEFAULT NULL"
        )
        print("✓ Added User.private_quota_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  User.private_quota_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN public_quota_bytes INTEGER DEFAULT NULL"
        )
        print("✓ Added User.public_quota_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  User.public_quota_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN private_used_bytes INTEGER DEFAULT 0"
        )
        print("✓ Added User.private_used_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  User.private_used_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN public_used_bytes INTEGER DEFAULT 0"
        )
        print("✓ Added User.public_used_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  User.public_used_bytes already exists, skipping")
        else:
            raise

    # === Organization table ===
    print("\nMigrating Organization table...")

    # Add private/public quota columns
    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN private_quota_bytes INTEGER DEFAULT NULL"
        )
        print("✓ Added Organization.private_quota_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  Organization.private_quota_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN public_quota_bytes INTEGER DEFAULT NULL"
        )
        print("✓ Added Organization.public_quota_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  Organization.public_quota_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN private_used_bytes INTEGER DEFAULT 0"
        )
        print("✓ Added Organization.private_used_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  Organization.private_used_bytes already exists, skipping")
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN public_used_bytes INTEGER DEFAULT 0"
        )
        print("✓ Added Organization.public_used_bytes")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("  Organization.public_used_bytes already exists, skipping")
        else:
            raise

    db.commit()
    print("\n✓ SQLite migration completed successfully")


def migrate_postgres():
    """Migrate PostgreSQL database - add all quota columns."""
    print("Migrating PostgreSQL database...")

    cursor = db.cursor()

    # === User table ===
    print("\nMigrating User table...")

    # Add private/public quota columns
    try:
        cursor.execute(
            'ALTER TABLE "user" ADD COLUMN private_quota_bytes BIGINT DEFAULT NULL'
        )
        print("✓ Added User.private_quota_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  User.private_quota_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            'ALTER TABLE "user" ADD COLUMN public_quota_bytes BIGINT DEFAULT NULL'
        )
        print("✓ Added User.public_quota_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  User.public_quota_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            'ALTER TABLE "user" ADD COLUMN private_used_bytes BIGINT DEFAULT 0'
        )
        print("✓ Added User.private_used_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  User.private_used_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            'ALTER TABLE "user" ADD COLUMN public_used_bytes BIGINT DEFAULT 0'
        )
        print("✓ Added User.public_used_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  User.public_used_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    # === Organization table ===
    print("\nMigrating Organization table...")

    # Add private/public quota columns
    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN private_quota_bytes BIGINT DEFAULT NULL"
        )
        print("✓ Added Organization.private_quota_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Organization.private_quota_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN public_quota_bytes BIGINT DEFAULT NULL"
        )
        print("✓ Added Organization.public_quota_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Organization.public_quota_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN private_used_bytes BIGINT DEFAULT 0"
        )
        print("✓ Added Organization.private_used_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Organization.private_used_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    try:
        cursor.execute(
            "ALTER TABLE organization ADD COLUMN public_used_bytes BIGINT DEFAULT 0"
        )
        print("✓ Added Organization.public_used_bytes")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Organization.public_used_bytes already exists, skipping")
            db.rollback()
        else:
            raise

    db.commit()
    print("\n✓ PostgreSQL migration completed successfully")


def verify_migration():
    """Verify the migration was successful."""
    print("\nVerifying migration...")

    try:
        # Query a user (or get the first one)
        user = User.select().first()
        if user:
            # Try to access the new fields
            _ = user.private_quota_bytes
            _ = user.public_quota_bytes
            _ = user.private_used_bytes
            _ = user.public_used_bytes
            print(
                f"✓ User quota fields verified (user: {user.username}): "
                f"private_quota={user.private_quota_bytes}, public_quota={user.public_quota_bytes}, "
                f"private_used={user.private_used_bytes}, public_used={user.public_used_bytes}"
            )
        else:
            print("  No users in database to verify, column creation succeeded")

        # Query an organization (or get the first one)
        org = Organization.select().first()
        if org:
            # Try to access the new fields
            _ = org.private_quota_bytes
            _ = org.public_quota_bytes
            _ = org.private_used_bytes
            _ = org.public_used_bytes
            print(
                f"✓ Organization quota fields verified (org: {org.name}): "
                f"private_quota={org.private_quota_bytes}, public_quota={org.public_quota_bytes}, "
                f"private_used={org.private_used_bytes}, public_used={org.public_used_bytes}"
            )
        else:
            print("  No organizations in database to verify, column creation succeeded")

        print("✓ Migration verification successful!")
        return True

    except Exception as e:
        print(f"✗ Migration verification failed: {e}")
        return False


def main():
    print("=" * 70)
    print("Storage Quota Migration - Add Private/Public Quota Fields")
    print("=" * 70)
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
            print("\n" + "=" * 70)
            print("Migration completed successfully!")
            print("=" * 70)
            print("\nNew fields added:")
            print("  User:")
            print("    - private_quota_bytes (BIGINT, NULL = unlimited)")
            print("    - public_quota_bytes (BIGINT, NULL = unlimited)")
            print("    - private_used_bytes (BIGINT, default 0)")
            print("    - public_used_bytes (BIGINT, default 0)")
            print("  Organization:")
            print("    - private_quota_bytes (BIGINT, NULL = unlimited)")
            print("    - public_quota_bytes (BIGINT, NULL = unlimited)")
            print("    - private_used_bytes (BIGINT, default 0)")
            print("    - public_used_bytes (BIGINT, default 0)")
            return 0
        else:
            print("\n" + "=" * 70)
            print("Migration verification failed - please check manually")
            print("=" * 70)
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
