"""Storage quota management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from kohakuhub.db import Organization, User, UserOrganization
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_current_user, get_optional_user
from kohakuhub.api.quota.util import (
    get_storage_info,
    set_quota,
    update_namespace_storage,
)

logger = get_logger("QUOTA")
router = APIRouter()


class QuotaInfo(BaseModel):
    """Storage quota information."""

    namespace: str
    is_organization: bool
    quota_bytes: int | None
    used_bytes: int
    available_bytes: int | None
    percentage_used: float | None


class PublicQuotaInfo(BaseModel):
    """Public storage quota information with separate private/public tracking."""

    namespace: str
    is_organization: bool
    # Public storage (always visible)
    public_quota_bytes: int | None
    public_used_bytes: int
    public_available_bytes: int | None
    public_percentage_used: float | None
    # Private storage (only visible with permission)
    private_quota_bytes: int | None = None
    private_used_bytes: int | None = None
    private_available_bytes: int | None = None
    private_percentage_used: float | None = None
    # Total (calculated from visible fields)
    total_used_bytes: int
    # Permission indicator
    can_see_private: bool


class SetQuotaRequest(BaseModel):
    """Request to set storage quota."""

    quota_bytes: int | None  # None = unlimited


@router.get("/api/quota/{namespace}")
async def get_quota(
    namespace: str,
    user: User = Depends(get_current_user),
):
    """Get storage quota information for a user or organization.

    Args:
        namespace: Username or organization name
        user: Current authenticated user

    Returns:
        Quota information

    Raises:
        HTTPException: If not authorized or namespace not found
    """

    # Check if namespace is organization
    org = Organization.get_or_none(Organization.name == namespace)
    is_org = org is not None

    # Check if namespace exists
    if not is_org:
        target_user = User.get_or_none(User.username == namespace)
        if not target_user:
            raise HTTPException(
                404, detail={"error": f"User or organization not found: {namespace}"}
            )

    # Get storage info
    info = get_storage_info(namespace, is_org)

    return QuotaInfo(
        namespace=namespace,
        is_organization=is_org,
        quota_bytes=info["quota_bytes"],
        used_bytes=info["used_bytes"],
        available_bytes=info["available_bytes"],
        percentage_used=info["percentage_used"],
    )


@router.put("/api/quota/{namespace}")
async def update_quota(
    namespace: str,
    request: SetQuotaRequest,
    user: User = Depends(get_current_user),
):
    """Set storage quota for a user or organization.

    Only the user themselves or organization admins can set quotas.

    Args:
        namespace: Username or organization name
        request: Quota settings
        user: Current authenticated user

    Returns:
        Updated quota information

    Raises:
        HTTPException: If not authorized or namespace not found
    """

    # Check if namespace is organization
    org = Organization.get_or_none(Organization.name == namespace)
    is_org = org is not None

    # Authorization check
    if is_org:
        # For orgs, must be admin member
        member = UserOrganization.get_or_none(
            (UserOrganization.user == user.id)
            & (UserOrganization.organization == org.id)
        )
        is_admin = member and member.role in ("admin", "super-admin")
        if not is_admin:
            raise HTTPException(
                403,
                detail={
                    "error": "Only organization admins can set quota for organizations"
                },
            )
    else:
        # For users, must be themselves (or we could add admin check here)
        if user.username != namespace:
            raise HTTPException(
                403, detail={"error": "You can only set quota for yourself"}
            )

    # Set quota
    info = set_quota(namespace, request.quota_bytes, is_org)

    return QuotaInfo(
        namespace=namespace,
        is_organization=is_org,
        quota_bytes=info["quota_bytes"],
        used_bytes=info["used_bytes"],
        available_bytes=info["available_bytes"],
        percentage_used=info["percentage_used"],
    )


@router.post("/api/quota/{namespace}/recalculate")
async def recalculate_storage(
    namespace: str,
    user: User = Depends(get_current_user),
):
    """Recalculate storage usage for a user or organization.

    This can be useful if storage tracking gets out of sync.

    Args:
        namespace: Username or organization name
        user: Current authenticated user

    Returns:
        Updated quota information

    Raises:
        HTTPException: If not authorized or namespace not found
    """

    # Check if namespace is organization
    org = Organization.get_or_none(Organization.name == namespace)
    is_org = org is not None

    # Authorization check (same as update_quota)
    if is_org:
        # For orgs, must be admin member
        member = UserOrganization.get_or_none(
            (UserOrganization.user == user.id)
            & (UserOrganization.organization == org.id)
        )
        is_admin = member and member.role in ("admin", "super-admin")
        if not is_admin:
            raise HTTPException(
                403,
                detail={
                    "error": "Only organization admins can recalculate quota for organizations"
                },
            )
    else:
        # For users, must be themselves
        if user.username != namespace:
            raise HTTPException(
                403, detail={"error": "You can only recalculate quota for yourself"}
            )

    # Recalculate storage
    logger.info(f"Recalculating storage for {'org' if is_org else 'user'} {namespace}")
    update_namespace_storage(namespace, is_org)

    # Get updated info
    info = get_storage_info(namespace, is_org)

    return QuotaInfo(
        namespace=namespace,
        is_organization=is_org,
        quota_bytes=info["quota_bytes"],
        used_bytes=info["used_bytes"],
        available_bytes=info["available_bytes"],
        percentage_used=info["percentage_used"],
    )


@router.get("/api/quota/{namespace}/public")
async def get_public_quota(
    namespace: str,
    user: User | None = Depends(get_optional_user),
):
    """Get public storage quota information with permission-based private data access.

    This endpoint is designed for profile pages. It returns:
    - Public storage quota (always visible to everyone)
    - Private storage quota (only visible if viewer has permission to see private repos)

    Permission to see private quota:
    - User viewing their own profile
    - Organization members viewing org profile

    Args:
        namespace: Username or organization name
        user: Current authenticated user (optional)

    Returns:
        Public quota information with conditional private data

    Raises:
        HTTPException: If namespace not found
    """

    # Check if namespace is organization
    org = Organization.get_or_none(Organization.name == namespace)
    is_org = org is not None

    # Check if namespace exists
    target_user = None
    if not is_org:
        target_user = User.get_or_none(User.username == namespace)
        if not target_user:
            raise HTTPException(
                404, detail={"error": f"User or organization not found: {namespace}"}
            )

    # Determine if viewer can see private storage info
    can_see_private = False

    if user:
        if is_org:
            # For organizations: user must be a member
            membership = UserOrganization.get_or_none(
                (UserOrganization.user == user.id)
                & (UserOrganization.organization == org.id)
            )
            can_see_private = membership is not None
        else:
            # For users: user must be viewing their own profile
            can_see_private = user.username == namespace

    # Get storage info
    info = get_storage_info(namespace, is_org)

    # Build response based on permissions
    response_data = {
        "namespace": namespace,
        "is_organization": is_org,
        # Public storage (always visible)
        "public_quota_bytes": info["public_quota_bytes"],
        "public_used_bytes": info["public_used_bytes"],
        "public_available_bytes": info["public_available_bytes"],
        "public_percentage_used": info["public_percentage_used"],
        # Permission indicator
        "can_see_private": can_see_private,
    }

    # Add private storage info if user has permission
    if can_see_private:
        response_data.update(
            {
                "private_quota_bytes": info["private_quota_bytes"],
                "private_used_bytes": info["private_used_bytes"],
                "private_available_bytes": info["private_available_bytes"],
                "private_percentage_used": info["private_percentage_used"],
                "total_used_bytes": info["total_used_bytes"],
            }
        )
    else:
        # Only show public usage total
        response_data["total_used_bytes"] = info["public_used_bytes"]

    return PublicQuotaInfo(**response_data)
