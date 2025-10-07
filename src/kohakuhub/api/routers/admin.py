"""Admin API endpoints - requires admin secret token authentication."""

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from kohakuhub.api.utils.quota import (
    get_storage_info,
    set_quota,
    update_namespace_storage,
)
from kohakuhub.config import cfg
from kohakuhub.db import Organization, User
from kohakuhub.db_async import create_user, delete_user, execute_db_query
from kohakuhub.logger import get_logger

logger = get_logger("ADMIN")
router = APIRouter()


# ===== Admin Authentication =====


async def verify_admin_token(x_admin_token: str | None = Header(None)) -> bool:
    """Verify admin secret token from header using constant-time comparison.

    Uses SHA3-512 hash with secrets.compare_digest() to prevent timing attacks.

    Args:
        x_admin_token: Admin token from X-Admin-Token header

    Returns:
        True if valid

    Raises:
        HTTPException: If admin API is disabled or token is invalid
    """
    if not cfg.admin.enabled:
        raise HTTPException(
            503,
            detail={"error": "Admin API is disabled"},
        )

    if not x_admin_token:
        raise HTTPException(
            401,
            detail={"error": "Admin token required in X-Admin-Token header"},
        )

    # Hash both tokens with SHA3-512 and compare using constant-time comparison
    # This prevents timing attacks that could leak token information
    provided_hash = hashlib.sha3_512(x_admin_token.encode()).hexdigest()
    expected_hash = hashlib.sha3_512(cfg.admin.secret_token.encode()).hexdigest()

    if not secrets.compare_digest(provided_hash, expected_hash):
        raise HTTPException(
            403,
            detail={"error": "Invalid admin token"},
        )

    return True


# ===== Models =====


class UserInfo(BaseModel):
    """User information response."""

    id: int
    username: str
    email: str
    email_verified: bool
    is_active: bool
    private_quota_bytes: int | None
    public_quota_bytes: int | None
    private_used_bytes: int
    public_used_bytes: int
    created_at: str


class CreateUserRequest(BaseModel):
    """Request to create a new user."""

    username: str
    email: str
    password: str
    email_verified: bool = False
    is_active: bool = True
    private_quota_bytes: int | None = None
    public_quota_bytes: int | None = None


class SetQuotaRequest(BaseModel):
    """Request to set quota."""

    private_quota_bytes: int | None = None
    public_quota_bytes: int | None = None


# ===== User Management Endpoints =====


@router.get("/users/{username}")
async def get_user_info(
    username: str,
    _admin: bool = Depends(verify_admin_token),
):
    """Get detailed user information.

    Args:
        username: Username to query
        _admin: Admin authentication (dependency)

    Returns:
        User information

    Raises:
        HTTPException: If user not found
    """

    def _get_user():
        return User.get_or_none(User.username == username)

    user = await execute_db_query(_get_user)

    if not user:
        raise HTTPException(404, detail={"error": f"User not found: {username}"})

    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        email_verified=user.email_verified,
        is_active=user.is_active,
        private_quota_bytes=user.private_quota_bytes,
        public_quota_bytes=user.public_quota_bytes,
        private_used_bytes=user.private_used_bytes,
        public_used_bytes=user.public_used_bytes,
        created_at=user.created_at.isoformat(),
    )


@router.get("/users")
async def list_users(
    limit: int = 100,
    offset: int = 0,
    _admin: bool = Depends(verify_admin_token),
):
    """List all users with quota information.

    Args:
        limit: Maximum number of users to return
        offset: Offset for pagination
        _admin: Admin authentication (dependency)

    Returns:
        List of users with quota information
    """

    def _list_users():
        users = User.select().limit(limit).offset(offset)
        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "email_verified": u.email_verified,
                "is_active": u.is_active,
                "private_quota_bytes": u.private_quota_bytes,
                "public_quota_bytes": u.public_quota_bytes,
                "private_used_bytes": u.private_used_bytes,
                "public_used_bytes": u.public_used_bytes,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]

    users = await execute_db_query(_list_users)

    return {"users": users, "limit": limit, "offset": offset}


@router.post("/users")
async def create_user_admin(
    request: CreateUserRequest,
    _admin: bool = Depends(verify_admin_token),
):
    """Create a new user (admin only).

    Args:
        request: User creation request
        _admin: Admin authentication (dependency)

    Returns:
        Created user information

    Raises:
        HTTPException: If username or email already exists
    """
    import bcrypt

    # Check if user already exists
    def _check_exists():
        return (
            User.get_or_none(User.username == request.username),
            User.get_or_none(User.email == request.email),
        )

    existing_username, existing_email = await execute_db_query(_check_exists)

    if existing_username:
        raise HTTPException(
            400, detail={"error": f"Username already exists: {request.username}"}
        )

    if existing_email:
        raise HTTPException(
            400, detail={"error": f"Email already exists: {request.email}"}
        )

    # Hash password
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()

    # Create user with quotas (defaults applied if not specified)
    user = await create_user(
        username=request.username,
        email=request.email,
        password_hash=password_hash,
        email_verified=request.email_verified,
        is_active=request.is_active,
        private_quota_bytes=request.private_quota_bytes,
        public_quota_bytes=request.public_quota_bytes,
    )

    logger.info(f"Admin created user: {user.username}")

    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        email_verified=user.email_verified,
        is_active=user.is_active,
        private_quota_bytes=user.private_quota_bytes,
        public_quota_bytes=user.public_quota_bytes,
        private_used_bytes=user.private_used_bytes,
        public_used_bytes=user.public_used_bytes,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/users/{username}")
