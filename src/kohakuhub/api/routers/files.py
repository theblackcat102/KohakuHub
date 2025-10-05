"""File upload/download API endpoints (preupload, revision, download)."""

import base64
import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from kohakuhub.api.utils.hf import (
    hf_repo_not_found,
    hf_revision_not_found,
    hf_server_error,
    is_lakefs_not_found_error,
)
from kohakuhub.api.utils.lakefs import get_lakefs_client, lakefs_repo_name
from kohakuhub.api.utils.s3 import generate_download_presigned_url, parse_s3_uri
from kohakuhub.async_utils import get_async_lakefs_client
from kohakuhub.auth.dependencies import get_current_user, get_optional_user
from kohakuhub.auth.permissions import (
    check_repo_read_permission,
    check_repo_write_permission,
)
from kohakuhub.config import cfg
from kohakuhub.db import File, Repository, User
from kohakuhub.logger import get_logger

logger = get_logger("FILE")
router = APIRouter()


class RepoType(str, Enum):
    """Repository type enumeration."""

    model = "model"
    dataset = "dataset"
    space = "space"


# ========== Preupload Endpoint ==========


@router.post("/{repo_type}s/{namespace}/{name}/preupload/{revision}")
async def preupload(
    repo_type: RepoType,
    namespace: str,
    name: str,
    revision: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Check files before upload and determine upload mode.

    This endpoint implements HuggingFace's content deduplication mechanism.
    Files are checked against the database by SHA256 hash OR by comparing
    the base64 sample content for small files.

    Args:
        repo_type: Type of repository
        repo_id: Full repository ID
        revision: Branch name
        request: FastAPI request with file metadata
        user: Current authenticated user

    Returns:
        Upload instructions for each file

    Raises:
        HTTPException: If repository not found or invalid payload
    """
    repo_id = f"{namespace}/{name}"
    # Verify repository exists
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type.value)
    )
    if not repo_row:
        raise HTTPException(404, detail={"error": "Repository not found"})

    # Check write permission
    check_repo_write_permission(repo_row, user)

    # Parse request body
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": f"Invalid JSON: {e}"})

    if cfg.app.debug_log_payloads:
        logger.debug("==== Preupload Payload ====")
        logger.debug(json.dumps(body, indent=2))

    files = body.get("files")
    if not isinstance(files, list):
        raise HTTPException(400, detail={"error": "Missing or invalid 'files' array"})

    # Get LakeFS client to check existing files
    lakefs_repo = lakefs_repo_name(repo_type.value, repo_id)

    # Process each file
    result_files: List[Dict[str, Any]] = []
    threshold = cfg.app.lfs_threshold_bytes

    for f in files:
        path = f.get("path") or f.get("path_in_repo")
        size = int(f.get("size") or 0)
        sha256 = f.get("sha256", "")
        sample = f.get("sample", "")  # Base64 encoded sample content

        # Determine upload mode based on size
        upload_mode = "lfs" if size >= threshold else "regular"
        should_ignore = False

        # Check for existing file with same content
        if sha256:
            # If sha256 provided, use it for comparison (most reliable)
            existing = File.get_or_none(
                (File.repo_full_id == repo_id) & (File.path_in_repo == path)
            )
            if existing and existing.sha256 == sha256 and existing.size == size:
                should_ignore = True
        elif sample and upload_mode == "regular":
            # For small files, compare sample content if no sha256 provided
            try:
                # Decode the sample
                sample_data = base64.b64decode(sample)
                sample_sha256 = hashlib.sha256(sample_data).hexdigest()

                # Try to get existing file from LakeFS
                try:
                    async_client = get_async_lakefs_client()
                    obj_stat = await async_client.stat_object(
                        repository=lakefs_repo, ref=revision, path=path
                    )

                    # If file exists and size matches, download and compare
                    if obj_stat.size_bytes == size:
                        # Get the actual content to compare
                        try:
                            obj_content = await async_client.get_object(
                                repository=lakefs_repo, ref=revision, path=path
                            )
                            # Read the content
                            existing_data = obj_content.read()
                            existing_sha256 = hashlib.sha256(existing_data).hexdigest()

                            # If content matches, skip upload
                            if existing_sha256 == sample_sha256:
                                should_ignore = True
                        except Exception:
                            # If can't read content, assume changed
                            pass
                except Exception:
                    # File doesn't exist, need to upload
                    pass
            except Exception as e:
                logger.warning(f"Failed to decode sample for {path}: {e}")

        result_files.append(
            {
                "path": path,
                "uploadMode": upload_mode,
                "shouldIgnore": should_ignore,
            }
        )

    return {"files": result_files}


# ========== Revision Info Endpoint ==========


@router.get("/{repo_type}s/{namespace}/{name}/revision/{revision}")
async def get_revision(
    repo_type: RepoType,
    namespace: str,
    name: str,
    revision: str,
    expand: Optional[str] = None,
    user: User = Depends(get_optional_user),
):
    """Get revision information for a repository.

    Args:
        repo_type: Type of repository
        repo_id: Full repository ID
        revision: Branch name or commit hash
        expand: Optional fields to expand
        user: Current authenticated user (optional)

    Returns:
        Revision metadata
    """
    repo_id = f"{namespace}/{name}"
    # Check if repository exists in database first
    repo_row = Repository.get_or_none(
        (Repository.repo_type == repo_type.value) & (Repository.full_id == repo_id)
    )

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type.value)

    # Check read permission for private repos
    check_repo_read_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type.value, repo_id)
    client = get_lakefs_client()

    # Get branch information
    try:
        branch = client.branches.get_branch(repository=lakefs_repo, branch=revision)
    except Exception as e:
        if is_lakefs_not_found_error(e):
            return hf_revision_not_found(repo_id, revision)
        return hf_server_error(f"Failed to get branch: {str(e)}")

    commit_id = branch.commit_id
    commit_info = None

    # Get commit details if available
    if commit_id:
        try:
            async_client = get_async_lakefs_client()
            commit_info = await async_client.get_commit(
                repository=lakefs_repo, commit_id=commit_id
            )
        except Exception as e:
            # Log but don't fail if commit info unavailable
            logger.warning(f"Could not get commit info: {e}")

    # Format last modified date
    last_modified = None
    if commit_info and commit_info.creation_date:
        last_modified = datetime.fromtimestamp(commit_info.creation_date).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    # Format created_at
    created_at = repo_row.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    return {
        "id": repo_id,
        "author": repo_row.namespace,
        "sha": commit_id,
        "lastModified": last_modified,
        "createdAt": created_at,
        "private": repo_row.private,
        "downloads": 0,
        "likes": 0,
        "gated": False,
        "files": [],  # Client will call /tree for file list
        "type": repo_type.value,
        "revision": revision,
        "commit": {
            "oid": commit_id,
            "date": commit_info.creation_date if commit_info else None,
        },
        "xetEnabled": False,
    }


# ========== Download Endpoints ==========


async def _get_file_metadata(
    repo_type: str,
    namespace: str,
    name: str,
    revision: str,
    path: str,
    user: User,
):
    """Shared logic to get file metadata for HEAD/GET requests."""
    repo_id = f"{namespace}/{name}"

    # Check repository exists and read permission
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )
    if repo_row:
        check_repo_read_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)
    client = get_lakefs_client()

    try:
        # Get object metadata from LakeFS
        async_client = get_async_lakefs_client()
        obj_stat = await async_client.stat_object(
            repository=lakefs_repo, ref=revision, path=path
        )
    except Exception as e:
        raise HTTPException(404, detail={"error": f"File not found: {e}"})

    # Get commit hash for the revision
    try:
        branch = client.branches.get_branch(repository=lakefs_repo, branch=revision)
        commit_hash = branch.commit_id
    except Exception:
        # If not a branch, might be a commit hash already
        commit_hash = revision

    # Parse physical address to get S3 bucket and key
    physical_address = obj_stat.physical_address

    if not physical_address.startswith("s3://"):
        raise HTTPException(500, detail={"error": "Unsupported storage backend"})

    bucket, key = parse_s3_uri(physical_address)

    # Generate presigned download URL
    presigned_url = generate_download_presigned_url(
        bucket=bucket,
        key=key,
        expires_in=3600,  # 1 hour
        filename=path.split("/")[-1],  # Just the filename
    )

    # Prepare headers required by HuggingFace client
    file_size = obj_stat.size_bytes

    # Get correct checksum from database
    # sha256 column stores: git blob SHA1 for non-LFS, SHA256 for LFS
    file_record = File.get_or_none(
        (File.repo_full_id == repo_id) & (File.path_in_repo == path)
    )

    # HuggingFace expects plain SHA256 hex (64 characters, unquoted)
    # For non-LFS: use git blob SHA1, for LFS: use SHA256
    etag_value = file_record.sha256 if file_record and file_record.sha256 else ""

    response_headers = {
        # Critical headers for HuggingFace client
        "X-Repo-Commit": commit_hash or "",
        "X-Linked-Etag": etag_value,  # Plain hex, not quoted
        "X-Linked-Size": str(file_size) if file_size else "0",
        "ETag": etag_value,  # Plain hex, not quoted
        "Content-Length": str(file_size) if file_size else "0",
        "Accept-Ranges": "bytes",  # Support resume
        # Additional useful headers
        "Content-Type": obj_stat.content_type or "application/octet-stream",
        "Last-Modified": (
            datetime.fromtimestamp(obj_stat.mtime).strftime("%a, %d %b %Y %H:%M:%S GMT")
            if obj_stat.mtime
            else ""
        ),
        "Content-Disposition": f'attachment; filename="{path}";',
    }

    return presigned_url, response_headers


@router.head("/{repo_type}s/{namespace}/{name}/resolve/{revision}/{path:path}")
async def resolve_file_head(
    repo_type: str,
    namespace: str,
    name: str,
    revision: str,
    path: str,
    user: User = Depends(get_optional_user),
):
    """Get file metadata (HEAD request).

    Returns only headers without body, for clients to check file info.
    """
    _, response_headers = await _get_file_metadata(
        repo_type, namespace, name, revision, path, user
    )

    # Return metadata headers only, NO redirect
    return Response(
        status_code=200,
        headers=response_headers,
    )


@router.get("/{repo_type}s/{namespace}/{name}/resolve/{revision}/{path:path}")
async def resolve_file_get(
    repo_type: str,
    namespace: str,
    name: str,
    revision: str,
    path: str,
    user: User = Depends(get_optional_user),
):
    """Download file (GET request).

    Returns 302 redirect to presigned S3 URL for actual download.
    """
    presigned_url, _ = await _get_file_metadata(
        repo_type, namespace, name, revision, path, user
    )

    # Return 302 redirect to presigned S3 URL
    return RedirectResponse(
        url=presigned_url,
        status_code=302,
    )
