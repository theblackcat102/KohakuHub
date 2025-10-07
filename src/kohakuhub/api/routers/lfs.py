"""Git LFS Batch API implementation - Refactored version.

This module implements the Git LFS Batch API specification for handling
large file uploads (>10MB). It provides presigned S3 URLs for direct uploads.
"""

import asyncio
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from kohakuhub.api.utils.quota import check_quota
from kohakuhub.api.utils.s3 import (
    generate_download_presigned_url,
    generate_upload_presigned_url,
    get_object_metadata,
    object_exists,
)
from kohakuhub.auth.dependencies import get_optional_user
from kohakuhub.auth.permissions import (
    check_repo_read_permission,
    check_repo_write_permission,
)
from kohakuhub.config import cfg
from kohakuhub.db_async import execute_db_query, get_file_by_sha256
from kohakuhub.db import Organization, Repository, User
from kohakuhub.logger import get_logger

logger = get_logger("LFS")
router = APIRouter()


class LFSObject(BaseModel):
    """LFS object specification."""

    oid: str  # SHA256 hash
    size: int


class LFSBatchRequest(BaseModel):
    """LFS batch API request."""

    operation: str  # "upload" or "download"
    transfers: list[str] | None = ["basic"]
    objects: list[LFSObject]
    hash_algo: str | None = "sha256"


class LFSError(BaseModel):
    """LFS error object - must have 'code' (int) and 'message' (str)."""

    code: int  # HTTP status code as integer
    message: str  # Error description


class LFSObjectResponse(BaseModel):
    """LFS object response with actions."""

    oid: str
    size: int
    authenticated: bool | None = True
    actions: dict | None = None  # Contains "upload", "verify", "download"
    error: LFSError | None = None  # Must use LFSError model


class LFSBatchResponse(BaseModel):
    """LFS batch API response."""

    transfer: str = "basic"
    objects: list[LFSObjectResponse]
    hash_algo: str = "sha256"


def get_lfs_key(oid: str) -> str:
    """Generate S3 key for LFS object.

    Args:
        oid: SHA256 hash

    Returns:
        S3 key with balanced directory structure
    """
    return f"lfs/{oid[:2]}/{oid[2:4]}/{oid}"


async def process_upload_object(oid: str, size: int, repo_id: str) -> LFSObjectResponse:
    """Process single LFS object for upload operation.

    Args:
        oid: Object ID (SHA256)
        size: File size in bytes
        repo_id: Repository ID

    Returns:
        LFS object response with upload actions or error
    """
    lfs_key = get_lfs_key(oid)

    # Check if object already exists (deduplication)
    existing = await get_file_by_sha256(oid)

    if existing and existing.size == size:
        # Object exists, no upload needed
        return LFSObjectResponse(
            oid=oid,
            size=size,
            authenticated=True,
            # No actions = already exists
        )

    # Check if multipart upload required (>5GB)
    multipart_threshold = 5 * 1024 * 1024 * 1024  # 5GB

    if size > multipart_threshold:
        return LFSObjectResponse(
            oid=oid,
            size=size,
            error=LFSError(
                code=501,  # Not Implemented
                message="Multipart upload not yet implemented for files >5GB",
            ),
        )

    # Single PUT upload
    try:
        # Convert SHA256 hex to base64 for S3 checksum verification
        checksum_sha256 = base64.b64encode(bytes.fromhex(oid)).decode("utf-8")

        upload_info = await generate_upload_presigned_url(
            bucket=cfg.s3.bucket,
            key=lfs_key,
            expires_in=3600,  # 1 hour
            content_type="application/octet-stream",
            checksum_sha256=checksum_sha256,
        )

        return LFSObjectResponse(
            oid=oid,
            size=size,
            authenticated=True,
            actions={
                "upload": {
                    "href": upload_info["url"],
                    "expires_at": upload_info["expires_at"],
                    "header": upload_info.get("headers", {}),
                },
                "verify": {
                    "href": f"{cfg.app.base_url}/api/{repo_id}.git/info/lfs/verify",
                    "expires_at": upload_info["expires_at"],
                },
            },
        )
    except Exception as e:
        return LFSObjectResponse(
            oid=oid,
            size=size,
            error=LFSError(
                code=500,
                message=f"Failed to generate upload URL: {str(e)}",
            ),
        )


async def process_download_object(oid: str, size: int) -> LFSObjectResponse:
    """Process single LFS object for download operation.

    Args:
        oid: Object ID (SHA256)
        size: File size in bytes

    Returns:
        LFS object response with download actions or error
    """
    lfs_key = get_lfs_key(oid)

    # Check if object exists
    existing = await get_file_by_sha256(oid)

    if not existing:
        return LFSObjectResponse(
            oid=oid,
            size=size,
            error=LFSError(code=404, message="Object not found"),
        )

    # Object exists, provide download URL
    try:
        download_url = await generate_download_presigned_url(
            bucket=cfg.s3.bucket,
            key=lfs_key,
            expires_in=3600,
        )

        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=3600)).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

        return LFSObjectResponse(
            oid=oid,
            size=size,
            authenticated=True,
            actions={
                "download": {
                    "href": download_url,
                    "expires_at": expires_at,
                },
            },
        )
    except Exception as e:
        return LFSObjectResponse(
            oid=oid,
            size=size,
            error=LFSError(
                code=500,
                message=f"Failed to generate download URL: {str(e)}",
            ),
        )


