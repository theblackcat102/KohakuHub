"""Garbage collection utilities for LFS objects."""

from datetime import datetime, timezone
from typing import List, Optional

from kohakuhub.config import cfg
from kohakuhub.db import File, LFSObjectHistory
from kohakuhub.logger import get_logger
from kohakuhub.db_async import execute_db_query
from kohakuhub.api.utils.s3 import get_s3_client, object_exists
from kohakuhub.api.utils.lakefs import get_lakefs_client

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


async def check_lfs_recoverability(
    repo_full_id: str, commit_id: str
) -> tuple[bool, list[str]]:
    """Check if all LFS files in a commit are still available in S3.

    Args:
        repo_full_id: Full repository ID
        commit_id: Commit ID to check

    Returns:
        Tuple of (all_recoverable: bool, missing_files: list[str])
    """
    # Get all LFS objects from this commit
    lfs_objects = list(
        LFSObjectHistory.select().where(
            (LFSObjectHistory.repo_full_id == repo_full_id)
            & (LFSObjectHistory.commit_id == commit_id)
        )
    )

    if not lfs_objects:
        # No LFS files in this commit, always recoverable
        return True, []

    missing_files = []

    for lfs_obj in lfs_objects:
        lfs_key = f"lfs/{lfs_obj.sha256[:2]}/{lfs_obj.sha256[2:4]}/{lfs_obj.sha256}"

        # Check if object exists in S3
        exists = await object_exists(cfg.s3.bucket, lfs_key)

        if not exists:
            missing_files.append(lfs_obj.path_in_repo)
            logger.warning(
                f"LFS object missing for {lfs_obj.path_in_repo}: {lfs_obj.sha256[:8]}"
            )

    all_recoverable = len(missing_files) == 0

    if all_recoverable:
        logger.info(
            f"All {len(lfs_objects)} LFS files in commit {commit_id[:8]} are recoverable"
        )
    else:
        logger.warning(
            f"{len(missing_files)} LFS files in commit {commit_id[:8]} are NOT recoverable"
        )

    return all_recoverable, missing_files


async def check_commit_range_recoverability(
    lakefs_repo: str,
    repo_full_id: str,
    target_commit: str,
    current_branch: str,
) -> tuple[bool, list[str], list[str]]:
    """Check if all LFS files in commit range (target to HEAD) are recoverable.

    For reset operations, we need to ensure all commits from target to current HEAD
    have their LFS files available, because the operation traverses this range.

    Args:
        lakefs_repo: LakeFS repository name
        repo_full_id: Full repository ID
        target_commit: Target commit to reset to
        current_branch: Current branch name

    Returns:
        Tuple of (all_recoverable: bool, missing_files: list[str], affected_commits: list[str])
    """
    client = get_lakefs_client()

    # Get all commits from target to HEAD
    try:
        commits_result = await client.log_commits(
            repository=lakefs_repo,
            ref=current_branch,
            amount=1000,  # Should be enough for most cases
        )

        commit_list = commits_result.get("results", [])

        # Find target commit in the list
        target_index = None
        for i, commit in enumerate(commit_list):
            if commit["id"] == target_commit:
                target_index = i
                break

        if target_index is None:
            logger.warning(
                f"Target commit {target_commit[:8]} not found in branch history"
            )
            return False, [], []

        # Check all commits from index 0 (HEAD) to target_index (inclusive)
        commits_to_check = commit_list[: target_index + 1]

        logger.info(
            f"Checking LFS recoverability for {len(commits_to_check)} commit(s) "
            f"from HEAD to {target_commit[:8]}"
        )

        all_missing_files = []
        affected_commits = []

        for commit in commits_to_check:
            commit_id = commit["id"]
            recoverable, missing = await check_lfs_recoverability(
                repo_full_id, commit_id
            )

            if not recoverable:
                all_missing_files.extend(missing)
                affected_commits.append(commit_id)

        all_recoverable = len(all_missing_files) == 0

        if all_recoverable:
            logger.success(
                f"All LFS files in {len(commits_to_check)} commit(s) are recoverable"
            )
        else:
            logger.warning(
                f"Found {len(all_missing_files)} missing LFS file(s) across "
                f"{len(affected_commits)} commit(s)"
            )

        return all_recoverable, all_missing_files, affected_commits

    except Exception as e:
        logger.exception(f"Failed to check commit range recoverability", e)
        return False, [], []


