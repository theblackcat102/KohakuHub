"""Admin API endpoints - requires admin secret token authentication."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from peewee import fn
from pydantic import BaseModel

from kohakuhub.config import cfg
from kohakuhub.db import Commit, File, LFSObjectHistory, Organization, Repository, User
from kohakuhub.db_async import (
    create_user,
    delete_repository,
    delete_user,
    execute_db_query,
)
from kohakuhub.logger import get_logger
from kohakuhub.api.utils.quota import (
    get_storage_info,
    set_quota,
    update_namespace_storage,
)
from kohakuhub.api.utils.s3 import get_s3_client
from kohakuhub.async_utils import run_in_s3_executor

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


# ===== Repository Management Endpoints =====


@router.get("/repositories")
async def list_repositories_admin(
    repo_type: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _admin: bool = Depends(verify_admin_token),
):
    """List all repositories with filters.

    Args:
        repo_type: Filter by repository type (model/dataset/space)
        namespace: Filter by namespace
        limit: Maximum number to return
        offset: Offset for pagination
        _admin: Admin authentication (dependency)

    Returns:
        List of repositories with metadata
    """

    def _list_repos():
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
                }
            )

        return repos

    repos = await execute_db_query(_list_repos)

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

    def _get_repo_details():
        repo = Repository.get_or_none(
            Repository.repo_type == repo_type,
            Repository.namespace == namespace,
            Repository.name == name,
        )

        if not repo:
            return None

        # Get owner
        owner = User.get_or_none(User.id == repo.owner_id)

        # Count files
        file_count = File.select().where(File.repo_full_id == repo.full_id).count()

        # Count commits
        commit_count = (
            Commit.select()
            .where(
                Commit.repo_full_id == repo.full_id, Commit.repo_type == repo.repo_type
            )
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
        }

    repo_info = await execute_db_query(_get_repo_details)

    if not repo_info:
        raise HTTPException(
            404,
            detail={"error": f"Repository not found: {repo_type}/{namespace}/{name}"},
        )

    return repo_info


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

    def _list_commits():
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

        return commits

    commits = await execute_db_query(_list_commits)

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

    def _get_detailed_stats():
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
        dataset_repos = (
            Repository.select().where(Repository.repo_type == "dataset").count()
        )
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
            LFSObjectHistory.select(
                fn.SUM(LFSObjectHistory.size).alias("total")
            ).scalar()
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

    stats = await execute_db_query(_get_detailed_stats)

    return stats


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

    def _get_timeseries():
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

    stats = await execute_db_query(_get_timeseries)

    return stats


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

    def _get_top_repos():
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

        return result

    repos = await execute_db_query(_get_top_repos)

    return {"top_repositories": repos, "sorted_by": by}
