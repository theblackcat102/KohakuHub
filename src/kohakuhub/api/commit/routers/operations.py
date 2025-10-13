"""Commit creation endpoint - Refactored version with smaller functions."""

from datetime import datetime, timezone
from enum import Enum
import asyncio
import base64
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request

from kohakuhub.config import cfg
from kohakuhub.db import File, Organization, Repository, User
from kohakuhub.db_operations import (
    create_commit,
    create_file,
    delete_file,
    get_file,
    update_file,
)
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_current_user
from kohakuhub.auth.permissions import check_repo_write_permission
from kohakuhub.utils.lakefs import get_lakefs_client, lakefs_repo_name
from kohakuhub.utils.s3 import get_object_metadata, object_exists
from kohakuhub.api.quota.util import update_namespace_storage
from kohakuhub.api.repo.utils.gc import run_gc_for_file, track_lfs_object

logger = get_logger("FILE")
router = APIRouter()


class RepoType(str, Enum):
    """Repository type enumeration."""

    model = "model"
    dataset = "dataset"
    space = "space"


def calculate_git_blob_sha1(content: bytes) -> str:
    """Calculate SHA1 hash in git blob format.

    Git uses: sha1(f'blob {size}\\0' + content)

    Args:
        content: File content bytes

    Returns:
        SHA1 hex digest
    """
    size = len(content)
    sha = hashlib.sha1()
    sha.update(f"blob {size}\0".encode("utf-8"))
    sha.update(content)
    return sha.hexdigest()


async def process_regular_file(
    path: str,
    content_b64: str,
    encoding: str,
    repo_id: str,
    lakefs_repo: str,
    revision: str,
) -> bool:
    """Process regular file with inline base64 content.

    IMPORTANT: This should only be used for small files (< LFS threshold).
    Large files MUST use the lfsFile operation to avoid duplication.

    Args:
        path: File path in repository
        content_b64: Base64 encoded content
        encoding: Content encoding
        repo_id: Repository ID
        lakefs_repo: LakeFS repository name
        revision: Branch name

    Returns:
        True if file was changed, False if unchanged

    Raises:
        HTTPException: If processing fails or file is too large for standard commit
    """
    if not encoding.startswith("base64"):
        raise HTTPException(400, detail={"error": f"Invalid file operation for {path}"})

    # Decode content
    try:
        data = base64.b64decode(content_b64)
    except Exception as e:
        raise HTTPException(400, detail={"error": f"Failed to decode base64: {e}"})

    # Check file size against LFS threshold
    file_size = len(data)
    lfs_threshold = cfg.app.lfs_threshold_bytes

    if file_size >= lfs_threshold:
        # File is too large for standard commit - must use LFS workflow
        raise HTTPException(
            400,
            detail={
                "error": f"File {path} is too large ({file_size} bytes) for standard commit. "
                f"Files >= {lfs_threshold} bytes must be uploaded through Git LFS. "
                f"Use 'lfsFile' operation instead of 'file' operation.",
                "file_size": file_size,
                "lfs_threshold": lfs_threshold,
                "suggested_operation": "lfsFile",
            },
        )

    # Calculate git blob SHA1 for non-LFS files (HuggingFace format)
    git_blob_sha1 = calculate_git_blob_sha1(data)

    # Check if file unchanged (deduplication)
    existing = get_file(repo_id, path)
    if existing and existing.sha256 == git_blob_sha1 and existing.size == len(data):
        logger.info(f"Skipping unchanged file: {path}")
        return False

    # File changed, need to upload
    logger.info(f"Uploading regular file: {path} ({file_size} bytes)")

    # Upload to LakeFS
    try:
        client = get_lakefs_client()
        await client.upload_object(
            repository=lakefs_repo,
            branch=revision,
            path=path,
            content=data,
        )
    except Exception as e:
        raise HTTPException(500, detail={"error": f"Failed to upload {path}: {e}"})

    # Update database - store git blob SHA1 in sha256 column for non-LFS files
    File.insert(
        repo_full_id=repo_id,
        path_in_repo=path,
        size=len(data),
        sha256=git_blob_sha1,
        lfs=False,
    ).on_conflict(
        conflict_target=(File.repo_full_id, File.path_in_repo),
        update={
            File.sha256: git_blob_sha1,
            File.size: len(data),
            File.lfs: False,  # Explicitly set to False
            File.updated_at: datetime.now(timezone.utc),
        },
    ).execute()

    return True


