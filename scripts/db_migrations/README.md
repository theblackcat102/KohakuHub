# Database Migrations

This directory contains database migration scripts for KohakuHub.

## How Migrations Work

1. **Auto-detection**: Each migration checks if it needs to run by verifying if columns/tables exist
2. **Sequential execution**: Migrations run in numerical order (001, 002, 003, etc.)
3. **Idempotent**: Safe to run multiple times - already-applied migrations are skipped
4. **Auto-run**: Migrations automatically run on container startup via `docker/startup.py`

## Migration Order

| # | Name | Description |
|---|------|-------------|
| 001 | repository_schema | Remove unique constraint from Repository.full_id |
| 002 | user_org_quotas | Add private/public quota fields to User/Organization |
| 003 | commit_tracking | Add Commit table for tracking user commits |
| 004 | repo_quotas | Add quota/used_bytes fields to Repository |

## Creating New Migrations

1. Create a new file: `scripts/db_migrations/00X_name.py`
2. Implement these functions:
   - `check_migration_needed()` - Returns True if migration should run
   - `migrate_sqlite()` - SQLite migration logic
   - `migrate_postgres()` - PostgreSQL migration logic
   - `run()` - Main entry point

3. Template:
```python
#!/usr/bin/env python3
"""Migration 00X: Description"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kohakuhub.db import db
from kohakuhub.config import cfg

def check_migration_needed():
    """Check if columns/tables exist."""
    cursor = db.cursor()
    if cfg.app.db_backend == "postgres":
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='mytable' AND column_name='mycolumn'
        """)
        return cursor.fetchone() is None
    else:
        cursor.execute("PRAGMA table_info(mytable)")
        columns = [row[1] for row in cursor.fetchall()]
        return 'mycolumn' not in columns

def migrate_sqlite():
    cursor = db.cursor()
    cursor.execute("ALTER TABLE mytable ADD COLUMN mycolumn INTEGER")
    db.commit()

def migrate_postgres():
    cursor = db.cursor()
    cursor.execute("ALTER TABLE mytable ADD COLUMN mycolumn BIGINT")
    db.commit()

def run():
    db.connect(reuse_if_open=True)
    try:
        if not check_migration_needed():
            print("Migration 00X: Already applied")
            return True
        print("Migration 00X: Running...")
        if cfg.app.db_backend == "postgres":
            migrate_postgres()
        else:
            migrate_sqlite()
        print("Migration 00X: ✓ Completed")
        return True
    except Exception as e:
        print(f"Migration 00X: ✗ Failed - {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
```

## Running Migrations

**Automatic (in Docker):**
- Migrations run automatically on container startup

**Manual:**
```bash
# Run all migrations
python scripts/run_migrations.py

# Run specific migration
python scripts/db_migrations/001_repository_schema.py
```

## Notes

- Migrations are idempotent - safe to re-run
- Failed migrations will prevent server startup
- Old migration scripts in `scripts/migrate_*.py` are kept for reference
