"""Garbage collection utilities for LFS objects."""

from typing import List, Optional
from datetime import datetime, timezone

from ..db import LFSObjectHistory, File
from ..config import cfg
from ..logger import get_logger

logger = get_logger("GC")


def track_lfs_object(
    repo_full_id: str,
    path_in_repo: str,
    sha256: str,
    size: int,
    commit_id: str,
):
    """Track LFS object usage in a commit.

    Args:
        repo_full_id: Full repository ID (namespace/name)
        path_in_repo: File path in repository
        sha256: LFS object SHA256 hash
        size: Object size in bytes
        commit_id: LakeFS commit ID
    """
    LFSObjectHistory.create(
        repo_full_id=repo_full_id,
        path_in_repo=path_in_repo,
        sha256=sha256,
        size=size,
        commit_id=commit_id,
    )
    logger.debug(
        f"Tracked LFS object {sha256[:8]} for {path_in_repo} in commit {commit_id[:8]}"
    )


def get_old_lfs_versions(
    repo_full_id: str,
    path_in_repo: str,
    keep_count: int,
) -> List[str]:
    """Get old LFS object hashes that should be garbage collected.

    Args:
        repo_full_id: Full repository ID
        path_in_repo: File path
        keep_count: Number of versions to keep

    Returns:
        List of SHA256 hashes to delete
    """
    # Get all historical versions for this file, sorted by creation date (newest first)
    history = (
        LFSObjectHistory.select()
        .where(
            (LFSObjectHistory.repo_full_id == repo_full_id)
            & (LFSObjectHistory.path_in_repo == path_in_repo)
        )
        .order_by(LFSObjectHistory.created_at.desc())
    )

    all_versions = list(history)

    if len(all_versions) <= keep_count:
        # Not enough versions to trigger GC
        logger.debug(
            f"Only {len(all_versions)} versions of {path_in_repo}, keeping all"
        )
        return []

    # Keep the newest K versions, delete the rest
    versions_to_keep = all_versions[:keep_count]
    versions_to_delete = all_versions[keep_count:]

    keep_hashes = {v.sha256 for v in versions_to_keep}
    delete_hashes = []

    for old_version in versions_to_delete:
        # Only delete if not in the "keep" set (shouldn't happen, but safety check)
        if old_version.sha256 not in keep_hashes:
            delete_hashes.append(old_version.sha256)

    logger.info(
        f"GC for {path_in_repo}: keeping {len(versions_to_keep)} versions, "
        f"marking {len(delete_hashes)} for deletion"
    )

    return delete_hashes


def cleanup_lfs_object(sha256: str, repo_full_id: Optional[str] = None) -> bool:
    """Delete an LFS object from S3 if it's not used anywhere.

    Args:
        sha256: LFS object hash
        repo_full_id: Optional - restrict check to specific repo

    Returns:
        True if deleted, False if still in use or deletion failed
    """
    # Check if this object is still referenced in current files
    query = File.select().where((File.sha256 == sha256) & (File.lfs == True))
    if repo_full_id:
        query = query.where(File.repo_full_id == repo_full_id)

    current_uses = query.count()

    if current_uses > 0:
        logger.debug(
            f"LFS object {sha256[:8]} still used by {current_uses} file(s), keeping"
        )
        return False

    # Check if this object is referenced in any commit history (other repos might use it)
    if not repo_full_id:
        # Global check across all repos
        history_uses = (
            LFSObjectHistory.select().where(LFSObjectHistory.sha256 == sha256).count()
        )

        if history_uses > 0:
            logger.debug(
                f"LFS object {sha256[:8]} in history ({history_uses} references), keeping"
            )
            return False

    # Safe to delete from S3
    try:
        from .s3_utils import get_s3_client

        lfs_key = f"lfs/{sha256[:2]}/{sha256[2:4]}/{sha256}"
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=cfg.s3.bucket, Key=lfs_key)

        logger.success(f"Deleted LFS object from S3: {lfs_key}")

        # Remove from history table
        if repo_full_id:
            deleted_count = (
                LFSObjectHistory.delete()
                .where(
                    (LFSObjectHistory.repo_full_id == repo_full_id)
                    & (LFSObjectHistory.sha256 == sha256)
                )
                .execute()
            )
        else:
            deleted_count = (
                LFSObjectHistory.delete()
                .where(LFSObjectHistory.sha256 == sha256)
                .execute()
            )

        logger.info(f"Removed {deleted_count} history records for {sha256[:8]}")
        return True

    except Exception as e:
        logger.exception(f"Failed to delete LFS object {sha256[:8]}", e)
        return False


def run_gc_for_file(
    repo_full_id: str,
    path_in_repo: str,
    current_commit_id: str,
) -> int:
    """Run garbage collection for a specific file.

    Args:
        repo_full_id: Full repository ID
        path_in_repo: File path
        current_commit_id: Current commit ID

    Returns:
        Number of objects deleted
    """
    if not cfg.app.lfs_auto_gc:
        logger.debug("Auto GC disabled, skipping")
        return 0

    keep_count = cfg.app.lfs_keep_versions
    old_hashes = get_old_lfs_versions(repo_full_id, path_in_repo, keep_count)

    if not old_hashes:
        return 0

    deleted_count = 0
    for sha256 in old_hashes:
        if cleanup_lfs_object(sha256, repo_full_id):
            deleted_count += 1

    if deleted_count > 0:
        logger.success(
            f"GC completed for {path_in_repo}: deleted {deleted_count} old version(s)"
        )

    return deleted_count
