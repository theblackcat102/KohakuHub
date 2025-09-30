"""Git LFS Batch API implementation.

This module implements the Git LFS Batch API specification for handling
large file uploads (>10MB). It provides presigned S3 URLs for direct uploads.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..config import cfg
from ..db import File
from .s3_utils import generate_upload_presigned_url, generate_multipart_upload_urls

router = APIRouter()


class LFSObject(BaseModel):
    """LFS object specification."""

    oid: str  # SHA256 hash
    size: int


class LFSBatchRequest(BaseModel):
    """LFS batch API request."""

    operation: str  # "upload" or "download"
    transfers: Optional[List[str]] = ["basic"]
    objects: List[LFSObject]
    hash_algo: Optional[str] = "sha256"


class LFSAction(BaseModel):
    """LFS upload/download action."""

    href: str
    header: Optional[dict] = None
    expires_at: Optional[str] = None


class LFSError(BaseModel):
    """LFS error object - must have 'code' (int) and 'message' (str)."""

    code: int  # HTTP status code as integer
    message: str  # Error description


class LFSObjectResponse(BaseModel):
    """LFS object response with actions."""

    oid: str
    size: int
    authenticated: Optional[bool] = True
    actions: Optional[dict] = None  # Contains "upload", "verify", "download"
    error: Optional[LFSError] = None  # Must use LFSError model


class LFSBatchResponse(BaseModel):
    """LFS batch API response."""

    transfer: str = "basic"
    objects: List[LFSObjectResponse]
    hash_algo: str = "sha256"


@router.post("/{repo_id:path}.git/info/lfs/objects/batch")
async def lfs_batch(repo_id: str, request: Request):
    """Git LFS Batch API endpoint.

    Handles LFS batch requests for upload/download operations.
    Returns presigned URLs for S3 direct upload/download.

    Args:
        repo_id: Repository ID (e.g., "org/repo")
        request: FastAPI request with LFS batch payload

    Returns:
        LFS batch response with actions

    Raises:
        HTTPException: If operation fails
    """
    # Parse request
    try:
        body = await request.json()
        batch_req = LFSBatchRequest(**body)
    except Exception as e:
        raise HTTPException(400, detail={"error": f"Invalid LFS batch request: {e}"})

    if cfg.app.debug_log_payloads:
        print("==== LFS Batch Request ====")
        print(body)

    operation = batch_req.operation
    objects_response = []

    # LFS files stored in: s3://bucket/lfs/{oid[:2]}/{oid[2:4]}/{oid}
    # This provides a balanced directory structure

    for obj in batch_req.objects:
        oid = obj.oid
        size = obj.size

        # S3 key for LFS object (content-addressable)
        lfs_key = f"lfs/{oid[:2]}/{oid[2:4]}/{oid}"

        # Check if object already exists (deduplication)
        existing = File.get_or_none(File.sha256 == oid)

        if operation == "upload":
            if existing and existing.size == size:
                # Object exists, no upload needed
                objects_response.append(
                    LFSObjectResponse(
                        oid=oid,
                        size=size,
                        authenticated=True,
                        # No actions = already exists
                    )
                )
            else:
                # Object needs upload
                # Check if multipart upload required (>5GB)
                multipart_threshold = 5 * 1024 * 1024 * 1024  # 5GB

                if size > multipart_threshold:
                    # Return error for multipart uploads (not yet implemented)
                    objects_response.append(
                        LFSObjectResponse(
                            oid=oid,
                            size=size,
                            error=LFSError(
                                code=501,  # Not Implemented
                                message="Multipart upload not yet implemented for files >5GB",
                            ),
                        )
                    )
                else:
                    # Single PUT upload
                    try:
                        upload_info = generate_upload_presigned_url(
                            bucket=cfg.s3.bucket,
                            key=lfs_key,
                            expires_in=3600,  # 1 hour
                            content_type="application/octet-stream",
                        )

                        objects_response.append(
                            LFSObjectResponse(
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
                        )
                    except Exception as e:
                        # Error generating presigned URL
                        objects_response.append(
                            LFSObjectResponse(
                                oid=oid,
                                size=size,
                                error=LFSError(
                                    code=500,
                                    message=f"Failed to generate upload URL: {str(e)}",
                                ),
                            )
                        )

        elif operation == "download":
            if not existing:
                # Object not found - use proper error format
                objects_response.append(
                    LFSObjectResponse(
                        oid=oid,
                        size=size,
                        error=LFSError(code=404, message="Object not found"),
                    )
                )
            else:
                # Object exists, provide download URL
                try:
                    from .s3_utils import generate_download_presigned_url

                    download_url = generate_download_presigned_url(
                        bucket=cfg.s3.bucket,
                        key=lfs_key,
                        expires_in=3600,
                    )

                    expires_at = (
                        datetime.now(timezone.utc) + timedelta(seconds=3600)
                    ).isoformat() + "Z"

                    objects_response.append(
                        LFSObjectResponse(
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
                    )
                except Exception as e:
                    # Error generating download URL
                    objects_response.append(
                        LFSObjectResponse(
                            oid=oid,
                            size=size,
                            error=LFSError(
                                code=500,
                                message=f"Failed to generate download URL: {str(e)}",
                            ),
                        )
                    )

    # Return response with exclude_none to omit null fields
    # This ensures "error": null is not included in the JSON
    response = LFSBatchResponse(
        transfer="basic",
        objects=objects_response,
        hash_algo="sha256",
    )

    # Use JSONResponse to ensure proper serialization with exclude_none
    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        media_type="application/vnd.git-lfs+json",
    )


@router.post("/{repo_id:path}.git/info/lfs/verify")
async def lfs_verify(repo_id: str, request: Request):
    """Verify LFS upload completion.

    Called by client after successful upload to confirm the file.

    Args:
        repo_id: Repository ID
        request: FastAPI request with verification data

    Returns:
        Verification result
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(400, detail={"error": f"Invalid verification request: {e}"})

    oid = body.get("oid")
    size = body.get("size")

    if not oid:
        raise HTTPException(400, detail={"error": "Missing OID"})

    # Check if object exists in S3
    from .s3_utils import object_exists

    lfs_key = f"lfs/{oid[:2]}/{oid[2:4]}/{oid}"

    if not object_exists(cfg.s3.bucket, lfs_key):
        raise HTTPException(404, detail={"error": "Object not found in storage"})

    # Optionally verify size
    if size:
        from .s3_utils import get_object_metadata

        try:
            metadata = get_object_metadata(cfg.s3.bucket, lfs_key)
            if metadata["size"] != size:
                raise HTTPException(400, detail={"error": "Size mismatch"})
        except Exception:
            # If metadata retrieval fails, still accept the verification
            pass

    return {"message": "Object verified successfully"}