async def process_lfs_file(
    path: str,
    oid: str,
    size: int,
    algo: str,
    repo_id: str,
    lakefs_repo: str,
    revision: str,
) -> tuple[bool, dict | None]:
    """Process LFS file that was uploaded to S3.

    Args:
        path: File path in repository
        oid: Object ID (SHA256 hash)
        size: File size in bytes
        algo: Hash algorithm (default: sha256)
        repo_id: Repository ID
        lakefs_repo: LakeFS repository name
        revision: Branch name

    Returns:
        Tuple of (changed: bool, lfs_tracking_info: dict | None)

    Raises:
        HTTPException: If processing fails
    """
    if not oid:
        raise HTTPException(400, detail={"error": f"Missing OID for LFS file {path}"})

    # Check for existing file
    existing = get_file(repo_id, path)

    # Track old LFS object for potential deletion
    old_lfs_oid = None
    if existing and existing.lfs and existing.sha256 != oid:
        old_lfs_oid = existing.sha256
        logger.info(f"File {path} will be replaced: {old_lfs_oid} → {oid}")

    # Check if file unchanged
    if existing and existing.sha256 == oid and existing.size == size:
        logger.info(f"Skipping unchanged LFS file: {path}")
        return False, None

    # File changed or new
    logger.info(f"Linking LFS file: {path}")

    # Construct S3 physical address
    lfs_key = f"lfs/{oid[:2]}/{oid[2:4]}/{oid}"
    physical_address = f"s3://{cfg.s3.bucket}/{lfs_key}"

    # Verify object exists in S3
    if not await object_exists(cfg.s3.bucket, lfs_key):
        raise HTTPException(
            400,
            detail={
                "error": f"LFS object {oid} not found in storage. "
                f"Upload to S3 may have failed. Path: {lfs_key}"
            },
        )

    # Get actual size from S3 to verify
    try:
        s3_metadata = await get_object_metadata(cfg.s3.bucket, lfs_key)
        actual_size = s3_metadata["size"]

        if actual_size != size:
            logger.warning(
                f"Size mismatch for {path}. Expected: {size}, Got: {actual_size}"
            )
            size = actual_size
    except Exception as e:
        logger.exception(f"Failed to get S3 object metadata", e)
        logger.warning(f"Could not verify S3 object metadata: {e}")

    # Link the physical S3 object to LakeFS
    try:
        staging_metadata = {
            "staging": {
                "physical_address": physical_address,
            },
            "checksum": f"{algo}:{oid}",
            "size_bytes": size,
        }

        client = get_lakefs_client()
        await client.link_physical_address(
            repository=lakefs_repo,
            branch=revision,
            path=path,
            staging_metadata=staging_metadata,
        )

        logger.success(f"Successfully linked LFS file in LakeFS: {path}")

    except Exception as e:
        logger.exception(f"Failed to link LFS file in LakeFS: {path}", e)
        raise HTTPException(
            500,
            detail={"error": f"Failed to link LFS file {path} in LakeFS: {str(e)}"},
        )

    # Update database
    File.insert(
        repo_full_id=repo_id,
        path_in_repo=path,
        size=size,
        sha256=oid,
        lfs=True,
    ).on_conflict(
        conflict_target=(File.repo_full_id, File.path_in_repo),
        update={
            File.sha256: oid,
            File.size: size,
            File.lfs: True,
            File.updated_at: datetime.now(timezone.utc),
        },
    ).execute()

    logger.success(f"Updated database record for LFS file: {path}")

    # Return tracking info for GC
    return True, {
        "path": path,
        "sha256": oid,
        "size": size,
        "old_sha256": old_lfs_oid,
    }


