"""Authorization and permission checking utilities."""

from typing import Optional

from fastapi import HTTPException

from kohakuhub.db import Repository, User
from kohakuhub.db_operations import get_organization, get_user_organization


def check_namespace_permission(
    namespace: str,
    user: Optional[User],
    require_admin: bool = False,
    is_admin: bool = False,
) -> bool:
    """Check if user has permission to use a namespace.

    Args:
        namespace: The namespace (username or org name)
        user: The authenticated user (None if admin token used)
        require_admin: If True, require admin/super-admin role for orgs
        is_admin: If True, bypass all checks (admin token authenticated)

    Returns:
        True if user has permission

    Raises:
        HTTPException: If user doesn't have permission
    """
    # Admin bypass
    if is_admin:
        return True

    if not user:
        raise HTTPException(403, detail="User authentication required")

    # User's own namespace
    if namespace == user.username:
        return True

    # Check if it's an organization
    org = get_organization(namespace)
    if not org:
        raise HTTPException(
            403,
            detail=f"Namespace '{namespace}' does not exist or you don't have access",
        )

    # Check user's membership in the organization
    membership = get_user_organization(user, org)

    if not membership:
        raise HTTPException(
            403, detail=f"You are not a member of organization '{namespace}'"
        )

    # If admin required, check role
    if require_admin and membership.role not in ["admin", "super-admin"]:
        raise HTTPException(
            403, detail=f"You need admin privileges in organization '{namespace}'"
        )

    return True


def check_repo_read_permission(
    repo: Repository, user: Optional[User] = None, is_admin: bool = False
) -> bool:
    """Check if user can read a repository.

    Public repos: anyone can read
    Private repos: only creator or org members can read

    Args:
        repo: The repository to check
        user: The authenticated user (optional for public repos)
        is_admin: If True, bypass all checks (admin token authenticated)

    Returns:
        True if user has permission

    Raises:
        HTTPException: If user doesn't have permission
    """
    # Admin bypass
    if is_admin:
        return True

    # Public repos are accessible to everyone
    if not repo.private:
        return True

    # Private repos require authentication
    if not user:
        raise HTTPException(
            401, detail="Authentication required to access private repository"
        )

    # Check if user is the creator (namespace matches username)
    if repo.namespace == user.username:
        return True

    # Check if namespace is an organization and user is a member
    org = get_organization(repo.namespace)
    if org:
        membership = get_user_organization(user, org)
        if membership:
            return True

    raise HTTPException(
        403, detail=f"You don't have access to private repository '{repo.full_id}'"
    )


def check_repo_write_permission(
    repo: Repository, user: Optional[User], is_admin: bool = False
) -> bool:
    """Check if user can modify a repository.

    Users can modify:
    - Their own repos
    - Repos in orgs where they are member/admin/super-admin

    Args:
        repo: The repository to check
        user: The authenticated user (None if admin token used)
        is_admin: If True, bypass all checks (admin token authenticated)

    Returns:
        True if user has permission

    Raises:
        HTTPException: If user doesn't have permission
    """
    # Admin bypass
    if is_admin:
        return True

    if not user:
        raise HTTPException(403, detail="User authentication required")

    # Check if user owns the repo (namespace matches username)
    if repo.namespace == user.username:
        return True

    # Check if namespace is an organization and user is a member
    org = get_organization(repo.namespace)
    if org:
        membership = get_user_organization(user, org)
        if membership:
            # Any member can write (visitor role can also read but not write)
            if membership.role in ["member", "admin", "super-admin"]:
                return True

    raise HTTPException(
        403, detail=f"You don't have permission to modify repository '{repo.full_id}'"
    )


def check_repo_delete_permission(
    repo: Repository, user: Optional[User], is_admin: bool = False
) -> bool:
    """Check if user can delete a repository.

    Users can delete:
    - Their own repos
    - Repos in orgs where they are admin/super-admin

    Args:
        repo: The repository to check
        user: The authenticated user (None if admin token used)
        is_admin: If True, bypass all checks (admin token authenticated)

    Returns:
        True if user has permission

    Raises:
        HTTPException: If user doesn't have permission
    """
    # Admin bypass
    if is_admin:
        return True

    if not user:
        raise HTTPException(403, detail="User authentication required")

    # Check if user owns the repo (namespace matches username)
    if repo.namespace == user.username:
        return True

    # Check if namespace is an organization and user is admin
    org = get_organization(repo.namespace)
    if org:
        membership = get_user_organization(user, org)
        if membership and membership.role in ["admin", "super-admin"]:
            return True

    raise HTTPException(
        403, detail=f"You don't have permission to delete repository '{repo.full_id}'"
    )
