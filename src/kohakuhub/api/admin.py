"""Admin API endpoints - requires admin secret token authentication."""

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from peewee import fn
from pydantic import BaseModel

from kohakuhub.async_utils import run_in_s3_executor
from kohakuhub.config import cfg
from kohakuhub.db import (
    db,
    Commit,
    File,
    LFSObjectHistory,
    Organization,
    Repository,
    User,
)
from kohakuhub.db_operations import (
    check_invitation_available,
    create_invitation,
    create_user,
    delete_invitation,
    delete_repository,
    delete_user,
    get_invitation,
)
from kohakuhub.logger import get_logger
from kohakuhub.utils.s3 import get_s3_client
from kohakuhub.api.quota.util import (
    get_storage_info,
    set_quota,
    update_namespace_storage,
    get_repo_storage_info,
    update_repository_storage,
)

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


class CreateRegisterInvitationRequest(BaseModel):
    """Request to create registration invitation."""

    org_id: int | None = None  # Optional organization to join after registration
    role: str = "member"  # Role in organization (if org_id provided)
    max_usage: int | None = None  # None=one-time, -1=unlimited, N=max uses
    expires_days: int = 7  # Days until expiration


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

    user = User.get_or_none(User.username == username)

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

    users_query = User.select().limit(limit).offset(offset)
    users = [
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
        for u in users_query
    ]

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

    # Hash password
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()

    # Check if user already exists and create atomically
    with db.atomic():
        existing_username = User.get_or_none(User.username == request.username)
        if existing_username:
            raise HTTPException(
                400, detail={"error": f"Username already exists: {request.username}"}
            )

        existing_email = User.get_or_none(User.email == request.email)
        if existing_email:
            raise HTTPException(
                400, detail={"error": f"Email already exists: {request.email}"}
            )

        # Create user with quotas (defaults applied if not specified)
        user = create_user(
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

    user = User.get_or_none(User.username == username)

    if not user:
        raise HTTPException(404, detail={"error": f"User not found: {username}"})

    # Get all repositories owned by this user
    owned_repos = list(Repository.select().where(Repository.owner_id == user.id))

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
        # Delete repositories sequentially (sync DB operations)
        for repo in owned_repos:
            delete_repository(repo)
            logger.warning(f"Admin deleted repository: {repo.full_id}")
            deleted_repos.append(f"{repo.repo_type}:{repo.full_id}")

    # Delete user (already has db.atomic() inside)
    delete_user(user)

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

    user = User.get_or_none(User.username == username)
    if not user:
        raise HTTPException(404, detail={"error": f"User not found: {username}"})

    user.email_verified = verified
    user.save()

    logger.info(f"Admin set email_verified={verified} for user: {username}")

    return {
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
    }


# ===== Invitation Management Endpoints =====


@router.post("/invitations/register")
async def create_register_invitation_admin(
    request: CreateRegisterInvitationRequest,
    _admin: bool = Depends(verify_admin_token),
):
    """Create registration invitation (admin only).

    Allows admin to generate invitations for user registration.
    If invitation_only mode is enabled, this is the only way users can register.

    Args:
        request: Invitation creation request
        _admin: Admin authentication (dependency)

    Returns:
        Created invitation token and link
    """
    import json

    # Validate role if org_id provided
    if request.org_id:
        if request.role not in ["visitor", "member", "admin"]:
            raise HTTPException(
                400, detail={"error": "Invalid role. Must be visitor, member, or admin"}
            )

        # Verify organization exists
        org = Organization.get_or_none(Organization.id == request.org_id)
        if not org:
            raise HTTPException(404, detail={"error": f"Organization not found: {request.org_id}"})

        org_name = org.name
    else:
        org_name = None

    # Generate invitation token
    token = secrets.token_urlsafe(32)

    # Set expiration
    expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_days)

    # Create parameters
    parameters = json.dumps(
        {
            "org_id": request.org_id,
            "org_name": org_name,
            "role": request.role if request.org_id else None,
        }
    )

    # Create invitation (no created_by for admin-generated invitations, use system user ID 1)
    invitation = create_invitation(
        token=token,
        action="register_account",
        parameters=parameters,
        created_by=1,  # System/Admin user
        expires_at=expires_at,
        max_usage=request.max_usage,
    )

    invitation_link = f"{cfg.app.base_url}/register?invitation={token}"

    logger.success(
        f"Admin created registration invitation (max_usage={request.max_usage}, expires={request.expires_days}d)"
    )

    return {
        "success": True,
        "token": token,
        "invitation_link": invitation_link,
        "expires_at": expires_at.isoformat(),
        "max_usage": request.max_usage,
        "is_reusable": request.max_usage is not None,
        "action": "register_account",
    }


