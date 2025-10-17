#!/usr/bin/env python3
"""
Main migration runner for KohakuHub database migrations.

This script automatically discovers and runs all migration scripts in the
db_migrations/ directory in numerical order (001, 002, 003, etc.).

Each migration script should:
1. Have a run() function that returns True on success, False on failure
2. Auto-detect if it needs to run (check if columns exist)
3. Handle both SQLite and PostgreSQL

Usage:
    python scripts/run_migrations.py
"""

import sys
import os
from pathlib import Path
import importlib.util

# Add src to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

# Import after path setup
from kohakuhub.db import db, init_db
from kohakuhub.config import cfg


def discover_migrations():
    """Discover all migration scripts in db_migrations/ directory.

    Returns:
        List of (name, path) tuples sorted by name
    """
    migrations_dir = SCRIPT_DIR / "db_migrations"
    if not migrations_dir.exists():
        return []

    migrations = []
    for file_path in migrations_dir.glob("*.py"):
        if file_path.name.startswith("_"):
            continue  # Skip __init__.py and private files
        migrations.append((file_path.stem, file_path))

    # Sort by name (which should be numerical like 001_, 002_, etc.)
    migrations.sort(key=lambda x: x[0])
    return migrations


def load_migration_module(name, path):
    """Dynamically load a migration module.

    Args:
        name: Module name
        path: Path to migration file

    Returns:
        Loaded module or None if failed
    """
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"  [ERROR] Failed to load {name}: {e}")
        return None


def run_migrations():
    """Run all pending migrations."""
    print("=" * 70)
    print("KohakuHub Database Migrations")
    print("=" * 70)
    print(f"Database backend: {cfg.app.db_backend}")
    print(f"Database URL: {cfg.app.database_url}")
    print()

    # Discover migrations
    migrations = discover_migrations()
    if not migrations:
        print("No migrations found in db_migrations/")
        print("\nInitializing database (creating tables)...")
        init_db()
        print("✓ Database initialized\n")
        return True

    print(f"Found {len(migrations)} migration(s):\n")

    # Run each migration
    all_success = True
    for name, path in migrations:
        print(f"Running {name}...")

        # Load migration module
        module = load_migration_module(name, path)
        if not module:
            all_success = False
            continue

        # Check if module has run() function
        if not hasattr(module, "run"):
            print(f"  [ERROR] Migration {name} missing run() function")
            all_success = False
            continue

        # Run migration
        try:
            success = module.run()
            if not success:
                all_success = False
        except Exception as e:
            print(f"  [ERROR] Migration {name} crashed: {e}")
            import traceback

            traceback.print_exc()
            all_success = False

        print()

    # Initialize database AFTER migrations (create tables/indexes if needed)
    if all_success:
        print("\nFinalizing database schema (ensuring all tables/indexes exist)...")
        try:
            init_db()
            print("[OK] Database schema finalized\n")
        except Exception as e:
            print(f"[ERROR] Failed to finalize database schema: {e}")
            import traceback

            traceback.print_exc()
            all_success = False

    # Summary
    print("=" * 70)
    if all_success:
        print("[OK] All migrations completed successfully!")
    else:
        print("[ERROR] Some migrations failed - please check errors above")
    print("=" * 70)

    return all_success


def main():
    try:
        success = run_migrations()
        return 0 if success else 1
    except Exception as e:
        print(f"\n[ERROR] Migration runner crashed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
