"""Repository tree listing and path information endpoints - Refactored version."""

import asyncio
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Form

from kohakuhub.api.repo.utils.hf import (
    hf_repo_not_found,
    hf_revision_not_found,
    hf_server_error,
    is_lakefs_not_found_error,
    is_lakefs_revision_error,
)
from kohakuhub.utils.lakefs import get_lakefs_client, lakefs_repo_name
from kohakuhub.auth.dependencies import get_optional_user
from kohakuhub.auth.permissions import check_repo_read_permission
from kohakuhub.config import cfg
from kohakuhub.db_async import execute_db_query, get_file
from kohakuhub.db import File, Repository, User
from kohakuhub.logger import get_logger

logger = get_logger("REPO")
router = APIRouter()

RepoType = Literal["model", "dataset", "space"]


async def fetch_lakefs_objects(
    lakefs_repo: str, revision: str, prefix: str, recursive: bool
) -> list:
    """Fetch all objects from LakeFS with pagination.

    Args:
        lakefs_repo: LakeFS repository name
        revision: Branch or commit
        prefix: Path prefix
        recursive: Whether to list recursively

    Returns:
        List of all LakeFS objects

    Raises:
        Exception: If listing fails
    """
    client = get_lakefs_client()

    all_results = []
    after = ""
    has_more = True

    while has_more:
        result = await client.list_objects(
            repository=lakefs_repo,
            ref=revision,
            prefix=prefix,
            delimiter="" if recursive else "/",
            amount=1000,  # Max per request
            after=after,
        )

        all_results.extend(result["results"])

        # Check pagination
        if result.get("pagination") and result["pagination"].get("has_more"):
            after = result["pagination"]["next_offset"]
            has_more = True
        else:
            has_more = False

    return all_results


async def calculate_folder_stats(
    lakefs_repo: str, revision: str, folder_path: str
) -> tuple[int, float | None]:
    """Calculate folder size and latest modification time.

    Args:
        lakefs_repo: LakeFS repository name
        revision: Branch or commit
        folder_path: Full folder path

    Returns:
        Tuple of (total_size, latest_mtime)
    """
    folder_size = 0
    folder_latest_mtime = None

    try:
        client = get_lakefs_client()
        folder_contents = await client.list_objects(
            repository=lakefs_repo,
            ref=revision,
            prefix=folder_path,
            delimiter="",  # No delimiter = recursive
            amount=1000,
        )

        # Calculate total size and find latest modification
        for child_obj in folder_contents["results"]:
            if child_obj["path_type"] == "object":
                folder_size += child_obj.get("size_bytes") or 0
                if child_obj.get("mtime"):
                    if (
                        folder_latest_mtime is None
                        or child_obj["mtime"] > folder_latest_mtime
                    ):
                        folder_latest_mtime = child_obj["mtime"]

    except Exception as e:
        logger.debug(f"Could not calculate stats for folder {folder_path}: {str(e)}")

    return folder_size, folder_latest_mtime


async def convert_file_object(obj, repo_id: str, prefix_len: int) -> dict:
    """Convert LakeFS file object to HuggingFace format.

    Args:
        obj: LakeFS object dict
        repo_id: Repository ID
        prefix_len: Length of path prefix to remove

    Returns:
        HuggingFace formatted file object
    """
    is_lfs = obj["size_bytes"] > cfg.app.lfs_threshold_bytes

    # Remove prefix from path to get relative path
    relative_path = obj["path"][prefix_len:] if prefix_len else obj["path"]

    # Get correct checksum from database
    file_record = await get_file(repo_id, obj["path"])

    checksum = (
        file_record.sha256 if file_record and file_record.sha256 else obj["checksum"]
    )

    file_obj = {
        "type": "file",
        "oid": checksum,  # Git blob SHA1 for non-LFS, SHA256 for LFS
        "size": obj["size_bytes"],
        "path": relative_path,
    }

    # Add last modified info if available
    if obj.get("mtime"):
        file_obj["lastModified"] = datetime.fromtimestamp(obj["mtime"]).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    # Add LFS metadata if it's an LFS file
    if is_lfs:
        file_obj["lfs"] = {
            "oid": checksum,  # SHA256 for LFS files
            "size": obj["size_bytes"],
            "pointerSize": 134,  # Standard Git LFS pointer size
        }

    return file_obj


async def convert_directory_object(
    obj, lakefs_repo: str, revision: str, prefix_len: int
) -> dict:
    """Convert LakeFS directory object to HuggingFace format.

    Args:
        obj: LakeFS common_prefix object dict
        lakefs_repo: LakeFS repository name
        revision: Branch or commit
        prefix_len: Length of path prefix to remove

    Returns:
        HuggingFace formatted directory object
    """
    # Remove prefix from path to get relative path
    relative_path = obj["path"][prefix_len:] if prefix_len else obj["path"]

    # Calculate folder stats
    folder_size, folder_latest_mtime = await calculate_folder_stats(
        lakefs_repo, revision, obj["path"]
    )

    dir_obj = {
        "type": "directory",
        "oid": obj.get("checksum", ""),
        "size": folder_size,
        "path": relative_path.rstrip("/"),  # Remove trailing slash
    }

    # Add last modified info
    if folder_latest_mtime:
        dir_obj["lastModified"] = datetime.fromtimestamp(folder_latest_mtime).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    elif obj.get("mtime"):
        dir_obj["lastModified"] = datetime.fromtimestamp(obj["mtime"]).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    return dir_obj