@router.get("/invitations")
async def list_invitations_admin(
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _admin: bool = Depends(verify_admin_token),
):
    """List all invitations (admin only).

    Args:
        action: Filter by action type (join_org, register_account)
        limit: Maximum number to return
        offset: Offset for pagination
        _admin: Admin authentication (dependency)

    Returns:
        List of invitations with details
    """
    from kohakuhub.db import Invitation

    query = Invitation.select()

    if action:
        query = query.where(Invitation.action == action)

    query = query.order_by(Invitation.created_at.desc()).limit(limit).offset(offset)

    invitations = []
    for inv in query:
        # Get creator username
        creator = User.get_or_none(User.id == inv.created_by)
        creator_username = creator.username if creator else "System"

        # Parse parameters
        try:
            params = json.loads(inv.parameters)
        except json.JSONDecodeError:
            params = {}

        # Check availability
        is_available, error_msg = check_invitation_available(inv)

        invitations.append(
            {
                "id": inv.id,
                "token": inv.token,
                "action": inv.action,
                "org_id": params.get("org_id"),
                "org_name": params.get("org_name"),
                "role": params.get("role"),
                "email": params.get("email"),
                "created_by": inv.created_by,
                "creator_username": creator_username,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat(),
                "max_usage": inv.max_usage,
                "usage_count": inv.usage_count,
                "is_reusable": inv.max_usage is not None,
                "is_available": is_available,
                "error_message": error_msg,
                "used_at": inv.used_at.isoformat() if inv.used_at else None,
                "used_by": inv.used_by,
            }
        )

    return {"invitations": invitations, "limit": limit, "offset": offset}


@router.delete("/invitations/{token}")
async def delete_invitation_admin(
    token: str,
    _admin: bool = Depends(verify_admin_token),
):
    """Delete invitation (admin only).

    Args:
        token: Invitation token
        _admin: Admin authentication (dependency)

    Returns:
        Success message
    """
    invitation = get_invitation(token)

    if not invitation:
        raise HTTPException(404, detail={"error": "Invitation not found"})

    delete_invitation(invitation)

    logger.info(f"Admin deleted invitation: {token[:8]}... (action={invitation.action})")

    return {"success": True, "message": "Invitation deleted successfully"}


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
    if is_org:
        entity = Organization.get_or_none(Organization.name == namespace)
    else:
        entity = User.get_or_none(User.username == namespace)

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
        entity = Organization.get_or_none(Organization.name == namespace)
    else:
        entity = User.get_or_none(User.username == namespace)

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
        entity = Organization.get_or_none(Organization.name == namespace)
    else:
        entity = User.get_or_none(User.username == namespace)

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

    user_count = User.select().count()
    org_count = Organization.select().count()
    repo_count = Repository.select().count()
    private_repo_count = Repository.select().where(Repository.private == True).count()
    public_repo_count = Repository.select().where(Repository.private == False).count()

    return {
        "users": user_count,
        "organizations": org_count,
        "repositories": {
            "total": repo_count,
            "private": private_repo_count,
            "public": public_repo_count,
        },
    }


# ===== Repository Management Endpoints =====