async def sync_file_table_with_commit(
    lakefs_repo: str,
    ref: str,
    repo_full_id: str,
) -> int:
    """Sync File table with actual commit state (for reset operations).

    After a reset, the branch points to an old commit, but the File table
    may still have entries from the newer state. This function syncs the
    File table to match the actual commit state.

    Args:
        lakefs_repo: LakeFS repository name
        ref: Branch name or commit ID to sync to
        repo_full_id: Full repository ID (namespace/name)

    Returns:
        Number of files synced
    """
    client = get_lakefs_client()

    try:
        # Get commit ID from ref
        # For reset operations, ref is the branch name, but we should list using commit ID
        # to avoid issues with uncommitted changes
        branch_info = await client.get_branch(repository=lakefs_repo, branch=ref)
        commit_id = branch_info["commit_id"]

        # Get ALL objects at the commit (use commit ID to avoid staging issues)
        list_result = await client.list_objects(
            repository=lakefs_repo,
            ref=commit_id,  # Use commit ID, not branch name!
            amount=10000,  # Large enough for most repos
        )

        all_objects = list_result.get("results", [])
        logger.info(
            f"Syncing {len(all_objects)} file(s) from ref {ref} (commit {commit_id[:8]})"
        )

        synced_count = 0
        file_paths = []

        for obj in all_objects:
            if obj.get("path_type") != "object":
                continue

            path = obj["path"]
            file_paths.append(path)
            size_bytes = obj.get("size_bytes", 0)
            checksum = obj.get("checksum", "")

            # Extract SHA256 from checksum
            if ":" in checksum:
                sha256 = checksum.split(":", 1)[1]
            else:
                sha256 = checksum

            is_lfs = size_bytes >= cfg.app.lfs_threshold_bytes

            logger.debug(
                f"Syncing file: {path} (size={size_bytes}, lfs={is_lfs}, sha256={sha256[:8]})"
            )

            # Update File table
            File.insert(
                repo_full_id=repo_full_id,
                path_in_repo=path,
                size=size_bytes,
                sha256=sha256,
                lfs=is_lfs,
            ).on_conflict(
                conflict_target=(File.repo_full_id, File.path_in_repo),
                update={
                    File.sha256: sha256,
                    File.size: size_bytes,
                    File.lfs: is_lfs,
                    File.updated_at: datetime.now(timezone.utc),
                },
            ).execute()

            # Track LFS objects in history
            if is_lfs:
                track_lfs_object(
                    repo_full_id=repo_full_id,
                    path_in_repo=path,
                    sha256=sha256,
                    size=size_bytes,
                    commit_id=commit_id,
                )

            synced_count += 1

        # Remove files from File table that no longer exist in commit
        def _cleanup_removed_files():
            if file_paths:
                return (
                    File.delete()
                    .where(
                        (File.repo_full_id == repo_full_id)
                        & (File.path_in_repo.not_in(file_paths))
                    )
                    .execute()
                )
            return 0

        removed_count = await execute_db_query(_cleanup_removed_files)

        if removed_count > 0:
            logger.info(f"Removed {removed_count} stale file(s) from File table")

        logger.success(
            f"Synced {synced_count} file(s) to ref {ref} (commit {commit_id[:8]})"
        )
        return synced_count

    except Exception as e:
        logger.exception(f"Failed to sync file table", e)
        return 0


async def track_commit_lfs_objects(
    lakefs_repo: str,
    commit_id: str,
    repo_full_id: str,
) -> int:
    """Track all LFS objects in a commit (after revert/merge).

    This function is called after a revert or merge operation to ensure
    all LFS objects in the new commit are tracked in history and won't
    be accidentally garbage collected.

    Args:
        lakefs_repo: LakeFS repository name
        commit_id: The new commit ID (from revert/merge)
        repo_full_id: Full repository ID (namespace/name)

    Returns:
        Number of LFS objects tracked
    """
    client = get_lakefs_client()

    # Get commit details to find parent
    try:
        commit = await client.get_commit(repository=lakefs_repo, commit_id=commit_id)
        parents = commit.get("parents", [])

        if not parents:
            logger.warning(f"Commit {commit_id[:8]} has no parents, cannot track diff")
            return 0

        parent_commit = parents[0]
        logger.info(
            f"Tracking LFS objects in commit {commit_id[:8]} (diff from {parent_commit[:8]})"
        )

        # Get diff between parent and new commit
        diff_result = await client.diff_refs(
            repository=lakefs_repo,
            left_ref=parent_commit,
            right_ref=commit_id,
        )

        tracked_count = 0
        files_to_remove = []

        for result in diff_result.get("results", []):
            path = result.get("path")
            path_type = result.get("path_type")
            diff_type = result.get("type")  # "added", "removed", "changed"

            # Skip if not an object
            if path_type != "object":
                continue

            # Handle removed files
            if diff_type == "removed":
                files_to_remove.append(path)
                logger.debug(f"File removed: {path}")
                continue

            # Get object metadata to check if it's LFS
            try:
                obj_stat = await client.stat_object(
                    repository=lakefs_repo,
                    ref=commit_id,
                    path=path,
                )

                size_bytes = obj_stat.get("size_bytes", 0)
                is_lfs = size_bytes >= cfg.app.lfs_threshold_bytes

                # Extract SHA256 from checksum (format: "sha256:hash")
                checksum = obj_stat.get("checksum", "")
                if ":" in checksum:
                    sha256 = checksum.split(":", 1)[1]
                else:
                    sha256 = checksum

                # Track LFS objects in history
                if is_lfs:
                    track_lfs_object(
                        repo_full_id=repo_full_id,
                        path_in_repo=path,
                        sha256=sha256,
                        size=size_bytes,
                        commit_id=commit_id,
                    )
                    tracked_count += 1
                    logger.debug(f"Tracked LFS object: {path} ({sha256[:8]})")

                # Update File table for BOTH LFS and regular files
                File.insert(
                    repo_full_id=repo_full_id,
                    path_in_repo=path,
                    size=size_bytes,
                    sha256=sha256,
                    lfs=is_lfs,
                ).on_conflict(
                    conflict_target=(File.repo_full_id, File.path_in_repo),
                    update={
                        File.sha256: sha256,
                        File.size: size_bytes,
                        File.lfs: is_lfs,
                        File.updated_at: datetime.now(timezone.utc),
                    },
                ).execute()

            except Exception as e:
                logger.warning(f"Failed to stat object {path}: {e}")
                continue

        # Remove deleted files from File table
        if files_to_remove:

            def _cleanup_removed_files():
                return (
                    File.delete()
                    .where(
                        (File.repo_full_id == repo_full_id)
                        & (File.path_in_repo.in_(files_to_remove))
                    )
                    .execute()
                )

            removed_count = await execute_db_query(_cleanup_removed_files)
            logger.info(f"Removed {removed_count} deleted file(s) from File table")

        if tracked_count > 0:
            logger.success(
                f"Tracked {tracked_count} LFS object(s) in commit {commit_id[:8]}"
            )

        return tracked_count

    except Exception as e:
        logger.exception(f"Failed to track commit LFS objects", e)
        return 0
