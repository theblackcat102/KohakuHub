"""Quota management endpoints for admin API."""

from fastapi import APIRouter, Depends, HTTPException
from peewee import fn
from pydantic import BaseModel

from kohakuhub.db import LFSObjectHistory, Repository, User
from kohakuhub.logger import get_logger
from kohakuhub.api.admin.utils import verify_admin_token
from kohakuhub.api.quota.util import (
    get_repo_storage_info,
    get_storage_info,
    set_quota,
    update_namespace_storage,
    update_repository_storage,
)

logger = get_logger("ADMIN")
router = APIRouter()


# ===== Models =====

# NOTE: Route order matters! Specific routes like /quota/overview must come
# BEFORE parameterized routes like /quota/{namespace} to avoid conflicts.


class SetQuotaRequest(BaseModel):
    """Request to set quota."""

    private_quota_bytes: int | None = None
    public_quota_bytes: int | None = None


# ===== Endpoints =====

# IMPORTANT: /quota/overview must come BEFORE /quota/{namespace}
# to avoid "overview" being interpreted as a namespace parameter!


@router.get("/quota/overview")
async def get_quota_overview(
    _admin: bool = Depends(verify_admin_token),
):
    """Get system-wide quota overview with warnings.

    Args:
        _admin: Admin authentication (dependency)

    Returns:
        Users/repos over quota, top consumers, system totals
    """

    # Users over quota
    users_over = []
    for user in User.select().where(User.is_org == False):
        private_pct = (
            (user.private_used_bytes / user.private_quota_bytes * 100)
            if user.private_quota_bytes
            else 0
        )
        public_pct = (
            (user.public_used_bytes / user.public_quota_bytes * 100)
            if user.public_quota_bytes
            else 0
        )

        if private_pct > 100 or public_pct > 100:
            users_over.append(
                {
                    "username": user.username,
                    "private_percentage": round(private_pct, 1),
                    "public_percentage": round(public_pct, 1),
                    "private_used": user.private_used_bytes,
                    "private_quota": user.private_quota_bytes,
                    "public_used": user.public_used_bytes,
                    "public_quota": user.public_quota_bytes,
                }
            )

    # Repos over quota
    repos_over = []
    for repo in Repository.select():
        info = get_repo_storage_info(repo)
        if info["percentage_used"] and info["percentage_used"] > 100:
            repos_over.append(
                {
                    "full_id": repo.full_id,
                    "repo_type": repo.repo_type,
                    "used_bytes": info["used_bytes"],
                    "quota_bytes": info["quota_bytes"],
                    "percentage": round(info["percentage_used"], 1),
                }
            )

    # Top consumers (users + orgs by total storage)
    top_consumers = (
        User.select(
            User.username,
            User.is_org,
            (User.private_used_bytes + User.public_used_bytes).alias("total"),
        )
        .order_by((User.private_used_bytes + User.public_used_bytes).desc())
        .limit(10)
    )

    # System totals
    total_private = (
        User.select(fn.SUM(User.private_used_bytes))
        .where(User.is_org == False)
        .scalar()
        or 0
    )
    total_public = (
        User.select(fn.SUM(User.public_used_bytes)).where(User.is_org == False).scalar()
        or 0
    )
    total_lfs = LFSObjectHistory.select(fn.SUM(LFSObjectHistory.size)).scalar() or 0

    return {
        "users_over_quota": users_over,
        "repos_over_quota": repos_over,
        "top_consumers": [
            {
                "username": c.username,
                "is_org": c.is_org,
                "total_bytes": c.total,
            }
            for c in top_consumers
        ],
        "system_storage": {
            "private_used": total_private,
            "public_used": total_public,
            "lfs_used": total_lfs,
            "total_used": total_private + total_public,
        },
    }


@router.get("/quota/{namespace}")
async def get_quota_admin(
    namespace: str,
    is_org: bool = False,
    _admin: bool = Depends(verify_admin_token),
):
    """Get storage quota information for a user or organization.

    Args:
        namespace: Username or organization name
        is_org: True if namespace is an organization
        _admin: Admin authentication (dependency)

    Returns:
        Quota information

    Raises:
        HTTPException: If namespace not found
    """

    # Check if namespace exists
    if is_org:
        entity = User.get_or_none((User.username == namespace) & (User.is_org == True))
    else:
        entity = User.get_or_none((User.username == namespace) & (User.is_org == False))

    if not entity:
        raise HTTPException(
            404,
            detail={
                "error": f"{'Organization' if is_org else 'User'} not found: {namespace}"
            },
        )

    info = get_storage_info(namespace, is_org)

    return {
        "namespace": namespace,
        "is_organization": is_org,
        **info,
    }