@router.get("/repositories")
async def list_repositories_admin(
    repo_type: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _admin: bool = Depends(verify_admin_token),
):
    """List all repositories with filters and storage information.

    Args:
        repo_type: Filter by repository type (model/dataset/space)
        namespace: Filter by namespace
        limit: Maximum number to return
        offset: Offset for pagination
        _admin: Admin authentication (dependency)

    Returns:
        List of repositories with metadata and storage info
    """

    query = Repository.select()
    if repo_type:
        query = query.where(Repository.repo_type == repo_type)
    if namespace:
        query = query.where(Repository.namespace == namespace)

    query = query.order_by(Repository.created_at.desc()).limit(limit).offset(offset)

    repos = []
    for repo in query:
        # Get owner username
        owner = User.get_or_none(User.id == repo.owner_id)
        owner_username = owner.username if owner else "unknown"

        # Get storage info
        storage_info = get_repo_storage_info(repo)

        repos.append(
            {
                "id": repo.id,
                "repo_type": repo.repo_type,
                "namespace": repo.namespace,
                "name": repo.name,
                "full_id": repo.full_id,
                "private": repo.private,
                "owner_id": repo.owner_id,
                "owner_username": owner_username,
                "created_at": repo.created_at.isoformat(),
                # Storage information
                "quota_bytes": storage_info["quota_bytes"],
                "used_bytes": storage_info["used_bytes"],
                "percentage_used": storage_info["percentage_used"],
                "is_inheriting": storage_info["is_inheriting"],
            }
        )

    return {"repositories": repos, "limit": limit, "offset": offset}


@router.get("/repositories/{repo_type}/{namespace}/{name}")
async def get_repository_admin(
    repo_type: str,
    namespace: str,
    name: str,
    _admin: bool = Depends(verify_admin_token),
):
    """Get detailed repository information.

    Args:
        repo_type: Repository type
        namespace: Repository namespace
        name: Repository name
        _admin: Admin authentication (dependency)

    Returns:
        Repository details including file count and commit count

    Raises:
        HTTPException: If repository not found
    """

    repo = Repository.get_or_none(
        Repository.repo_type == repo_type,
        Repository.namespace == namespace,
        Repository.name == name,
    )

    if not repo:
        raise HTTPException(
            404,
            detail={"error": f"Repository not found: {repo_type}/{namespace}/{name}"},
        )

    # Get owner
    owner = User.get_or_none(User.id == repo.owner_id)

    # Count files
    file_count = File.select().where(File.repo_full_id == repo.full_id).count()

    # Count commits
    commit_count = (
        Commit.select()
        .where(Commit.repo_full_id == repo.full_id, Commit.repo_type == repo.repo_type)
        .count()
    )

    # Get total file size
    total_size = (
        File.select()
        .where(File.repo_full_id == repo.full_id)
        .select(File.size)
        .scalar(as_tuple=False)
    )
    if total_size is None:
        total_size = 0

    # Get storage info
    storage_info = get_repo_storage_info(repo)

    return {
        "id": repo.id,
        "repo_type": repo.repo_type,
        "namespace": repo.namespace,
        "name": repo.name,
        "full_id": repo.full_id,
        "private": repo.private,
        "owner_id": repo.owner_id,
        "owner_username": owner.username if owner else "unknown",
        "created_at": repo.created_at.isoformat(),
        "file_count": file_count,
        "commit_count": commit_count,
        "total_size": total_size,
        # Storage information
        "quota_bytes": storage_info["quota_bytes"],
        "used_bytes": storage_info["used_bytes"],
        "percentage_used": storage_info["percentage_used"],
        "is_inheriting": storage_info["is_inheriting"],
    }


# ===== Commit History Endpoints =====


@router.get("/commits")
async def list_commits_admin(
    repo_full_id: str | None = None,
    username: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _admin: bool = Depends(verify_admin_token),
):
    """List commits with filters.

    Args:
        repo_full_id: Filter by repository full ID
        username: Filter by author username
        limit: Maximum number to return
        offset: Offset for pagination
        _admin: Admin authentication (dependency)

    Returns:
        List of commits
    """

    query = Commit.select()

    if repo_full_id:
        query = query.where(Commit.repo_full_id == repo_full_id)
    if username:
        query = query.where(Commit.username == username)

    query = query.order_by(Commit.created_at.desc()).limit(limit).offset(offset)

    commits = []
    for commit in query:
        commits.append(
            {
                "id": commit.id,
                "commit_id": commit.commit_id,
                "repo_full_id": commit.repo_full_id,
                "repo_type": commit.repo_type,
                "branch": commit.branch,
                "user_id": commit.user_id,
                "username": commit.username,
                "message": commit.message,
                "description": commit.description,
                "created_at": commit.created_at.isoformat(),
            }
        )

    return {"commits": commits, "limit": limit, "offset": offset}


# ===== S3 Storage Information =====