@router.get("/{repo_type}s/{namespace}/{repo_name}/tree/{revision}{path:path}")
async def list_repo_tree(
    repo_type: RepoType,
    namespace: str,
    repo_name: str,
    revision: str = "main",
    path: str = "",
    recursive: bool = False,
    expand: bool = False,
    user: User | None = Depends(get_optional_user),
):
    """List repository file tree.

    Returns a flat list of files and folders in HuggingFace format.

    Args:
        repo_type: Type of repository
        namespace: Repository namespace
        repo_name: Repository name
        revision: Branch name or commit hash (default: "main")
        path: Path within repository (default: root)
        recursive: List recursively (default: False)
        expand: Include detailed metadata (default: False)
        user: Current authenticated user (optional)

    Returns:
        Flat list of file/folder objects
    """
    # Construct full repo ID
    repo_id = f"{namespace}/{repo_name}"

    # Check if repository exists
    def _get_repo():
        return Repository.get_or_none(
            (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
        )

    repo_row = await execute_db_query(_get_repo)

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check read permission for private repos
    check_repo_read_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)

    # Clean path - ensure it ends with / if not empty
    prefix = path.lstrip("/") if path and path != "/" else ""
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    # Fetch all objects from LakeFS
    try:
        all_results = await fetch_lakefs_objects(
            lakefs_repo, revision, prefix, recursive
        )
    except Exception as e:
        # Check for specific error types
        if is_lakefs_not_found_error(e):
            if is_lakefs_revision_error(e):
                return hf_revision_not_found(repo_id, revision)
            else:
                # Return empty list for non-existent paths
                return []

        # Other errors are server errors
        logger.exception(f"Failed to list objects for {repo_id}", e)
        return hf_server_error(f"Failed to list objects: {str(e)}")

    # Convert LakeFS objects to HuggingFace format
    result_list = []
    prefix_len = len(prefix)

    for obj in all_results:
        match obj["path_type"]:
            case "object":
                # File object
                file_obj = await convert_file_object(obj, repo_id, prefix_len)
                result_list.append(file_obj)

            case "common_prefix":
                # Directory object
                dir_obj = await convert_directory_object(
                    obj, lakefs_repo, revision, prefix_len
                )
                result_list.append(dir_obj)

    return result_list


@router.post("/{repo_type}s/{namespace}/{repo_name}/paths-info/{revision}")
async def get_paths_info(
    repo_type: str,
    namespace: str,
    repo_name: str,
    revision: str,
    paths: list[str] = Form(...),
    expand: bool = Form(False),
    user: User | None = Depends(get_optional_user),
):
    """Get information about specific paths in a repository.

    This endpoint matches HuggingFace Hub API format.

    Args:
        repo_type: Type of repository (model/dataset/space)
        namespace: Repository namespace
        repo_name: Repository name
        revision: Branch name or commit hash
        paths: List of paths to get information about
        expand: Whether to fetch extended metadata
        user: Current authenticated user (optional)

    Returns:
        List of path information objects (files and folders)
    """
    # Construct full repo ID
    repo_id = f"{namespace}/{repo_name}"

    # Check if repository exists
    def _get_repo():
        return Repository.get_or_none(
            (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
        )

    repo_row = await execute_db_query(_get_repo)

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check read permission for private repos
    check_repo_read_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)

    # Helper function to process a single path
    async def process_path(path: str) -> dict | None:
        """Process single path and return its info, or None if path doesn't exist."""
        clean_path = path.lstrip("/")

        try:
            # Try to get object stats
            client = get_lakefs_client()
            obj_stats = await client.stat_object(
                repository=lakefs_repo,
                ref=revision,
                path=clean_path,
            )

            # It's a file
            is_lfs = obj_stats["size_bytes"] > cfg.app.lfs_threshold_bytes

            # Get correct checksum from database
            file_record = await get_file(repo_id, clean_path)

            checksum = (
                file_record.sha256
                if file_record and file_record.sha256
                else obj_stats["checksum"]
            )

            file_info = {
                "type": "file",
                "path": clean_path,
                "size": obj_stats["size_bytes"],
                "oid": checksum,  # Git blob SHA1 for non-LFS, SHA256 for LFS
                "lfs": None,
                "last_commit": None,
                "security": None,
            }

            # Add LFS metadata if applicable
            if is_lfs:
                file_info["lfs"] = {
                    "oid": checksum,  # SHA256 for LFS files
                    "size": obj_stats["size_bytes"],
                    "pointerSize": 134,
                }

            return file_info

        except Exception as e:
            # Check if it might be a directory by trying to list with prefix
            if is_lakefs_not_found_error(e):
                try:
                    # Try to list objects with this path as prefix
                    client = get_lakefs_client()
                    prefix = (
                        clean_path if clean_path.endswith("/") else clean_path + "/"
                    )
                    list_result = await client.list_objects(
                        repository=lakefs_repo,
                        ref=revision,
                        prefix=prefix,
                        amount=1,  # Just check if any objects exist
                    )

                    # If we get results, it's a directory
                    if list_result["results"]:
                        # Try to get an oid from the first result if available
                        oid = ""
                        if list_result["results"]:
                            oid = list_result["results"][0].get("checksum", "")

                        return {
                            "type": "directory",
                            "path": clean_path,
                            "oid": oid,
                            "tree_id": oid,
                            "last_commit": None,
                        }
                    # Path doesn't exist, return None
                    return None
                except Exception as ex:
                    # Path doesn't exist, skip it (as per HF behavior)
                    logger.debug(f"Path {clean_path} doesn't exist or is invalid")
                    return None
            # For other errors, also return None
            return None

    # Process all paths in parallel
    results = await asyncio.gather(*[process_path(path) for path in paths])

    # Filter out None values (paths that don't exist)
    return [r for r in results if r is not None]
