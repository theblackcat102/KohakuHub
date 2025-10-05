"""Repository tree listing and path information endpoints."""

from typing import List, Literal

from fastapi import APIRouter, Depends, Form

from kohakuhub.api.utils.hf import (
    hf_repo_not_found,
    hf_revision_not_found,
    hf_server_error,
    is_lakefs_not_found_error,
    is_lakefs_revision_error,
)
from kohakuhub.api.utils.lakefs import lakefs_repo_name
from kohakuhub.async_utils import get_async_lakefs_client
from kohakuhub.auth.dependencies import get_optional_user
from kohakuhub.auth.permissions import check_repo_read_permission
from kohakuhub.config import cfg
from kohakuhub.db import File, Repository, User
from kohakuhub.logger import get_logger

logger = get_logger("REPO")
router = APIRouter()

RepoType = Literal["model", "dataset", "space"]


@router.get("/{repo_type}s/{namespace}/{repo_name}/tree/{revision}{path:path}")
async def list_repo_tree(
    repo_type: RepoType,
    namespace: str,
    repo_name: str,
    revision: str = "main",
    path: str = "",
    recursive: bool = False,
    expand: bool = False,
    user: User = Depends(get_optional_user),
):
    """List repository file tree.

    Returns a flat list of files and folders in HuggingFace format.

    Response format matches HuggingFace API:
    [
        {
            "type": "file",  # or "directory"
            "oid": "sha256_hash",
            "size": 1234,
            "path": "relative/path/to/file.txt",
            "lfs": {"oid": "...", "size": ..., "pointerSize": ...}  # if LFS file
        },
        ...
    ]

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
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check read permission for private repos
    check_repo_read_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)

    # Clean path - ensure it ends with / if not empty
    prefix = path.lstrip("/") if path and path != "/" else ""
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    try:
        # List objects from LakeFS with pagination support
        async_client = get_async_lakefs_client()

        # Collect all results with pagination
        all_results = []
        after = ""
        has_more = True

        while has_more:
            result = await async_client.list_objects(
                repository=lakefs_repo,
                ref=revision,
                prefix=prefix,
                delimiter="" if recursive else "/",
                amount=1000,  # Max per request
                after=after,
            )

            all_results.extend(result.results)

            # Check pagination
            if result.pagination and result.pagination.has_more:
                after = result.pagination.next_offset
                has_more = True
            else:
                has_more = False

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

    # Convert LakeFS objects to HuggingFace format (flat list)
    result_list = []
    prefix_len = len(prefix)

    for obj in all_results:
        if obj.path_type == "object":
            # File object
            is_lfs = obj.size_bytes > cfg.app.lfs_threshold_bytes

            # Remove prefix from path to get relative path
            relative_path = obj.path[prefix_len:] if prefix else obj.path

            # Get correct checksum from database
            # sha256 column stores: git blob SHA1 for non-LFS, SHA256 for LFS
            file_record = File.get_or_none(
                (File.repo_full_id == repo_id) & (File.path_in_repo == obj.path)
            )

            checksum = (
                file_record.sha256
                if file_record and file_record.sha256
                else obj.checksum
            )

            file_obj = {
                "type": "file",
                "oid": checksum,  # Git blob SHA1 for non-LFS, SHA256 for LFS
                "size": obj.size_bytes,
                "path": relative_path,
            }

            # Add last modified info if available from LakeFS
            if hasattr(obj, "mtime") and obj.mtime:
                from datetime import datetime

                file_obj["lastModified"] = datetime.fromtimestamp(obj.mtime).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                )

            # Add LFS metadata if it's an LFS file
            if is_lfs:
                file_obj["lfs"] = {
                    "oid": checksum,  # SHA256 for LFS files
                    "size": obj.size_bytes,
                    "pointerSize": 134,  # Standard Git LFS pointer size
                }

            result_list.append(file_obj)

        elif obj.path_type == "common_prefix":
            # Directory object
            # Remove prefix from path to get relative path
            relative_path = obj.path[prefix_len:] if prefix else obj.path

            # Calculate folder stats by listing its contents recursively
            folder_size = 0
            folder_latest_mtime = None

            try:
                # List all objects in this folder recursively
                async_client = get_async_lakefs_client()
                folder_contents = await async_client.list_objects(
                    repository=lakefs_repo,
                    ref=revision,
                    prefix=obj.path,  # Use full path as prefix
                    delimiter="",  # No delimiter = recursive
                    amount=1000,
                )

                # Calculate total size and find latest modification
                for child_obj in folder_contents.results:
                    if child_obj.path_type == "object":
                        folder_size += child_obj.size_bytes or 0
                        if hasattr(child_obj, "mtime") and child_obj.mtime:
                            if (
                                folder_latest_mtime is None
                                or child_obj.mtime > folder_latest_mtime
                            ):
                                folder_latest_mtime = child_obj.mtime

            except Exception as e:
                logger.debug(
                    f"Could not calculate stats for folder {obj.path}: {str(e)}"
                )

            dir_obj = {
                "type": "directory",
                "oid": (
                    obj.checksum if hasattr(obj, "checksum") and obj.checksum else ""
                ),
                "size": folder_size,
                "path": relative_path.rstrip("/"),  # Remove trailing slash
            }

            # Add last modified info
            if folder_latest_mtime:
                from datetime import datetime

                dir_obj["lastModified"] = datetime.fromtimestamp(
                    folder_latest_mtime
                ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            elif hasattr(obj, "mtime") and obj.mtime:
                from datetime import datetime

                dir_obj["lastModified"] = datetime.fromtimestamp(obj.mtime).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                )

            result_list.append(dir_obj)

    return result_list


@router.post("/{repo_type}s/{namespace}/{repo_name}/paths-info/{revision}")
async def get_paths_info(
    repo_type: str,
    namespace: str,
    repo_name: str,
    revision: str,
    paths: List[str] = Form(...),
    expand: bool = Form(False),
    user: User = Depends(get_optional_user),
):
    """Get information about specific paths in a repository.

    This endpoint matches HuggingFace Hub API format:
    POST /api/{repo_type}s/{namespace}/{repo_name}/paths-info/{revision}

    Form data:
        paths: List of paths to query
        expand: Whether to include extended metadata

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
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check read permission for private repos
    check_repo_read_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)

    # Get information for each path
    result = []

    for path in paths:
        # Clean path
        clean_path = path.lstrip("/")

        try:
            # Try to get object stats
            async_client = get_async_lakefs_client()
            obj_stats = await async_client.stat_object(
                repository=lakefs_repo,
                ref=revision,
                path=clean_path,
            )

            # It's a file
            is_lfs = obj_stats.size_bytes > cfg.app.lfs_threshold_bytes

            # Get correct checksum from database
            # sha256 column stores: git blob SHA1 for non-LFS, SHA256 for LFS
            file_record = File.get_or_none(
                (File.repo_full_id == repo_id) & (File.path_in_repo == clean_path)
            )

            checksum = (
                file_record.sha256
                if file_record and file_record.sha256
                else obj_stats.checksum
            )

            file_info = {
                "type": "file",
                "path": clean_path,
                "size": obj_stats.size_bytes,
                "oid": checksum,  # Git blob SHA1 for non-LFS, SHA256 for LFS
                "lfs": None,
                "last_commit": None,
                "security": None,
            }

            # Add LFS metadata if applicable
            if is_lfs:
                file_info["lfs"] = {
                    "oid": checksum,  # SHA256 for LFS files
                    "size": obj_stats.size_bytes,
                    "pointerSize": 134,
                }

            result.append(file_info)

        except Exception as e:
            # Check if it might be a directory by trying to list with prefix
            if is_lakefs_not_found_error(e):
                try:
                    # Try to list objects with this path as prefix
                    async_client = get_async_lakefs_client()
                    prefix = (
                        clean_path if clean_path.endswith("/") else clean_path + "/"
                    )
                    list_result = await async_client.list_objects(
                        repository=lakefs_repo,
                        ref=revision,
                        prefix=prefix,
                        amount=1,  # Just check if any objects exist
                    )

                    # If we get results, it's a directory
                    if list_result.results:
                        # Try to get an oid from the first result if available
                        oid = ""
                        if list_result.results and hasattr(
                            list_result.results[0], "checksum"
                        ):
                            oid = list_result.results[0].checksum or ""

                        result.append(
                            {
                                "type": "directory",
                                "path": clean_path,
                                "oid": oid,
                                "tree_id": oid,
                                "last_commit": None,
                            }
                        )
                    # else: path doesn't exist, skip it (as per HF behavior)
                except Exception as ex:
                    # Path doesn't exist, skip it (as per HF behavior)
                    logger.debug(f"Path {clean_path} doesn't exist or is invalid")
            # For other errors, also skip the path

    return result