@router.get("/storage/buckets")
async def list_s3_buckets(
    _admin: bool = Depends(verify_admin_token),
):
    """List S3 buckets and their sizes.

    Args:
        _admin: Admin authentication (dependency)

    Returns:
        List of buckets with sizes
    """

    def _list_buckets():
        s3 = get_s3_client()
        buckets = s3.list_buckets()

        bucket_info = []
        for bucket in buckets.get("Buckets", []):
            bucket_name = bucket["Name"]

            # Get bucket size (sum of all objects)
            try:
                total_size = 0
                paginator = s3.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket_name):
                    for obj in page.get("Contents", []):
                        total_size += obj.get("Size", 0)

                object_count = sum(
                    len(page.get("Contents", []))
                    for page in paginator.paginate(Bucket=bucket_name)
                )

                bucket_info.append(
                    {
                        "name": bucket_name,
                        "creation_date": bucket["CreationDate"].isoformat(),
                        "total_size": total_size,
                        "object_count": object_count,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to get size for bucket {bucket_name}: {e}")
                bucket_info.append(
                    {
                        "name": bucket_name,
                        "creation_date": bucket["CreationDate"].isoformat(),
                        "total_size": 0,
                        "object_count": 0,
                        "error": str(e),
                    }
                )

        return bucket_info

    buckets = await run_in_s3_executor(_list_buckets)

    return {"buckets": buckets}


@router.get("/storage/objects/{bucket}")
async def list_s3_objects(
    bucket: str,
    prefix: str = "",
    limit: int = 100,
    _admin: bool = Depends(verify_admin_token),
):
    """List S3 objects in a bucket.

    Args:
        bucket: Bucket name
        prefix: Key prefix filter
        limit: Maximum objects to return
        _admin: Admin authentication (dependency)

    Returns:
        List of S3 objects
    """

    def _list_objects():
        s3 = get_s3_client()

        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=limit)

            objects = []
            for obj in response.get("Contents", []):
                objects.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "storage_class": obj.get("StorageClass", "STANDARD"),
                    }
                )

            return {
                "objects": objects,
                "is_truncated": response.get("IsTruncated", False),
                "key_count": len(objects),
            }
        except Exception as e:
            logger.error(f"Failed to list objects in bucket {bucket}: {e}")
            raise HTTPException(500, detail={"error": str(e)})

    result = await run_in_s3_executor(_list_objects)

    return result


# ===== Enhanced Statistics =====


@router.get("/stats/detailed")
async def get_detailed_stats(
    _admin: bool = Depends(verify_admin_token),
):
    """Get detailed system statistics.

    Args:
        _admin: Admin authentication (dependency)

    Returns:
        Detailed statistics from database
    """

    # User stats
    total_users = User.select().count()
    active_users = User.select().where(User.is_active == True).count()
    verified_users = User.select().where(User.email_verified == True).count()

    # Organization stats
    total_orgs = Organization.select().count()

    # Repository stats
    total_repos = Repository.select().count()
    private_repos = Repository.select().where(Repository.private == True).count()
    public_repos = Repository.select().where(Repository.private == False).count()

    # Repos by type
    model_repos = Repository.select().where(Repository.repo_type == "model").count()
    dataset_repos = Repository.select().where(Repository.repo_type == "dataset").count()
    space_repos = Repository.select().where(Repository.repo_type == "space").count()

    # Commit stats
    total_commits = Commit.select().count()

    # Top contributors
    top_contributors = (
        Commit.select(Commit.username, fn.COUNT(Commit.id).alias("commit_count"))
        .group_by(Commit.username)
        .order_by(fn.COUNT(Commit.id).desc())
        .limit(10)
    )

    contributors = [
        {"username": c.username, "commit_count": c.commit_count}
        for c in top_contributors
    ]

    # LFS object stats
    total_lfs_objects = LFSObjectHistory.select().count()
    total_lfs_size = (
        LFSObjectHistory.select(fn.SUM(LFSObjectHistory.size).alias("total")).scalar()
        or 0
    )

    # Storage stats
    total_private_used = (
        User.select(fn.SUM(User.private_used_bytes).alias("total")).scalar() or 0
    )
    total_public_used = (
        User.select(fn.SUM(User.public_used_bytes).alias("total")).scalar() or 0
    )

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
            "inactive": total_users - active_users,
        },
        "organizations": {
            "total": total_orgs,
        },
        "repositories": {
            "total": total_repos,
            "private": private_repos,
            "public": public_repos,
            "by_type": {
                "model": model_repos,
                "dataset": dataset_repos,
                "space": space_repos,
            },
        },
        "commits": {
            "total": total_commits,
            "top_contributors": contributors,
        },
        "lfs": {
            "total_objects": total_lfs_objects,
            "total_size": total_lfs_size,
        },
        "storage": {
            "private_used": total_private_used,
            "public_used": total_public_used,
            "total_used": total_private_used + total_public_used,
        },
    }