async def delete_user_admin(
    username: str,
    force: bool = False,
    _admin: bool = Depends(verify_admin_token),
):
    """Delete a user (admin only).

    WARNING: This will delete all user's sessions, tokens, and org memberships.
    Repositories owned by the user will be transferred to a default admin user
    or deleted if force=true.

    Args:
        username: Username to delete
        force: If true, delete user even if they own repositories (repositories will be deleted)
        _admin: Admin authentication (dependency)

    Returns:
        Success message with deletion info

    Raises:
        HTTPException: If user not found or has repositories (without force)
    """

    def _get_user_and_repos():
        from kohakuhub.db import Repository

        user = User.get_or_none(User.username == username)
        if not user:
            return None, []

        # Get all repositories owned by this user
        repos = list(Repository.select().where(Repository.owner_id == user.id))
        return user, repos

    user, owned_repos = await execute_db_query(_get_user_and_repos)

    if not user:
        raise HTTPException(404, detail={"error": f"User not found: {username}"})

    # Check if user owns repositories
    if owned_repos and not force:
        raise HTTPException(
            400,
            detail={
                "error": "User owns repositories",
                "message": f"User owns {len(owned_repos)} repository(ies). Use force=true to delete user and their repositories.",
                "owned_repositories": [
                    f"{r.repo_type}:{r.full_id}" for r in owned_repos
                ],
            },
        )

    # Delete user's repositories if force=true
    deleted_repos = []
    if owned_repos and force:
        from kohakuhub.db_async import delete_repository

        for repo in owned_repos:
            await delete_repository(repo)
            deleted_repos.append(f"{repo.repo_type}:{repo.full_id}")
            logger.warning(f"Admin deleted repository: {repo.full_id}")

    # Delete user
    await delete_user(user)

    logger.warning(
        f"Admin deleted user: {username} (deleted {len(deleted_repos)} repositories)"
    )

    return {
        "message": f"User deleted: {username}",
        "deleted_repositories": deleted_repos,
    }


@router.patch("/users/{username}/email-verification")
async def set_email_verification(
    username: str,
    verified: bool,
    _admin: bool = Depends(verify_admin_token),
):
    """Set email verification status for a user.

    Args:
        username: Username to update
        verified: Email verification status
        _admin: Admin authentication (dependency)

    Returns:
        Updated user information

    Raises:
        HTTPException: If user not found
    """

    def _update_user():
        user = User.get_or_none(User.username == username)
        if not user:
            return None
        user.email_verified = verified
        user.save()
        return user

    user = await execute_db_query(_update_user)

    if not user:
        raise HTTPException(404, detail={"error": f"User not found: {username}"})

    logger.info(f"Admin set email_verified={verified} for user: {username}")

    return {
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
    }


# ===== Quota Management Endpoints =====


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
    def _check_exists():
        if is_org:
            return Organization.get_or_none(Organization.name == namespace)
        else:
            return User.get_or_none(User.username == namespace)

    entity = await execute_db_query(_check_exists)

    if not entity:
        raise HTTPException(
            404,
            detail={
                "error": f"{'Organization' if is_org else 'User'} not found: {namespace}"
            },
        )

    info = await get_storage_info(namespace, is_org)

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
    def _check_exists():
        if is_org:
            return Organization.get_or_none(Organization.name == namespace)
        else:
            return User.get_or_none(User.username == namespace)

    entity = await execute_db_query(_check_exists)

    if not entity:
        raise HTTPException(
            404,
            detail={
                "error": f"{'Organization' if is_org else 'User'} not found: {namespace}"
            },
        )

    info = await set_quota(
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
    def _check_exists():
        if is_org:
            return Organization.get_or_none(Organization.name == namespace)
        else:
            return User.get_or_none(User.username == namespace)

    entity = await execute_db_query(_check_exists)

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
    info = await get_storage_info(namespace, is_org)

    return {
        "namespace": namespace,
        "is_organization": is_org,
        "recalculated": storage,
        **info,
    }


# ===== System Information =====


@router.get("/stats")
async def get_system_stats(
    _admin: bool = Depends(verify_admin_token),
):
    """Get system statistics.

    Args:
        _admin: Admin authentication (dependency)

    Returns:
        System statistics
    """

    def _get_stats():
        from kohakuhub.db import Repository

        user_count = User.select().count()
        org_count = Organization.select().count()
        repo_count = Repository.select().count()
        private_repo_count = (
            Repository.select().where(Repository.private == True).count()
        )
        public_repo_count = (
            Repository.select().where(Repository.private == False).count()
        )

        return {
            "users": user_count,
            "organizations": org_count,
            "repositories": {
                "total": repo_count,
                "private": private_repo_count,
                "public": public_repo_count,
            },
        }

    stats = await execute_db_query(_get_stats)

    return stats
