#!/usr/bin/env python3
"""
Test script for migration 009 (Repository LFS settings).

This script:
1. Creates a test database with old schema (old_db.py)
2. Populates with mock data
3. Runs migration 009
4. Verifies migration succeeded and data preserved
5. Tests new functionality

Usage:
    python scripts/test_migration_009.py
"""

import sys
import os
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "db_migrations"))

# Test database path
TEST_DB_PATH = Path(__file__).parent.parent / "test_migration_009.db"


def cleanup_test_db():
    """Remove test database if exists."""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        print(f"Cleaned up old test database: {TEST_DB_PATH}")


def step1_create_old_schema():
    """Step 1: Create database with old schema (before migration 009)."""
    print("\n" + "=" * 70)
    print("STEP 1: Create database with OLD schema (before migration 009)")
    print("=" * 70)

    # Import old schema
    from kohakuhub import old_db
    from kohakuhub.config import cfg

    # Override database to use test DB
    from peewee import SqliteDatabase

    old_db.db = SqliteDatabase(str(TEST_DB_PATH), pragmas={"foreign_keys": 1})

    # Reconnect all models to test DB
    for model in [
        old_db.User,
        old_db.EmailVerification,
        old_db.Session,
        old_db.Token,
        old_db.Repository,
        old_db.File,
        old_db.StagingUpload,
        old_db.UserOrganization,
        old_db.Commit,
        old_db.LFSObjectHistory,
        old_db.SSHKey,
        old_db.Invitation,
    ]:
        model._meta.database = old_db.db

    # Create tables
    old_db.db.connect(reuse_if_open=True)
    old_db.db.create_tables(
        [
            old_db.User,
            old_db.EmailVerification,
            old_db.Session,
            old_db.Token,
            old_db.Repository,
            old_db.File,
            old_db.StagingUpload,
            old_db.UserOrganization,
            old_db.Commit,
            old_db.LFSObjectHistory,
            old_db.SSHKey,
            old_db.Invitation,
        ],
        safe=True,
    )

    # Verify Repository table structure (should NOT have LFS fields)
    cursor = old_db.db.cursor()
    cursor.execute("PRAGMA table_info(repository)")
    columns = [row[1] for row in cursor.fetchall()]

    print(f"  Created tables with old schema")
    print(f"  Repository columns: {len(columns)}")
    print(f"  Has quota_bytes: {'quota_bytes' in columns}")
    print(f"  Has lfs_threshold_bytes: {'lfs_threshold_bytes' in columns}")
    print(f"  Has lfs_keep_versions: {'lfs_keep_versions' in columns}")
    print(f"  Has lfs_suffix_rules: {'lfs_suffix_rules' in columns}")

    if "lfs_threshold_bytes" in columns:
        print("  ERROR: Old schema should NOT have LFS fields!")
        return False

    print("  ✓ Old schema created correctly (no LFS fields)")
    return True


def step2_populate_mock_data():
    """Step 2: Populate database with mock data."""
    print("\n" + "=" * 70)
    print("STEP 2: Populate with mock data")
    print("=" * 70)

    from kohakuhub import old_db

    # Create test org
    org = old_db.User.create(
        username="test-org",
        normalized_name="testorg",
        is_org=True,
        email=None,
        password_hash=None,
        private_quota_bytes=10 * 1024 * 1024 * 1024,  # 10GB
        public_quota_bytes=50 * 1024 * 1024 * 1024,  # 50GB
    )
    print(f"  Created organization: {org.username}")

    # Create test user
    user = old_db.User.create(
        username="test-user",
        normalized_name="testuser",
        is_org=False,
        email="test@example.com",
        password_hash="dummy_hash",
        email_verified=True,
        is_active=True,
        private_quota_bytes=5 * 1024 * 1024 * 1024,  # 5GB
        public_quota_bytes=20 * 1024 * 1024 * 1024,  # 20GB
    )
    print(f"  Created user: {user.username}")

    # Create test repositories
    repo1 = old_db.Repository.create(
        repo_type="model",
        namespace="test-org",
        name="test-model",
        full_id="test-org/test-model",
        private=False,
        owner=org,
        quota_bytes=None,  # Inherit from org
        used_bytes=1024 * 1024 * 100,  # 100MB
    )
    print(f"  Created repository: {repo1.full_id}")

    repo2 = old_db.Repository.create(
        repo_type="dataset",
        namespace="test-user",
        name="test-dataset",
        full_id="test-user/test-dataset",
        private=True,
        owner=user,
        quota_bytes=2 * 1024 * 1024 * 1024,  # Custom 2GB quota
        used_bytes=500 * 1024 * 1024,  # 500MB used
    )
    print(f"  Created repository: {repo2.full_id}")

    # Verify data
    repo_count = old_db.Repository.select().count()
    user_count = old_db.User.select().count()

    print(f"\n  ✓ Mock data created:")
    print(f"    Users: {user_count}")
    print(f"    Repositories: {repo_count}")

    return True