async def process_deleted_file(
    path: str, repo_id: str, lakefs_repo: str, revision: str
) -> bool:
    """Process file deletion.

    Args:
        path: File path to delete
        repo_id: Repository ID
        lakefs_repo: LakeFS repository name
        revision: Branch name

    Returns:
        True (always changes repository)
    """
    logger.info(f"Deleting file: {path}")

    try:
        client = get_lakefs_client()
        await client.delete_object(repository=lakefs_repo, branch=revision, path=path)
        logger.success(f"Successfully deleted file from LakeFS: {path}")
    except Exception as e:
        # File might not exist, log warning but continue
        logger.warning(f"Failed to delete {path} from LakeFS: {e}")

    # Remove from database
    deleted_count = (
        File.delete()
        .where((File.repo_full_id == repo_id) & (File.path_in_repo == path))
        .execute()
    )

    if deleted_count > 0:
        logger.success(f"Removed {path} from database")
    else:
        logger.info(f"File {path} was not in database")

    return True


async def process_deleted_folder(
    path: str, repo_id: str, lakefs_repo: str, revision: str
) -> bool:
    """Process folder deletion.

    Args:
        path: Folder path to delete
        repo_id: Repository ID
        lakefs_repo: LakeFS repository name
        revision: Branch name

    Returns:
        True (always changes repository)
    """
    # Normalize folder path
    folder_path = path if path.endswith("/") else f"{path}/"
    logger.info(f"Deleting folder: {folder_path}")

    try:
        client = get_lakefs_client()

        # List all objects in the folder with pagination
        all_folder_objects = []
        after = ""
        has_more = True

        while has_more:
            objects = await client.list_objects(
                repository=lakefs_repo,
                ref=revision,
                prefix=folder_path,
                delimiter="",
                amount=1000,
                after=after,
            )

            all_folder_objects.extend(objects["results"])

            if objects.get("pagination") and objects["pagination"].get("has_more"):
                after = objects["pagination"]["next_offset"]
                has_more = True
            else:
                has_more = False

        # Delete each file concurrently
        file_objects = [
            obj for obj in all_folder_objects if obj["path_type"] == "object"
        ]

        async def delete_file_obj(obj):
            try:
                await client.delete_object(
                    repository=lakefs_repo, branch=revision, path=obj["path"]
                )
                logger.info(f"  Deleted: {obj['path']}")
                return obj["path"]
            except Exception as e:
                logger.warning(f"  Failed to delete {obj['path']}: {e}")
                return None

        results = await asyncio.gather(*[delete_file_obj(obj) for obj in file_objects])
        deleted_files = [path for path in results if path is not None]

        logger.success(f"Deleted {len(deleted_files)} files from folder {folder_path}")

        # Remove from database
        if deleted_files:
            deleted_count = (
                File.delete()
                .where(
                    (File.repo_full_id == repo_id)
                    & (File.path_in_repo.startswith(folder_path))
                )
                .execute()
            )
            logger.success(f"Removed {deleted_count} records from database")

    except Exception as e:
        logger.warning(f"Error deleting folder {folder_path}: {e}")

    return True


