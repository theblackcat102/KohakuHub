#!/usr/bin/env python3
"""
Migration 010: Add likes and download tracking system.

Adds the following:
- Repository: downloads, likes_count (denormalized counters)
- RepositoryLike table (user likes)
- DownloadSession table (session-based download tracking with deduplication)
- DailyRepoStats table (daily aggregated statistics for trends)
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Add db_migrations to path (for _migration_utils)
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.db import db
from kohakuhub.config import cfg
from _migration_utils import should_skip_due_to_future_migrations, check_column_exists

MIGRATION_NUMBER = 10


def is_applied(db, cfg):
    """Check if THIS migration has been applied.

    Returns True if Repository.downloads column exists.
    """
    return check_column_exists(db, cfg, "repository", "downloads")


def check_migration_needed():
    """Check if this migration needs to run by checking if columns/tables exist."""
    cursor = db.cursor()

    if cfg.app.db_backend == "postgres":
        # Check if Repository.downloads exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='repository' AND column_name='downloads'
        """
        )
        return cursor.fetchone() is None
    else:
        # SQLite: Check via PRAGMA
        cursor.execute("PRAGMA table_info(repository)")
        columns = [row[1] for row in cursor.fetchall()]
        return "downloads" not in columns


def migrate_sqlite():
    """Migrate SQLite database.

    Note: This function runs inside a transaction (db.atomic()).
    Do NOT call db.commit() or db.rollback() inside this function.
    """
    cursor = db.cursor()

    # Add columns to Repository table
    for column, sql in [
        (
            "downloads",
            "ALTER TABLE repository ADD COLUMN downloads INTEGER DEFAULT 0",
        ),
        (
            "likes_count",
            "ALTER TABLE repository ADD COLUMN likes_count INTEGER DEFAULT 0",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  [OK] Added Repository.{column}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  - Repository.{column} already exists")
            else:
                raise

    # Create RepositoryLike table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS repositorylike (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """
        )
        print("  [OK] Created RepositoryLike table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS repositorylike_repository_id ON repositorylike(repository_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS repositorylike_user_id ON repositorylike(user_id)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS repositorylike_repository_user ON repositorylike(repository_id, user_id)"
        )
        print("  [OK] Created RepositoryLike indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - RepositoryLike table already exists")
        else:
            raise

    # Create DownloadSession table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS downloadsession (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                user_id INTEGER,
                session_id VARCHAR(255) NOT NULL,
                time_bucket INTEGER NOT NULL,
                file_count INTEGER DEFAULT 1,
                first_file VARCHAR(255) NOT NULL,
                first_download_at DATETIME NOT NULL,
                last_download_at DATETIME NOT NULL,
                FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL
            )
        """
        )
        print("  [OK] Created DownloadSession table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_repository_id ON downloadsession(repository_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_user_id ON downloadsession(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_session_id ON downloadsession(session_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_time_bucket ON downloadsession(time_bucket)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_first_download_at ON downloadsession(first_download_at)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS downloadsession_dedup ON downloadsession(repository_id, session_id, time_bucket)"
        )
        print("  [OK] Created DownloadSession indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - DownloadSession table already exists")
        else:
            raise

    # Create DailyRepoStats table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dailyrepostats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                date DATE NOT NULL,
                download_sessions INTEGER DEFAULT 0,
                authenticated_downloads INTEGER DEFAULT 0,
                anonymous_downloads INTEGER DEFAULT 0,
                total_files INTEGER DEFAULT 0,
                created_at DATETIME NOT NULL,
                FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE
            )
        """
        )
        print("  [OK] Created DailyRepoStats table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS dailyrepostats_repository_id ON dailyrepostats(repository_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS dailyrepostats_date ON dailyrepostats(date)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS dailyrepostats_repo_date ON dailyrepostats(repository_id, date)"
        )
        print("  [OK] Created DailyRepoStats indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - DailyRepoStats table already exists")
        else:
            raise