@router.put("/quota/{namespace}")
async def set_quota_admin(
    namespace: str,
    request: SetQuotaRequest,
    is_org: bool = False,
    _admin: bool = Depends(verify_admin_token),
):
    """Set storage quota for a user or organization (admin only).

    Args:
        namespace: Username or organization name
        request: Quota settings
        is_org: True if namespace is an organization
        _admin: Admin authentication (dependency)

    Returns:
        Updated quota information

    Raises:
        HTTPException: If namespace not found
    """

    # Check if namespace exists
    if is_org:
        entity = User.get_or_none((User.username == namespace) & (User.is_org == True))
    else:
        entity = User.get_or_none((User.username == namespace) & (User.is_org == False))

    if not entity:
        raise HTTPException(
            404,
            detail={
                "error": f"{'Organization' if is_org else 'User'} not found: {namespace}"
            },
        )

    info = set_quota(
        namespace,
        private_quota_bytes=request.private_quota_bytes,
        public_quota_bytes=request.public_quota_bytes,
        is_org=is_org,
    )

    logger.info(
        f"Admin set quota for {'org' if is_org else 'user'} {namespace}: "
        f"private={request.private_quota_bytes}, public={request.public_quota_bytes}"
    )

    return {
        "namespace": namespace,
        "is_organization": is_org,
        **info,
    }


@router.post("/quota/{namespace}/recalculate")
async def recalculate_quota_admin(
    namespace: str,
    is_org: bool = False,
    _admin: bool = Depends(verify_admin_token),
):
    """Recalculate storage usage for a user or organization (admin only).

    Args:
        namespace: Username or organization name
        is_org: True if namespace is an organization
        _admin: Admin authentication (dependency)

    Returns:
        Updated quota information

    Raises:
        HTTPException: If namespace not found
    """

    # Check if namespace exists
    if is_org:
        entity = User.get_or_none((User.username == namespace) & (User.is_org == True))
    else:
        entity = User.get_or_none((User.username == namespace) & (User.is_org == False))

    if not entity:
        raise HTTPException(
            404,
            detail={
                "error": f"{'Organization' if is_org else 'User'} not found: {namespace}"
            },
        )

    logger.info(
        f"Admin recalculating storage for {'org' if is_org else 'user'} {namespace}"
    )

    storage = await update_namespace_storage(namespace, is_org)
    info = get_storage_info(namespace, is_org)

    return {
        "namespace": namespace,
        "is_organization": is_org,
        "recalculated": storage,
        **info,
    }


@router.post("/repositories/recalculate-all")
async def recalculate_all_repo_storage_admin(
    repo_type: str | None = None,
    namespace: str | None = None,
    _admin: bool = Depends(verify_admin_token),
):
    """Recalculate storage usage for all repositories (admin only).

    This is a bulk operation that recalculates storage for all repositories
    matching the optional filters. Can be slow for large datasets.

    Args:
        repo_type: Optional filter by repository type
        namespace: Optional filter by namespace
        _admin: Admin authentication (dependency)

    Returns:
        Recalculation summary with success/failure counts
    """

    logger.warning("Admin initiated bulk repository storage recalculation")

    # Get all repositories matching filters
    query = Repository.select()
    if repo_type:
        query = query.where(Repository.repo_type == repo_type)
    if namespace:
        query = query.where(Repository.namespace == namespace)

    repos = list(query)
    total = len(repos)

    logger.info(f"Recalculating storage for {total} repository(ies)")

    # Recalculate storage for each repository
    success_count = 0
    failure_count = 0
    failures = []

    for repo in repos:
        try:
            await update_repository_storage(repo)
            success_count += 1

            if success_count % 10 == 0:
                logger.info(
                    f"Progress: {success_count}/{total} repositories recalculated"
                )
        except Exception as e:
            failure_count += 1
            failures.append(
                {
                    "repo_id": repo.full_id,
                    "error": str(e),
                }
            )
            logger.error(f"Failed to recalculate storage for {repo.full_id}: {e}")

    logger.info(
        f"Bulk recalculation completed: {success_count} succeeded, {failure_count} failed"
    )

    return {
        "total": total,
        "success_count": success_count,
        "failure_count": failure_count,
        "failures": failures,
        "message": f"Recalculated storage for {success_count}/{total} repositories",
    }
