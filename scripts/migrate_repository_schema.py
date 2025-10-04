#!/usr/bin/env python3
"""
Migration script to remove unique constraint from Repository.full_id

This allows the same repository name to exist across different types.
For example: user/myrepo can exist as both a model and dataset.

The composite index on (repo_type, namespace, name) ensures uniqueness per type.
"""

import sys
import os

# Add src to path so we can import kohakuhub
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kohakuhub.db import db, Repository
from kohakuhub.config import cfg


def migrate_sqlite():
    """Migrate SQLite database - requires table recreation."""
    print("Migrating SQLite database...")

    # SQLite doesn't support dropping constraints easily
    # We need to recreate the table

    cursor = db.cursor()

    # 1. Create new table without unique constraint on full_id
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS repository_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_type VARCHAR(255) NOT NULL,
            namespace VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            full_id VARCHAR(255) NOT NULL,
            private INTEGER NOT NULL DEFAULT 0,
            owner_id INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL
        )
        """
    )

    # 2. Copy data from old table
    cursor.execute(
        """
        INSERT INTO repository_new
        SELECT id, repo_type, namespace, name, full_id, private, owner_id, created_at
        FROM repository
        """
    )

    # 3. Drop old table
    cursor.execute("DROP TABLE repository")

    # 4. Rename new table
    cursor.execute("ALTER TABLE repository_new RENAME TO repository")

    # 5. Create indexes
    cursor.execute("CREATE INDEX repository_repo_type ON repository (repo_type)")
    cursor.execute("CREATE INDEX repository_namespace ON repository (namespace)")
    cursor.execute("CREATE INDEX repository_name ON repository (name)")
    cursor.execute("CREATE INDEX repository_full_id ON repository (full_id)")
    cursor.execute("CREATE INDEX repository_owner_id ON repository (owner_id)")

    # 6. Create composite unique index
    cursor.execute(
        """
        CREATE UNIQUE INDEX repository_repo_type_namespace_name
        ON repository (repo_type, namespace, name)
        """
    )

    db.commit()
    print("✓ SQLite migration completed successfully")


def migrate_postgres():
    """Migrate PostgreSQL database - drop unique index on full_id."""
    print("Migrating PostgreSQL database...")

    cursor = db.cursor()

    # Check if unique index exists
    cursor.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'repository'
        AND indexname = 'repository_full_id'
        """
    )

    result = cursor.fetchone()

    if result:
        indexdef = result[1] if len(result) > 1 else ""
        print(f"Found index: {result[0]}")
        print(f"Definition: {indexdef}")

        # Check if it's a unique index
        if "UNIQUE" in indexdef.upper():
            print("Dropping unique index: repository_full_id")
            cursor.execute("DROP INDEX IF EXISTS repository_full_id")

            # Create regular (non-unique) index
            print("Creating regular index on full_id...")
            cursor.execute(
                """
                CREATE INDEX repository_full_id
                ON repository (full_id)
                """
            )
            print("✓ Index recreated as non-unique")
        else:
            print("Index is already non-unique, no migration needed")
    else:
        print("Index repository_full_id not found, creating regular index...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS repository_full_id
            ON repository (full_id)
            """
        )

    db.commit()
    print("✓ PostgreSQL migration completed successfully")


def verify_migration():
    """Verify the migration was successful."""
    print("\nVerifying migration...")

    # Check if we can create repos with same full_id but different types
    test_namespace = "__migration_test__"
    test_name = "__test_repo__"
    test_full_id = f"{test_namespace}/{test_name}"

    try:
        # Clean up any existing test repos
        Repository.delete().where(Repository.full_id == test_full_id).execute()

        # Try to create repos with same full_id but different types
        repo1 = Repository.create(
            repo_type="model",
            namespace=test_namespace,
            name=test_name,
            full_id=test_full_id,
            private=False,
        )

        repo2 = Repository.create(
            repo_type="dataset",
            namespace=test_namespace,
            name=test_name,
            full_id=test_full_id,
            private=False,
        )

        print(
            f"✓ Successfully created model: {repo1.repo_type}/{repo1.full_id} (id={repo1.id})"
        )
        print(
            f"✓ Successfully created dataset: {repo2.repo_type}/{repo2.full_id} (id={repo2.id})"
        )

        # Clean up test repos
        repo1.delete_instance()
        repo2.delete_instance()

        print("✓ Migration verification successful!")
        return True

    except Exception as e:
        print(f"✗ Migration verification failed: {e}")
        # Clean up on failure
        Repository.delete().where(Repository.full_id == test_full_id).execute()
        return False


def main():
    print("=" * 60)
    print("Repository Schema Migration")
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
