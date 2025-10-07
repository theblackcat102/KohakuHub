"""Migration: Add Commit table for tracking user commits.

This migration adds the Commit table to track which KohakuHub user made each commit.
LakeFS doesn't track the actual user (it only sees the KohakuHub backend), so we
need our own tracking table.

Run this migration after upgrading to a version that includes commit tracking.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kohakuhub.db import Commit, db


def migrate():
    """Add Commit table to database."""
    db.connect()

    print("Checking if Commit table exists...")

    # Check if table already exists
    if db.table_exists("commit"):
        print("✓ Commit table already exists, skipping migration")
        return

    print("Creating Commit table...")

    # Create table
    db.create_tables([Commit], safe=True)

    print("✓ Commit table created successfully!")
    print("\nTable structure:")
    print("  - commit_id: LakeFS commit SHA")
    print("  - repo_full_id: Repository (namespace/name)")
    print("  - repo_type: model/dataset/space")
    print("  - branch: Branch name")
    print("  - user_id: KohakuHub user ID who made the commit")
    print("  - username: Username (denormalized)")
    print("  - message: Commit message")
    print("  - description: Commit description")
    print("  - created_at: Timestamp")
    print("\nIndexes:")
    print("  - (commit_id, repo_full_id): Unique commit per repo")
    print("  - (repo_full_id, branch): Query commits by repo+branch")
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