def step3_run_migration():
    """Step 3: Run migration 009."""
    print("\n" + "=" * 70)
    print("STEP 3: Run migration 009")
    print("=" * 70)

    # Migration script will use kohakuhub.db which is already connected to our test DB
    # We just need to temporarily override the database path
    import kohakuhub.db as db_module
    from peewee import SqliteDatabase

    # Close any existing connection
    if not db_module.db.is_closed():
        db_module.db.close()

    # Replace with test database
    old_db = db_module.db
    db_module.db = SqliteDatabase(str(TEST_DB_PATH), pragmas={"foreign_keys": 1})
    db_module.db.connect(reuse_if_open=True)

    # Also update all model references to use the test db
    from kohakuhub.db import (
        User,
        EmailVerification,
        Session,
        Token,
        Repository,
        File,
        StagingUpload,
        UserOrganization,
        Commit,
        LFSObjectHistory,
        SSHKey,
        Invitation,
    )

    for model in [
        User,
        EmailVerification,
        Session,
        Token,
        Repository,
        File,
        StagingUpload,
        UserOrganization,
        Commit,
        LFSObjectHistory,
        SSHKey,
        Invitation,
    ]:
        model._meta.database = db_module.db

    try:
        # Load and run migration
        migration_path = (
            Path(__file__).parent / "db_migrations" / "009_repo_lfs_settings.py"
        )

        import importlib.util

        spec = importlib.util.spec_from_file_location("migration_009", migration_path)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)

        # Run migration
        success = migration_module.run()

        if not success:
            print("  ✗ Migration failed!")
            return False

        print("  ✓ Migration completed")
        return True

    finally:
        # Don't restore old_db, keep using test DB for verification
        pass