async def process_copy_file(
    dest_path: str,
    src_path: str,
    src_revision: str,
    repo_id: str,
    lakefs_repo: str,
    revision: str,
) -> bool:
    """Process file copy operation.

    Args:
        dest_path: Destination file path
        src_path: Source file path
        src_revision: Source revision
        repo_id: Repository ID
        lakefs_repo: LakeFS repository name
        revision: Branch name

    Returns:
        True (always changes repository)

    Raises:
        HTTPException: If copy fails
    """
    if not src_path:
        raise HTTPException(
            400, detail={"error": f"Missing srcPath for copyFile operation"}
        )

    logger.info(
        f"Copying file: {src_path} -> {dest_path} (from revision: {src_revision})"
    )

    try:
        # Get source file metadata from LakeFS
        client = get_lakefs_client()
        src_obj = await client.stat_object(
            repository=lakefs_repo, ref=src_revision, path=src_path
        )

        # Use LakeFS staging API to link the physical address
        staging_metadata = {
            "staging": {
                "physical_address": src_obj["physical_address"],
            },
            "checksum": src_obj["checksum"],
            "size_bytes": src_obj["size_bytes"],
        }

        await client.link_physical_address(
            repository=lakefs_repo,
            branch=revision,
            path=dest_path,
            staging_metadata=staging_metadata,
        )

        logger.success(
            f"Successfully linked {dest_path} to same physical address as {src_path}"
        )

        # Update database - copy file metadata
        src_file = get_file(repo_id, src_path)

        if src_file:
            File.insert(
                repo_full_id=repo_id,
                path_in_repo=dest_path,
                size=src_file.size,
                sha256=src_file.sha256,
                lfs=src_file.lfs,
            ).on_conflict(
                conflict_target=(File.repo_full_id, File.path_in_repo),
                update={
                    File.sha256: src_file.sha256,
                    File.size: src_file.size,
                    File.lfs: src_file.lfs,
                    File.updated_at: datetime.now(timezone.utc),
                },
            ).execute()
        else:
            # If not in database, create entry based on LakeFS info
            is_lfs = src_obj["size_bytes"] >= cfg.app.lfs_threshold_bytes
            File.insert(
                repo_full_id=repo_id,
                path_in_repo=dest_path,
                size=src_obj["size_bytes"],
                sha256=src_obj["checksum"],
                lfs=is_lfs,
            ).on_conflict(
                conflict_target=(File.repo_full_id, File.path_in_repo),
                update={
                    File.sha256: src_obj["checksum"],
                    File.size: src_obj["size_bytes"],
                    File.lfs: is_lfs,
                    File.updated_at: datetime.now(timezone.utc),
                },
            ).execute()

        logger.success(f"Successfully copied {src_path} to {dest_path}")

    except Exception as e:
        raise HTTPException(
            500,
            detail={
                "error": f"Failed to copy file {src_path} to {dest_path}: {str(e)}"
            },
        )

    return True