@router.post("/{repo_type}s/{namespace}/{name}.git/info/lfs/objects/batch")
@router.post("/{namespace}/{name}.git/info/lfs/objects/batch")
async def lfs_batch(
    namespace: str,
    name: str,
    request: Request,
    repo_type: str | None = "model",
    user: User | None = Depends(get_optional_user),
):
    """Git LFS Batch API endpoint.

    Handles LFS batch requests for upload/download operations.
    Returns presigned URLs for S3 direct upload/download.

    Args:
        namespace: Repository namespace
        name: Repository name
        request: FastAPI request with LFS batch payload
        repo_type: Repository type (default: model)
        user: Current authenticated user (optional for downloads)

    Returns:
        LFS batch response with actions

    Raises:
        HTTPException: If operation fails
    """
    repo_id = f"{namespace}/{name}"

    # Parse request
    try:
        body = await request.json()
        batch_req = LFSBatchRequest(**body)
    except Exception as e:
        raise HTTPException(400, detail={"error": f"Invalid LFS batch request: {e}"})

    # Check repository exists and permissions
    def _get_repo():
        return Repository.get_or_none(
            (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
        )

    repo_row = await execute_db_query(_get_repo)

    if repo_row:
        operation = batch_req.operation

        match operation:
            case "upload":
                # Upload requires authentication and write permission
                if not user:
                    raise HTTPException(
                        401, detail={"error": "Authentication required for upload"}
                    )
                check_repo_write_permission(repo_row, user)

                # Check storage quota for uploads
                total_upload_bytes = sum(obj.size for obj in batch_req.objects)

                # Check if namespace is organization
                def _check_org():
                    return Organization.get_or_none(Organization.name == namespace)

                org = await execute_db_query(_check_org)
                is_org = org is not None

                # Check quota (based on repo privacy)
                is_private = repo_row.private
                allowed, error_msg = await check_quota(
                    namespace, total_upload_bytes, is_private, is_org
                )
                if not allowed:
                    raise HTTPException(
                        status_code=413,  # Payload Too Large
                        detail={
                            "error": "Storage quota exceeded",
                            "message": error_msg,
                        },
                    )

            case "download":
                # Download requires read permission (may be public)
                check_repo_read_permission(repo_row, user)

    if cfg.app.debug_log_payloads:
        logger.debug("==== LFS Batch Request ====")
        logger.debug(body)

    # Process all objects in parallel
    async def process_object(obj: LFSObject) -> LFSObjectResponse:
        """Process single LFS object based on operation type."""
        match batch_req.operation:
            case "upload":
                return await process_upload_object(obj.oid, obj.size, repo_id)
            case "download":
                return await process_download_object(obj.oid, obj.size)
            case _:
                return LFSObjectResponse(
                    oid=obj.oid,
                    size=obj.size,
                    error=LFSError(
                        code=400, message=f"Unknown operation: {batch_req.operation}"
                    ),
                )

    objects_response = await asyncio.gather(
        *[process_object(obj) for obj in batch_req.objects]
    )

    # Return response with exclude_none to omit null fields
    response = LFSBatchResponse(
        transfer="basic",
        objects=objects_response,
        hash_algo="sha256",
    )

    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        media_type="application/vnd.git-lfs+json",
    )


@router.post("/api/{namespace}/{name}.git/info/lfs/verify")
async def lfs_verify(namespace: str, name: str, request: Request):
    """Verify LFS upload completion.

    Called by client after successful upload to confirm the file.

    Args:
        namespace: Repository namespace
        name: Repository name
        request: FastAPI request with verification data

    Returns:
        Verification result
    """
    repo_id = f"{namespace}/{name}"
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(400, detail={"error": f"Invalid verification request: {e}"})

    oid = body.get("oid")
    size = body.get("size")

    if not oid:
        raise HTTPException(400, detail={"error": "Missing OID"})

    lfs_key = get_lfs_key(oid)

    if not await object_exists(cfg.s3.bucket, lfs_key):
        raise HTTPException(404, detail={"error": "Object not found in storage"})

    # Optionally verify size
    if size:
        try:
            metadata = await get_object_metadata(cfg.s3.bucket, lfs_key)
            if metadata["size"] != size:
                raise HTTPException(400, detail={"error": "Size mismatch"})
        except Exception:
            # If metadata retrieval fails, still accept the verification
            pass

    return {"message": "Object verified successfully"}
