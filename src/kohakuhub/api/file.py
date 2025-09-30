"""File upload/download API endpoints."""

import base64
import hashlib
import io
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from lakefs_client.models import CommitCreation

from ..config import cfg
from ..db import File, Repository, StagingUpload
from .auth import get_current_user
from .lakefs_utils import get_lakefs_client, lakefs_repo_name
from .s3_utils import get_s3_client

router = APIRouter()


class RepoType(str, Enum):
    """Repository type enumeration."""

    model = "model"
    dataset = "dataset"
    space = "space"


# ========== Preupload Endpoint ==========


@router.post("/{repo_type}s/{repo_id:path}/preupload/{revision}")
async def preupload(repo_type: RepoType, repo_id: str, revision: str, request: Request):
    """Check files before upload and determine upload mode.

    This endpoint implements HuggingFace's content deduplication mechanism.
    Files are checked against the database by SHA256 hash OR by comparing
    the base64 sample content for small files.

    Args:
        repo_type: Type of repository
        repo_id: Full repository ID
        revision: Branch name
        request: FastAPI request with file metadata

    Returns:
        Upload instructions for each file

    Raises:
        HTTPException: If repository not found or invalid payload
    """
    # Verify repository exists
    if not Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type.value)
    ):
        raise HTTPException(404, detail={"error": "Repository not found"})

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


@router.get("/{repo_type}s/{repo_id:path}/revision/{revision}")
def get_revision(
    repo_type: RepoType, repo_id: str, revision: str, expand: Optional[str] = None
):
    """Get revision information for a repository.

    Args:
        repo_type: Type of repository
        repo_id: Full repository ID
        revision: Branch name or commit hash
        expand: Optional fields to expand

    Returns:
        Revision metadata

    Raises:
        HTTPException: If revision not found
    """
    lakefs_repo = lakefs_repo_name(repo_type.value, repo_id)
    client = get_lakefs_client()

    # Get branch information
    try:
        branch = client.branches.get_branch(repository=lakefs_repo, branch=revision)
    except Exception as e:
        raise HTTPException(404, detail={"error": f"Revision {revision} not found: {e}"})

    commit_id = branch.commit_id
    commit_info = None

    # Get commit details if available
    if commit_id:
        try:
            commit_info = client.commits.get_commit(
                repository=lakefs_repo, commit_id=commit_id
            )
        except Exception:
            pass

    # Get repository metadata from database
    repo_row = Repository.get_or_none(
        (Repository.repo_type == repo_type.value) & (Repository.full_id == repo_id)
    )
    namespace = repo_row.namespace if repo_row else repo_id.split("/")[0]
    private = repo_row.private if repo_row else False
    created_at = (
        repo_row.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if repo_row and repo_row.created_at
        else None
    )

    # Format last modified date
    last_modified = None
    if commit_info and commit_info.creation_date:
        last_modified = datetime.fromtimestamp(commit_info.creation_date).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    return {
        "id": repo_id,
        "author": namespace,
        "sha": commit_id,
        "lastModified": last_modified,
        "createdAt": created_at,
        "private": private,
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


@router.head("/{repo_type}s/{repo_id:path}/resolve/{revision}/{path:path}")
@router.get("/{repo_type}s/{repo_id:path}/resolve/{revision}/{path:path}")
async def resolve_file(
    repo_type: str, repo_id: str, revision: str, path: str, request: Request
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

    Returns:
        HEAD: Response with headers only
        GET: Redirect to presigned S3 URL

    Raises:
        HTTPException: If file not found
    """
    from fastapi.responses import Response, RedirectResponse
    from .s3_utils import generate_download_presigned_url, parse_s3_uri

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
        headers=response_headers,
    )


# ========== Commit Endpoint ==========


@router.post("/{repo_type}s/{repo_id:path}/commit/{revision}")
async def commit(
    repo_type: RepoType,
    repo_id: str,
    revision: str,
    request: Request,
    user=Depends(get_current_user),
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

            if not content_b64 or not encoding.startswith("base64"):
                raise HTTPException(400, detail={"error": f"Invalid file operation for {path}"})

            # Decode content
            try:
                data = base64.b64decode(content_b64)
            except Exception as e:
                raise HTTPException(400, detail={"error": f"Failed to decode base64: {e}"})

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
                raise HTTPException(500, detail={"error": f"Failed to upload {path}: {e}"})

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
            # Large file already uploaded via LFS batch API
            # TODO: Implement LFS file linking
            # For now, we expect the file to already be in S3
            oid = value.get("oid")
            size = value.get("size")

            if not oid:
                raise HTTPException(400, detail={"error": f"Missing OID for LFS file {path}"})

            # Check if file unchanged
            existing = File.get_or_none(
                (File.repo_full_id == repo_id) & (File.path_in_repo == path)
            )
            if existing and existing.sha256 == oid and existing.size == size:
                print(f"Skipping unchanged LFS file: {path}")
                continue

            # File changed
            files_changed = True

            # TODO: Link physical object in LakeFS
            # For now, just update database
            print(f"TODO: Implement LFS file linking for {path}")

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
                    File.updated_at: datetime.now(timezone.utc),
                },
            ).execute()

        elif key == "deletedFile":
            # Delete file
            files_changed = True

            try:
                client.objects.delete_object(
                    repository=lakefs_repo, branch=revision, path=path
                )
            except Exception as e:
                print(f"Warning: Failed to delete {path}: {e}")

            # Remove from database
            File.delete().where(
                (File.repo_full_id == repo_id) & (File.path_in_repo == path)
            ).execute()

        elif key == "deletedFolder":
            # Delete folder (delete all files with prefix)
            files_changed = True
            # TODO: Implement folder deletion
            print(f"TODO: Implement folder deletion for {path}")

        elif key == "copyFile":
            # Copy file within repository
            files_changed = True
            # TODO: Implement file copying
            print(f"TODO: Implement file copying for {path}")

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
        raise e
        raise HTTPException(500, detail={"error": f"Commit failed: {e}"})

    # Generate commit URL
    commit_url = f"{cfg.app.base_url}/{repo_id}/commit/{commit_result.id}"
    print(f"Commit URL: {commit_url}")

    return {
        "commitUrl": commit_url,
        "commitOid": commit_result.id,
        "pullRequestUrl": None,
    }
