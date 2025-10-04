"""File upload/download API endpoints."""

import base64
import hashlib
import io
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from lakefs_client.models import CommitCreation, StagingLocation, StagingMetadata

from ..config import cfg
from ..db import File, Repository, StagingUpload, User
from .auth import get_current_user, get_optional_user
from ..auth.permissions import check_repo_read_permission, check_repo_write_permission
from .lakefs_utils import get_lakefs_client, lakefs_repo_name
from .s3_utils import get_s3_client
from .hf_utils import (
    hf_repo_not_found,
    hf_entry_not_found,
    hf_revision_not_found,
    hf_bad_request,
    hf_server_error,
    is_lakefs_not_found_error,
)

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
        print("==== Preupload Payload ====")
        print(json.dumps(body, indent=2))

    files = body.get("files")
    if not isinstance(files, list):
        raise HTTPException(400, detail={"error": "Missing or invalid 'files' array"})

    # Get LakeFS client to check existing files
    lakefs_repo = lakefs_repo_name(repo_type.value, repo_id)
    client = get_lakefs_client()

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
                    obj_stat = client.objects.stat_object(
                        repository=lakefs_repo, ref=revision, path=path
                    )

                    # If file exists and size matches, download and compare
                    if obj_stat.size_bytes == size:
                        # Get the actual content to compare
                        try:
                            obj_content = client.objects.get_object(
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
                print(f"Failed to decode sample for {path}: {e}")

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
def get_revision(
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
            commit_info = client.commits.get_commit(
                repository=lakefs_repo, commit_id=commit_id
            )
        except Exception as e:
            # Log but don't fail if commit info unavailable
            print(f"Warning: Could not get commit info: {e}")

    # Format last modified date
    last_modified = None
    if commit_info and commit_info.creation_date:
        from datetime import datetime

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


@router.head("/{repo_type}s/{namespace}/{repo_name}/resolve/{revision}/{path:path}")
@router.get("/{repo_type}s/{namespace}/{repo_name}/resolve/{revision}/{path:path}")
async def resolve_file(
    repo_type: str,
    namespace: str,
    name: str,
    revision: str,
    path: str,
    request: Request,
    user: User = Depends(get_optional_user),
):
    """Resolve file path to download URL.

    This endpoint MUST return specific headers for HuggingFace client compatibility:
    - X-Repo-Commit: The commit hash
    - X-Linked-Etag: ETag of the file (preferably with quotes)
    - X-Linked-Size: Size of the file in bytes
    - Location: Presigned download URL (for redirects)
    - ETag: Standard ETag header
    - Content-Length: File size

    The client first makes a HEAD request to get metadata, then a GET request
    to download. Both must return the same headers.

    Args:
        repo_type: Type of repository
        repo_id: Full repository ID
        revision: Branch name or commit hash
        path: File path within repository
        request: FastAPI request object
        user: Current authenticated user (optional)

    Returns:
        HEAD: Response with headers only
        GET: Redirect to presigned S3 URL

    Raises:
        HTTPException: If file not found
    """
    from fastapi.responses import Response, RedirectResponse
    from .s3_utils import generate_download_presigned_url, parse_s3_uri

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
        obj_stat = client.objects.stat_object(
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
    file_checksum = obj_stat.checksum  # This is the ETag from LakeFS

    # Normalize ETag (add quotes if not present)
    if file_checksum and not file_checksum.startswith('"'):
        etag_value = f'"{file_checksum}"'
    else:
        etag_value = file_checksum or '""'

    response_headers = {
        # Critical headers for HuggingFace client
        "X-Repo-Commit": commit_hash or "",
        "X-Linked-Etag": etag_value,
        "X-Linked-Size": str(file_size) if file_size else "0",
        "ETag": etag_value,
        "Content-Length": str(file_size) if file_size else "0",
        "Accept-Ranges": "bytes",  # Support resume
        # Additional useful headers
        "Content-Type": obj_stat.content_type or "application/octet-stream",
        "Last-Modified": (
            datetime.fromtimestamp(obj_stat.mtime).strftime("%a, %d %b %Y %H:%M:%S GMT")
            if obj_stat.mtime
            else ""
        ),
    }

    # Handle HEAD request (metadata only)
    if request.method == "HEAD":
        # For HEAD, include Location header but don't redirect
        response_headers["Location"] = presigned_url
        return Response(
            status_code=200,
            headers=response_headers,
        )

    # Handle GET request (actual download)
    # Return 302 redirect to presigned S3 URL
    return RedirectResponse(
        url=presigned_url,
        status_code=302,
        # headers=response_headers,
    )


# ========== Commit Endpoint ==========


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
        repo_id: Full repository ID
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

    # Read NDJSON payload
    raw = await request.body()
    lines = raw.decode("utf-8").splitlines()

    if cfg.app.debug_log_payloads:
        print("==== Commit Payload ====")
        for line in lines:
            print(line)

    # Parse NDJSON
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

    # Process operations
    files_changed = False  # Track if any files actually changed

    for op in operations:
        key = op["key"]
        value = op["value"]
        path = value.get("path")
        print(f"Processing {key}: {path}")

        if key == "file":
            # Small file with inline base64 content
            content_b64 = value.get("content")
            encoding = (value.get("encoding") or "").lower()

            if not encoding.startswith("base64"):
                raise HTTPException(
                    400, detail={"error": f"Invalid file operation for {path}"}
                )

            # Decode content
            try:
                data = base64.b64decode(content_b64)
            except Exception as e:
                raise e
                raise HTTPException(
                    400, detail={"error": f"Failed to decode base64: {e}"}
                )

            new_sha256 = hashlib.sha256(data).hexdigest()

            # Check if file unchanged (deduplication)
            existing = File.get_or_none(
                (File.repo_full_id == repo_id) & (File.path_in_repo == path)
            )
            if (
                existing
                and existing.sha256 == new_sha256
                and existing.size == len(data)
            ):
                print(f"Skipping unchanged file: {path}")
                continue

            # File changed, need to upload
            files_changed = True

            # Upload to LakeFS
            try:
                client.objects.upload_object(
                    repository=lakefs_repo,
                    branch=revision,
                    path=path,
                    content=io.BytesIO(data),
                )
            except Exception as e:
                raise HTTPException(
                    500, detail={"error": f"Failed to upload {path}: {e}"}
                )

            # Update database
            File.insert(
                repo_full_id=repo_id,
                path_in_repo=path,
                size=len(data),
                sha256=new_sha256,
                lfs=False,
            ).on_conflict(
                conflict_target=(File.repo_full_id, File.path_in_repo),
                update={
                    File.sha256: new_sha256,
                    File.size: len(data),
                    File.updated_at: datetime.now(timezone.utc),
                },
            ).execute()

        elif key == "lfsFile":
            # Large file already uploaded via LFS batch API to S3
            # Need to link the physical S3 object to LakeFS
            oid = value.get("oid")
            size = value.get("size")
            algo = value.get("algo", "sha256")

            if not oid:
                raise HTTPException(
                    400, detail={"error": f"Missing OID for LFS file {path}"}
                )

            # Check for existing file at this path (BEFORE any changes)
            existing = File.get_or_none(
                (File.repo_full_id == repo_id) & (File.path_in_repo == path)
            )

            # Track old LFS object for potential deletion
            old_lfs_oid = None
            if existing and existing.lfs and existing.sha256 != oid:
                old_lfs_oid = existing.sha256
                print(f"File {path} will be replaced: {old_lfs_oid} → {oid}")

            # Check if file unchanged
            if existing and existing.sha256 == oid and existing.size == size:
                print(f"Skipping unchanged LFS file: {path}")
                continue

            # File changed or new
            files_changed = True

            # Construct S3 physical address for the LFS object
            # LFS files are stored at: s3://bucket/lfs/{oid[:2]}/{oid[2:4]}/{oid}
            lfs_key = f"lfs/{oid[:2]}/{oid[2:4]}/{oid}"
            physical_address = f"s3://{cfg.s3.bucket}/{lfs_key}"

            print(f"Linking LFS file: {path} -> {physical_address}")

            # Verify the object exists in S3 before linking
            from .s3_utils import object_exists, get_object_metadata

            if not object_exists(cfg.s3.bucket, lfs_key):
                raise HTTPException(
                    400,
                    detail={
                        "error": f"LFS object {oid} not found in storage. "
                        f"Upload to S3 may have failed. Path: {lfs_key}"
                    },
                )

            # Get actual size from S3 to verify
            try:
                s3_metadata = get_object_metadata(cfg.s3.bucket, lfs_key)
                actual_size = s3_metadata["size"]

                if actual_size != size:
                    print(
                        f"Warning: Size mismatch for {path}. Expected: {size}, Got: {actual_size}"
                    )
                    size = actual_size
            except Exception as e:
                print(f"Warning: Could not verify S3 object metadata: {e}")

            # Link the physical S3 object to LakeFS using StagingApi
            try:
                staging_location = StagingLocation(
                    physical_address=physical_address,
                    checksum=f"{algo}:{oid}",
                    size_bytes=size,
                )

                staging_metadata = StagingMetadata(
                    staging=staging_location,
                    checksum=f"{algo}:{oid}",
                    size_bytes=size,
                )

                client.staging.link_physical_address(
                    repository=lakefs_repo,
                    branch=revision,
                    path=path,
                    staging_metadata=staging_metadata,
                )

                print(f"Successfully linked LFS file in LakeFS: {path}")

            except Exception as e:
                raise HTTPException(
                    500,
                    detail={
                        "error": f"Failed to link LFS file {path} in LakeFS: {str(e)}"
                    },
                )

            # Update database (BEFORE deleting old object, so deduplication check works)
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

            print(f"Updated database record for LFS file: {path}")

            # NOW delete the old LFS object if it exists and is not used elsewhere
            if old_lfs_oid:
                # Check if this OID is still used by other files (deduplication check)
                other_uses = (
                    File.select()
                    .where((File.sha256 == old_lfs_oid) & (File.lfs == True))
                    .count()
                )

                if other_uses == 0:
                    # Safe to delete - not used anywhere
                    old_lfs_key = (
                        f"lfs/{old_lfs_oid[:2]}/{old_lfs_oid[2:4]}/{old_lfs_oid}"
                    )
                    try:
                        from .s3_utils import get_s3_client

                        s3_client = get_s3_client()
                        s3_client.delete_object(Bucket=cfg.s3.bucket, Key=old_lfs_key)
                        print(f"✓ Deleted old LFS object: {old_lfs_key}")
                    except Exception as e:
                        # Log but don't fail - the new file is already linked successfully
                        print(
                            f"Warning: Failed to delete old LFS object {old_lfs_key}: {e}"
                        )
                else:
                    print(
                        f"✓ Keeping old LFS object {old_lfs_oid} - still used by {other_uses} file(s)"
                    )

        elif key == "deletedFile":
            # Delete a single file
            files_changed = True

            print(f"Deleting file: {path}")

            try:
                client.objects.delete_object(
                    repository=lakefs_repo, branch=revision, path=path
                )
                print(f"Successfully deleted file from LakeFS: {path}")
            except Exception as e:
                # File might not exist, log warning but continue
                print(f"Warning: Failed to delete {path} from LakeFS: {e}")

            # Remove from database
            deleted_count = (
                File.delete()
                .where((File.repo_full_id == repo_id) & (File.path_in_repo == path))
                .execute()
            )

            if deleted_count > 0:
                print(f"Removed {path} from database")
            else:
                print(f"File {path} was not in database")

        elif key == "deletedFolder":
            # Delete all files with the given path prefix
            # LakeFS handles both LFS and regular files the same way
            files_changed = True

            # Normalize folder path (ensure it ends with /)
            folder_path = path if path.endswith("/") else f"{path}/"
            print(f"Deleting folder: {folder_path}")

            try:
                # List all objects in the folder
                objects = client.objects.list_objects(
                    repository=lakefs_repo,
                    ref=revision,
                    prefix=folder_path,
                    delimiter="",  # No delimiter to get all files recursively
                )

                deleted_files = []
                for obj in objects.results:
                    if obj.path_type == "object":
                        try:
                            client.objects.delete_object(
                                repository=lakefs_repo, branch=revision, path=obj.path
                            )
                            deleted_files.append(obj.path)
                            print(f"  Deleted: {obj.path}")
                        except Exception as e:
                            print(f"  Warning: Failed to delete {obj.path}: {e}")

                print(f"Deleted {len(deleted_files)} files from folder {folder_path}")

                # Remove from database - use LIKE for prefix matching
                if deleted_files:
                    # Delete all files that start with the folder path
                    deleted_count = (
                        File.delete()
                        .where(
                            (File.repo_full_id == repo_id)
                            & (File.path_in_repo.startswith(folder_path))
                        )
                        .execute()
                    )
                    print(f"Removed {deleted_count} records from database")

            except Exception as e:
                print(f"Warning: Error deleting folder {folder_path}: {e}")

        elif key == "copyFile":
            # Copy a file within the repository
            # LakeFS handles both LFS and regular files uniformly
            files_changed = True

            src_path = value.get("srcPath")
            dest_path = path  # 'path' is the destination
            src_revision = value.get(
                "srcRevision", revision
            )  # Default to current revision

            if not src_path:
                raise HTTPException(
                    400, detail={"error": f"Missing srcPath for copyFile operation"}
                )

            print(
                f"Copying file: {src_path} -> {dest_path} (from revision: {src_revision})"
            )

            try:
                # Get source file metadata from LakeFS
                src_obj = client.objects.stat_object(
                    repository=lakefs_repo, ref=src_revision, path=src_path
                )

                # Use LakeFS staging API to link the physical address
                # This works for both LFS and regular files
                staging_metadata = StagingMetadata(
                    staging=StagingLocation(
                        physical_address=src_obj.physical_address,
                        checksum=src_obj.checksum,
                        size_bytes=src_obj.size_bytes,
                    ),
                    checksum=src_obj.checksum,
                    size_bytes=src_obj.size_bytes,
                )

                client.staging.link_physical_address(
                    repository=lakefs_repo,
                    branch=revision,
                    path=dest_path,
                    staging_metadata=staging_metadata,
                )

                print(
                    f"Successfully linked {dest_path} to same physical address as {src_path}"
                )

                # Update database - copy file metadata
                src_file = File.get_or_none(
                    (File.repo_full_id == repo_id) & (File.path_in_repo == src_path)
                )

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
                    is_lfs = src_obj.size_bytes >= cfg.app.lfs_threshold_bytes
                    File.insert(
                        repo_full_id=repo_id,
                        path_in_repo=dest_path,
                        size=src_obj.size_bytes,
                        sha256=src_obj.checksum,
                        lfs=is_lfs,
                    ).on_conflict(
                        conflict_target=(File.repo_full_id, File.path_in_repo),
                        update={
                            File.sha256: src_obj.checksum,
                            File.size: src_obj.size_bytes,
                            File.lfs: is_lfs,
                            File.updated_at: datetime.now(timezone.utc),
                        },
                    ).execute()

                print(f"Successfully copied {src_path} to {dest_path}")

            except Exception as e:
                raise HTTPException(
                    500,
                    detail={
                        "error": f"Failed to copy file {src_path} to {dest_path}: {str(e)}"
                    },
                )

    # If no files changed, we can return early without creating a commit
    # Get current commit hash to return
    if not files_changed:
        try:
            branch = client.branches.get_branch(repository=lakefs_repo, branch=revision)
            commit_id = branch.commit_id
        except Exception:
            # If can't get branch, use a placeholder
            commit_id = "no-changes"

        # Return current commit info (no new commit created)
        commit_url = f"{cfg.app.base_url}/{repo_id}/commit/{commit_id}"

        return {
            "commitUrl": commit_url,
            "commitOid": commit_id,
            "pullRequestUrl": None,
        }

    # Create commit in LakeFS (only if files changed)
    commit_msg = header.get("summary", "Commit via API")
    commit_desc = header.get("description", "")
    print(f"Commit message: {commit_msg}")

    try:
        commit_result = client.commits.commit(
            repository=lakefs_repo,
            branch=revision,
            commit_creation=CommitCreation(
                message=commit_msg,
                metadata={"description": commit_desc} if commit_desc else {},
            ),
        )
    except Exception as e:
        raise HTTPException(500, detail={"error": f"Commit failed: {str(e)}"})

    # Generate commit URL
    commit_url = f"{cfg.app.base_url}/{repo_id}/commit/{commit_result.id}"
    print(f"Commit URL: {commit_url}")

    return {
        "commitUrl": commit_url,
        "commitOid": commit_result.id,
        "pullRequestUrl": None,
    }