def step4_verify_migration():
    """Step 4: Verify migration succeeded and data preserved."""
    print("\n" + "=" * 70)
    print("STEP 4: Verify migration results")
    print("=" * 70)

    # DB is already connected to test DB from step3
    from kohakuhub.db import Repository, User, db

    db.connect(reuse_if_open=True)

    # Verify schema
    cursor = db.cursor()
    cursor.execute("PRAGMA table_info(repository)")
    columns = [row[1] for row in cursor.fetchall()]

    print(f"  Repository columns after migration: {len(columns)}")
    print(f"  Has lfs_threshold_bytes: {'lfs_threshold_bytes' in columns}")
    print(f"  Has lfs_keep_versions: {'lfs_keep_versions' in columns}")
    print(f"  Has lfs_suffix_rules: {'lfs_suffix_rules' in columns}")

    if not all(
        col in columns
        for col in ["lfs_threshold_bytes", "lfs_keep_versions", "lfs_suffix_rules"]
    ):
        print("  ✗ Migration failed - LFS columns not found!")
        return False

    # Verify data preserved
    repos = list(Repository.select())
    users = list(User.select())

    print(f"\n  Data preservation check:")
    print(f"    Users: {len(users)}")
    print(f"    Repositories: {len(repos)}")

    if len(repos) != 2 or len(users) != 2:
        print("  ✗ Data loss detected!")
        return False

    # Verify specific data
    repo1 = Repository.get_or_none(
        Repository.repo_type == "model", Repository.namespace == "test-org"
    )
    repo2 = Repository.get_or_none(
        Repository.repo_type == "dataset", Repository.namespace == "test-user"
    )

    if not repo1 or not repo2:
        print("  ✗ Cannot find test repositories!")
        return False

    print(f"\n  Repository 1 (test-org/test-model):")
    print(f"    quota_bytes: {repo1.quota_bytes}")
    print(f"    used_bytes: {repo1.used_bytes}")
    print(
        f"    lfs_threshold_bytes: {repo1.lfs_threshold_bytes} (NULL = server default)"
    )
    print(f"    lfs_keep_versions: {repo1.lfs_keep_versions} (NULL = server default)")
    print(f"    lfs_suffix_rules: {repo1.lfs_suffix_rules} (NULL = no rules)")

    print(f"\n  Repository 2 (test-user/test-dataset):")
    print(f"    quota_bytes: {repo2.quota_bytes}")
    print(f"    used_bytes: {repo2.used_bytes}")
    print(f"    lfs_threshold_bytes: {repo2.lfs_threshold_bytes}")
    print(f"    lfs_keep_versions: {repo2.lfs_keep_versions}")
    print(f"    lfs_suffix_rules: {repo2.lfs_suffix_rules}")

    # Verify NULL values (new fields should be NULL after migration)
    if repo1.lfs_threshold_bytes is not None:
        print("  ✗ lfs_threshold_bytes should be NULL after migration!")
        return False

    if repo1.lfs_keep_versions is not None:
        print("  ✗ lfs_keep_versions should be NULL after migration!")
        return False

    if repo1.lfs_suffix_rules is not None:
        print("  ✗ lfs_suffix_rules should be NULL after migration!")
        return False

    # Verify old data preserved
    if repo1.quota_bytes is not None:
        print("  ✗ quota_bytes should still be NULL!")
        return False

    if repo1.used_bytes != 1024 * 1024 * 100:
        print(f"  ✗ used_bytes changed! Expected 104857600, got {repo1.used_bytes}")
        return False

    if repo2.quota_bytes != 2 * 1024 * 1024 * 1024:
        print(f"  ✗ quota_bytes changed! Expected 2147483648, got {repo2.quota_bytes}")
        return False

    print("\n  ✓ All data preserved correctly")
    print("  ✓ New LFS fields added as NULL")
    return True


