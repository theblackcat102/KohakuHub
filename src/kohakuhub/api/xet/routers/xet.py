"""
XET token refresh endpoint.

Returns XET-specific headers for CAS (Content Addressable Storage) access.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from kohakuhub.config import cfg
from kohakuhub.db import User
from kohakuhub.db_operations import get_repository
from kohakuhub.auth.dependencies import get_optional_user
from kohakuhub.auth.permissions import check_repo_read_permission

router = APIRouter()


@router.get(
    "/{repo_type}s/{namespace}/{name}/xet-read-token/{revision}/{filename:path}"
)
async def get_xet_read_token(
    repo_type: str,
    namespace: str,
    name: str,
    revision: str,
    filename: str,
    request: Request,
    user: User | None = Depends(get_optional_user),
    authorization: str | None = Header(None),
):
    """
    XET token refresh endpoint.

    Returns headers needed by hf-xet client for CAS access:
    - X-Xet-Cas-Url: Base URL for CAS endpoints
    - X-Xet-Access-Token: User's existing API token (reused)
    - X-Xet-Token-Expiration: Unix timestamp (7 days from now)

    Returns empty JSON body as per hf-xet protocol.
    """
    # Get repository
    repo_row = get_repository(repo_type, namespace, name)
    if not repo_row:
        return JSONResponse(status_code=404, content={"error": "Repository not found"})

    # Check read permission
    check_repo_read_permission(repo_row, user)

    # Extract token from Authorization header
    # Format: "Bearer <token>" or "Bearer <token>|external_tokens..."
    access_token = ""
    if authorization:
        auth_parts = authorization.split()
        if len(auth_parts) >= 2 and auth_parts[0].lower() == "bearer":
            # Get token before any pipe separator (external tokens)
            token_part = auth_parts[1]
            access_token = token_part.split("|")[0]

    # Calculate expiration (7 days from now)
    expiration = datetime.now(timezone.utc) + timedelta(days=7)
    expiration_unix = int(expiration.timestamp())

    # Return response with XET headers
    headers = {
        "X-Xet-Cas-Url": cfg.app.base_url,
        "X-Xet-Access-Token": access_token,
        "X-Xet-Token-Expiration": str(expiration_unix),
    }

    return JSONResponse(content={}, headers=headers)