@router.get("/stats/timeseries")
async def get_timeseries_stats(
    days: int = Query(default=30, ge=1, le=365),
    _admin: bool = Depends(verify_admin_token),
):
    """Get time-series statistics for charts.

    Args:
        days: Number of days to include
        _admin: Admin authentication (dependency)

    Returns:
        Time-series data for various metrics
    """

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Repositories created per day
    repos_by_day = (
        Repository.select(
            Repository.created_at,
            Repository.repo_type,
        )
        .where(Repository.created_at >= cutoff_date)
        .order_by(Repository.created_at.asc())
    )

    # Group by date
    daily_repos = {}
    for repo in repos_by_day:
        date_key = repo.created_at.date().isoformat()
        if date_key not in daily_repos:
            daily_repos[date_key] = {"model": 0, "dataset": 0, "space": 0}
        daily_repos[date_key][repo.repo_type] += 1

    # Commits created per day
    commits_by_day = (
        Commit.select(Commit.created_at)
        .where(Commit.created_at >= cutoff_date)
        .order_by(Commit.created_at.asc())
    )

    daily_commits = {}
    for commit in commits_by_day:
        date_key = commit.created_at.date().isoformat()
        daily_commits[date_key] = daily_commits.get(date_key, 0) + 1

    # Users created per day
    users_by_day = (
        User.select(User.created_at)
        .where(User.created_at >= cutoff_date)
        .order_by(User.created_at.asc())
    )

    daily_users = {}
    for user in users_by_day:
        date_key = user.created_at.date().isoformat()
        daily_users[date_key] = daily_users.get(date_key, 0) + 1

    return {
        "repositories_by_day": daily_repos,
        "commits_by_day": daily_commits,
        "users_by_day": daily_users,
    }


@router.get("/stats/top-repos")
async def get_top_repositories(
    limit: int = Query(default=10, ge=1, le=100),
    by: str = Query(default="commits", regex="^(commits|size)$"),
    _admin: bool = Depends(verify_admin_token),
):
    """Get top repositories by various metrics.

    Args:
        limit: Number of top repos to return
        by: Sort by 'commits' or 'size'
        _admin: Admin authentication (dependency)

    Returns:
        List of top repositories
    """

    if by == "commits":
        # Top repos by commit count
        top_repos = (
            Commit.select(
                Commit.repo_full_id,
                Commit.repo_type,
                fn.COUNT(Commit.id).alias("count"),
            )
            .group_by(Commit.repo_full_id, Commit.repo_type)
            .order_by(fn.COUNT(Commit.id).desc())
            .limit(limit)
        )

        result = []
        for item in top_repos:
            repo = Repository.get_or_none(
                Repository.full_id == item.repo_full_id,
                Repository.repo_type == item.repo_type,
            )
            result.append(
                {
                    "repo_full_id": item.repo_full_id,
                    "repo_type": item.repo_type,
                    "commit_count": item.count,
                    "private": repo.private if repo else False,
                }
            )

    else:  # by size
        # Top repos by total file size
        top_repos = (
            File.select(File.repo_full_id, fn.SUM(File.size).alias("total_size"))
            .group_by(File.repo_full_id)
            .order_by(fn.SUM(File.size).desc())
            .limit(limit)
        )

        result = []
        for item in top_repos:
            # Find repo in any type
            repo = None
            for repo_type in ["model", "dataset", "space"]:
                r = Repository.get_or_none(
                    Repository.full_id == item.repo_full_id,
                    Repository.repo_type == repo_type,
                )
                if r:
                    repo = r
                    break

            result.append(
                {
                    "repo_full_id": item.repo_full_id,
                    "repo_type": repo.repo_type if repo else "unknown",
                    "total_size": item.total_size,
                    "private": repo.private if repo else False,
                }
            )

    return {"top_repositories": result, "sorted_by": by}