def step5_test_new_functionality():
    """Step 5: Test new LFS functionality."""
    print("\n" + "=" * 70)
    print("STEP 5: Test new LFS functionality")
    print("=" * 70)

    # DB is already connected to test DB
    from kohakuhub.db import Repository, db
    from kohakuhub.db_operations import (
        get_effective_lfs_keep_versions,
        get_effective_lfs_suffix_rules,
        get_effective_lfs_threshold,
        should_use_lfs,
    )
    from kohakuhub.config import cfg
    import json

    repo = Repository.get_or_none(
        Repository.repo_type == "model", Repository.namespace == "test-org"
    )

    if not repo:
        print("  ✗ Test repository not found!")
        return False

    # Test 1: Default values (NULL in DB)
    print("  Test 1: Default values (NULL in database)")
    threshold = get_effective_lfs_threshold(repo)
    keep_versions = get_effective_lfs_keep_versions(repo)
    suffix_rules = get_effective_lfs_suffix_rules(repo)

    print(f"    Effective threshold: {threshold / (1024*1024):.1f} MB")
    print(f"    Effective keep_versions: {keep_versions}")
    print(f"    Suffix rules: {suffix_rules}")

    if threshold != cfg.app.lfs_threshold_bytes:
        print(
            f"    ✗ Wrong threshold! Expected {cfg.app.lfs_threshold_bytes}, got {threshold}"
        )
        return False

    if keep_versions != cfg.app.lfs_keep_versions:
        print(
            f"    ✗ Wrong keep_versions! Expected {cfg.app.lfs_keep_versions}, got {keep_versions}"
        )
        return False

    if len(suffix_rules) != 0:
        print(f"    ✗ Suffix rules should be empty! Got {suffix_rules}")
        return False

    # Test 2: should_use_lfs with defaults
    test_small = should_use_lfs(repo, "config.json", 1024)  # 1KB
    test_large = should_use_lfs(repo, "model.bin", 10 * 1024 * 1024)  # 10MB

    print(f"    config.json (1KB) uses LFS: {test_small}")
    print(f"    model.bin (10MB) uses LFS: {test_large}")

    if test_small or not test_large:
        print("    ✗ LFS detection failed with defaults!")
        return False

    print("    ✓ Default values work correctly")

    # Test 3: Custom threshold
    print("\n  Test 2: Custom threshold (1MB)")
    repo.lfs_threshold_bytes = 1024 * 1024
    repo.save()

    threshold = get_effective_lfs_threshold(repo)
    test_500kb = should_use_lfs(repo, "file.bin", 500 * 1024)
    test_2mb = should_use_lfs(repo, "file.bin", 2 * 1024 * 1024)

    print(f"    Effective threshold: {threshold / (1024*1024):.1f} MB")
    print(f"    file.bin (500KB) uses LFS: {test_500kb}")
    print(f"    file.bin (2MB) uses LFS: {test_2mb}")

    if test_500kb or not test_2mb:
        print("    ✗ Custom threshold not working!")
        return False

    print("    ✓ Custom threshold works correctly")

    # Test 4: Suffix rules
    print("\n  Test 3: Suffix rules (.safetensors, .gguf)")
    repo.lfs_suffix_rules = json.dumps([".safetensors", ".gguf"])
    repo.save()

    suffix_rules = get_effective_lfs_suffix_rules(repo)
    test_safetensors = should_use_lfs(repo, "model.safetensors", 100)  # 100 bytes
    test_gguf = should_use_lfs(repo, "model.gguf", 500)  # 500 bytes
    test_json = should_use_lfs(repo, "config.json", 100)  # 100 bytes

    print(f"    Suffix rules: {suffix_rules}")
    print(f"    model.safetensors (100B) uses LFS: {test_safetensors}")
    print(f"    model.gguf (500B) uses LFS: {test_gguf}")
    print(f"    config.json (100B) uses LFS: {test_json}")

    if not test_safetensors or not test_gguf or test_json:
        print("    ✗ Suffix rules not working!")
        return False

    print("    ✓ Suffix rules work correctly")

    # Test 5: Custom keep_versions
    print("\n  Test 4: Custom keep_versions (10)")
    repo.lfs_keep_versions = 10
    repo.save()

    keep_versions = get_effective_lfs_keep_versions(repo)
    print(f"    Effective keep_versions: {keep_versions}")

    if keep_versions != 10:
        print(f"    ✗ Wrong keep_versions! Expected 10, got {keep_versions}")
        return False

    print("    ✓ Custom keep_versions works correctly")

    print("\n  ✓ All new LFS functionality works!")
    return True


def main():
    """Run all test steps."""
    print("=" * 70)
    print("MIGRATION 009 TEST SUITE")
    print("Testing: Repository LFS Settings")
    print("=" * 70)

    # Cleanup old test database
    cleanup_test_db()

    # Run test steps
    steps = [
        step1_create_old_schema,
        step2_populate_mock_data,
        step3_run_migration,
        step4_verify_migration,
        step5_test_new_functionality,
    ]

    for i, step in enumerate(steps, 1):
        try:
            success = step()
            if not success:
                print(f"\n✗ Step {i} failed!")
                print(f"\nTest database preserved at: {TEST_DB_PATH}")
                print("You can inspect it with: sqlite3 test_migration_009.db")
                return 1
        except Exception as e:
            print(f"\n✗ Step {i} crashed with exception: {e}")
            import traceback

            traceback.print_exc()
            print(f"\nTest database preserved at: {TEST_DB_PATH}")
            return 1

    # Cleanup on success
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nMigration 009 is working correctly:")
    print("  ✓ Schema updated without data loss")
    print("  ✓ NULL values default to server settings")
    print("  ✓ Custom thresholds work")
    print("  ✓ Suffix rules work")
    print("  ✓ Keep versions work")
    print("\nCleaning up test database...")

    # Close database before cleanup
    from kohakuhub.db import db

    if not db.is_closed():
        db.close()

    cleanup_test_db()
    print("✓ Cleanup complete\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
