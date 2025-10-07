#!/usr/bin/env python3
"""
Migration script to separate storage quotas into private and public quotas.

Migrates from:
- User: storage_quota_bytes, storage_used_bytes
- Organization: storage_quota_bytes, storage_used_bytes

To:
- User: private_quota_bytes, public_quota_bytes, private_used_bytes, public_used_bytes
- Organization: private_quota_bytes, public_quota_bytes, private_used_bytes, public_used_bytes

The migration copies the old quota to private_quota and used to private_used,
leaving public quotas as NULL (unlimited) initially.
"""

import sys
import os

# Add src to path so we can import kohakuhub
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kohakuhub.db import db
from kohakuhub.config import cfg


def migrate_sqlite():
    """Migrate SQLite database - add new quota columns and migrate data."""
    print("Migrating SQLite database...")

    cursor = db.cursor()

    # === User table ===
    print("\nMigrating User table...")

    # Add new columns
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

    # Copy data from old fields to new fields (if old fields exist)
    try:
        cursor.execute(
            """
            UPDATE user
            SET private_quota_bytes = storage_quota_bytes,
                private_used_bytes = storage_used_bytes
            WHERE storage_quota_bytes IS NOT NULL OR storage_used_bytes IS NOT NULL
            """
        )
        print("✓ Migrated User quota data")
    except Exception as e:
        print(f"  Could not migrate User data (old columns may not exist): {e}")

    # === Organization table ===
    print("\nMigrating Organization table...")

    # Add new columns
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

    # Copy data from old fields to new fields (if old fields exist)
    try:
        cursor.execute(
            """
            UPDATE organization
            SET private_quota_bytes = storage_quota_bytes,
                private_used_bytes = storage_used_bytes
            WHERE storage_quota_bytes IS NOT NULL OR storage_used_bytes IS NOT NULL
            """
        )
        print("✓ Migrated Organization quota data")
    except Exception as e:
        print(f"  Could not migrate Organization data (old columns may not exist): {e}")

    db.commit()
    print("\n✓ SQLite migration completed successfully")


def migrate_postgres():
    """Migrate PostgreSQL database - add new quota columns and migrate data."""
    print("Migrating PostgreSQL database...")

    cursor = db.cursor()

    # === User table ===
    print("\nMigrating User table...")

    # Add new columns
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

    # Copy data from old fields to new fields (if old fields exist)
    try:
        cursor.execute(
            """
            UPDATE "user"
            SET private_quota_bytes = storage_quota_bytes,
                private_used_bytes = storage_used_bytes
            WHERE storage_quota_bytes IS NOT NULL OR storage_used_bytes IS NOT NULL
            """
        )
        print("✓ Migrated User quota data")
    except Exception as e:
        print(f"  Could not migrate User data (old columns may not exist): {e}")
        db.rollback()

    # === Organization table ===
    print("\nMigrating Organization table...")

    # Add new columns
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

    # Copy data from old fields to new fields (if old fields exist)
    try:
        cursor.execute(
            """
            UPDATE organization
            SET private_quota_bytes = storage_quota_bytes,
                private_used_bytes = storage_used_bytes
            WHERE storage_quota_bytes IS NOT NULL OR storage_used_bytes IS NOT NULL
            """
        )
        print("✓ Migrated Organization quota data")
    except Exception as e:
        print(f"  Could not migrate Organization data (old columns may not exist): {e}")
        db.rollback()

    db.commit()
    print("\n✓ PostgreSQL migration completed successfully")


def verify_migration():
    """Verify the migration was successful."""
    print("\nVerifying migration...")

    from kohakuhub.db import User, Organization

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
                f"✓ User quota fields verified: private={user.private_quota_bytes}/{user.private_used_bytes}, "
                f"public={user.public_quota_bytes}/{user.public_used_bytes}"
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
                f"✓ Organization quota fields verified: private={org.private_quota_bytes}/{org.private_used_bytes}, "
                f"public={org.public_quota_bytes}/{org.public_used_bytes}"
            )
        else:
            print("  No organizations in database to verify, column creation succeeded")

        print("✓ Migration verification successful!")
        return True

    except Exception as e:
        print(f"✗ Migration verification failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Separate Private/Public Quota Migration")
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
            print("\nNote: Old columns (storage_quota_bytes, storage_used_bytes)")
            print("      can be manually dropped if you're sure the migration worked.")
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