def migrate_postgres():
    """Migrate PostgreSQL database.

    Note: This function runs inside a transaction (db.atomic()).
    Do NOT call db.commit() or db.rollback() inside this function.
    """
    cursor = db.cursor()

    # Add columns to Repository table
    for column, sql in [
        (
            "downloads",
            "ALTER TABLE repository ADD COLUMN downloads INTEGER DEFAULT 0",
        ),
        (
            "likes_count",
            "ALTER TABLE repository ADD COLUMN likes_count INTEGER DEFAULT 0",
        ),
    ]:
        try:
            cursor.execute(sql)
            print(f"  [OK] Added Repository.{column}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  - Repository.{column} already exists")
            else:
                raise

    # Create RepositoryLike table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS repositorylike (
                id SERIAL PRIMARY KEY,
                repository_id INTEGER NOT NULL REFERENCES repository(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL
            )
        """
        )
        print("  [OK] Created RepositoryLike table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS repositorylike_repository_id ON repositorylike(repository_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS repositorylike_user_id ON repositorylike(user_id)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS repositorylike_repository_user ON repositorylike(repository_id, user_id)"
        )
        print("  [OK] Created RepositoryLike indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - RepositoryLike table already exists")
        else:
            raise

    # Create DownloadSession table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS downloadsession (
                id SERIAL PRIMARY KEY,
                repository_id INTEGER NOT NULL REFERENCES repository(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                session_id VARCHAR(255) NOT NULL,
                time_bucket INTEGER NOT NULL,
                file_count INTEGER DEFAULT 1,
                first_file VARCHAR(255) NOT NULL,
                first_download_at TIMESTAMP NOT NULL,
                last_download_at TIMESTAMP NOT NULL
            )
        """
        )
        print("  [OK] Created DownloadSession table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_repository_id ON downloadsession(repository_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_user_id ON downloadsession(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_session_id ON downloadsession(session_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_time_bucket ON downloadsession(time_bucket)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS downloadsession_first_download_at ON downloadsession(first_download_at)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS downloadsession_dedup ON downloadsession(repository_id, session_id, time_bucket)"
        )
        print("  [OK] Created DownloadSession indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - DownloadSession table already exists")
        else:
            raise

    # Create DailyRepoStats table
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dailyrepostats (
                id SERIAL PRIMARY KEY,
                repository_id INTEGER NOT NULL REFERENCES repository(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                download_sessions INTEGER DEFAULT 0,
                authenticated_downloads INTEGER DEFAULT 0,
                anonymous_downloads INTEGER DEFAULT 0,
                total_files INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL
            )
        """
        )
        print("  [OK] Created DailyRepoStats table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS dailyrepostats_repository_id ON dailyrepostats(repository_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS dailyrepostats_date ON dailyrepostats(date)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS dailyrepostats_repo_date ON dailyrepostats(repository_id, date)"
        )
        print("  [OK] Created DailyRepoStats indexes")

    except Exception as e:
        if "already exists" in str(e).lower():
            print("  - DailyRepoStats table already exists")
        else:
            raise


def run():
    """Run this migration.

    IMPORTANT: Do NOT call db.close() in finally block!
    The db connection is managed by run_migrations.py and should stay open
    across all migrations to avoid stdout/stderr closure issues on Windows.
    """
    db.connect(reuse_if_open=True)

    try:
        # Pre-flight checks (outside transaction for performance)
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 010: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 010: Already applied (columns exist)")
            return True

        print("Migration 010: Adding likes and download tracking system...")

        # Run migration in a transaction - will auto-rollback on exception
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                migrate_postgres()
            else:
                migrate_sqlite()

        print("Migration 010: [OK] Completed")
        return True

    except Exception as e:
        # Transaction automatically rolled back if we reach here
        print(f"Migration 010: [FAILED] {e}")
        print("  All changes have been rolled back")
        import traceback

        traceback.print_exc()
        return False
    # NOTE: No finally block - db connection stays open


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