@router.post("/{repo_type}s/{namespace}/{name}/commit/{revision}")
async def commit(
    repo_type: RepoType,
    namespace: str,
    name: str,
    revision: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Create atomic commit with multiple file operations.

    Accepts NDJSON payload with header and file operations.
    Supports inline base64 content for small files and LFS references for large files.

    Args:
        repo_type: Type of repository
        namespace: Repository namespace
        name: Repository name
        revision: Branch name
        request: FastAPI request with NDJSON payload
        user: Current authenticated user

    Returns:
        Commit result with OID and URL

    Raises:
        HTTPException: If commit fails
    """
    repo_id = f"{namespace}/{name}"

    # Check repository exists and write permission
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type.value)
    )
    if not repo_row:
        raise HTTPException(404, detail={"error": "Repository not found"})

    check_repo_write_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type.value, repo_id)
    client = get_lakefs_client()

    # Parse NDJSON payload
    raw = await request.body()
    lines = raw.decode("utf-8").splitlines()

    if cfg.app.debug_log_payloads:
        logger.debug("==== Commit Payload ====")
        for line in lines:
            logger.debug(line)

    # Parse header and operations
    header = None
    operations = []

    for line in lines:
        if not line.strip():
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise HTTPException(400, detail={"error": f"Invalid JSON line: {e}"})

        key = obj.get("key")
        value = obj.get("value", {})

        if key == "header":
            header = value
        elif key in ("file", "lfsFile", "deletedFile", "deletedFolder", "copyFile"):
            operations.append({"key": key, "value": value})

    if header is None:
        raise HTTPException(400, detail={"error": "Missing commit header"})

    # Process operations using match-case
    files_changed = False
    pending_lfs_tracking = []

    for op in operations:
        key = op["key"]
        value = op["value"]
        path = value.get("path")
        logger.info(f"Processing {key}: {path}")

        match key:
            case "file":
                # Regular file with inline content
                changed = await process_regular_file(
                    path=path,
                    content_b64=value.get("content"),
                    encoding=(value.get("encoding") or "").lower(),
                    repo_id=repo_id,
                    lakefs_repo=lakefs_repo,
                    revision=revision,
                )
                files_changed = files_changed or changed

            case "lfsFile":
                # LFS file already in S3
                changed, lfs_info = await process_lfs_file(
                    path=path,
                    oid=value.get("oid"),
                    size=value.get("size"),
                    algo=value.get("algo", "sha256"),
                    repo_id=repo_id,
                    lakefs_repo=lakefs_repo,
                    revision=revision,
                )
                files_changed = files_changed or changed
                if lfs_info:
                    pending_lfs_tracking.append(lfs_info)

            case "deletedFile":
                # Delete single file
                changed = await process_deleted_file(
                    path=path,
                    repo_id=repo_id,
                    lakefs_repo=lakefs_repo,
                    revision=revision,
                )
                files_changed = files_changed or changed

            case "deletedFolder":
                # Delete folder recursively
                changed = await process_deleted_folder(
                    path=path,
                    repo_id=repo_id,
                    lakefs_repo=lakefs_repo,
                    revision=revision,
                )
                files_changed = files_changed or changed

            case "copyFile":
                # Copy file
                changed = await process_copy_file(
                    dest_path=path,
                    src_path=value.get("srcPath"),
                    src_revision=value.get("srcRevision", revision),
                    repo_id=repo_id,
                    lakefs_repo=lakefs_repo,
                    revision=revision,
                )
                files_changed = files_changed or changed

    # If no files changed, return early
    if not files_changed:
        try:
            branch = await client.get_branch(repository=lakefs_repo, branch=revision)
            commit_id = branch["commit_id"]
        except Exception:
            commit_id = "no-changes"

        commit_url = f"{cfg.app.base_url}/{repo_id}/commit/{commit_id}"

        return {
            "commitUrl": commit_url,
            "commitOid": commit_id,
            "pullRequestUrl": None,
        }

    # Create commit in LakeFS
    commit_msg = header.get("summary", "Commit via API")
    commit_desc = header.get("description", "")
    logger.info(f"Commit message: {commit_msg}")

    try:
        commit_result = await client.commit(
            repository=lakefs_repo,
            branch=revision,
            message=commit_msg,
            metadata={"description": commit_desc} if commit_desc else None,
        )
    except Exception as e:
        raise HTTPException(500, detail={"error": f"Commit failed: {str(e)}"})

    # Record commit in our database (track the actual user)
    try:
        create_commit(
            commit_id=commit_result["id"],
            repo_full_id=repo_id,
            repo_type=repo_type,
            branch=revision,
            user_id=user.id,
            username=user.username,
            message=commit_msg,
            description=commit_desc,
        )
        logger.info(f"Recorded commit {commit_result['id'][:8]} by {user.username}")
    except Exception as e:
        logger.warning(f"Failed to record commit in database: {e}")
        # Don't fail the commit if DB recording fails

    # Generate commit URL
    commit_url = f"{cfg.app.base_url}/{repo_id}/commit/{commit_result['id']}"
    logger.success(f"Commit URL: {commit_url}")

    # Track LFS objects and run GC
    if pending_lfs_tracking:
        for lfs_info in pending_lfs_tracking:
            track_lfs_object(
                repo_full_id=repo_id,
                path_in_repo=lfs_info["path"],
                sha256=lfs_info["sha256"],
                size=lfs_info["size"],
                commit_id=commit_result["id"],
            )

            if cfg.app.lfs_auto_gc and lfs_info.get("old_sha256"):
                deleted_count = run_gc_for_file(
                    repo_full_id=repo_id,
                    path_in_repo=lfs_info["path"],
                    current_commit_id=commit_result["id"],
                )
                if deleted_count > 0:
                    logger.info(
                        f"GC: Cleaned up {deleted_count} old version(s) of {lfs_info['path']}"
                    )

    # Update storage usage for namespace after successful commit
    try:
        # Check if namespace is organization
        org = Organization.get_or_none(Organization.name == namespace)
        is_org = org is not None

        # Recalculate storage usage
        await update_namespace_storage(namespace, is_org)
        logger.debug(
            f"Updated storage usage for {'org' if is_org else 'user'} {namespace}"
        )
    except Exception as e:
        # Log error but don't fail the commit
        logger.warning(f"Failed to update storage usage for {namespace}: {e}")

    return {
        "commitUrl": commit_url,
        "commitOid": commit_result["id"],
        "pullRequestUrl": None,
    }
