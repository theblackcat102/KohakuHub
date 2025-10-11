"""User, organization, and repository settings API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from kohakuhub.db import Organization, Repository, User, UserOrganization
from kohakuhub.db_operations import (
    get_organization,
    get_repository,
    get_user_organization,
)
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_current_user
from kohakuhub.auth.permissions import check_repo_delete_permission
from kohakuhub.api.repo.utils.hf import hf_repo_not_found

logger = get_logger("SETTINGS")

router = APIRouter()


# ============================================================================
# User Settings API
# ============================================================================
# Note: /whoami-v2 is implemented in api/routers/misc.py


class UpdateUserSettingsRequest(BaseModel):
    email: Optional[EmailStr] = None
    fullname: Optional[str] = None


@router.put("/users/{username}/settings")
async def update_user_settings(
    username: str,
    req: UpdateUserSettingsRequest,
    user: User = Depends(get_current_user),
):
    """Update user settings.

    Args:
        username: Username to update (must match authenticated user)
        req: Settings to update
        user: Current authenticated user

    Returns:
        Success message
    """
    # Verify user can only update their own settings
    if user.username != username:
        raise HTTPException(403, detail="Not authorized to update this user's settings")

    # Update fields if provided
    if req.email is not None:
        # Check if email is already taken by another user
        existing = User.get_or_none((User.email == req.email) & (User.id != user.id))
        if existing:
            raise HTTPException(400, detail="Email already in use")

        User.update(email=req.email, email_verified=False).where(
            User.id == user.id
        ).execute()
        # TODO: Send new verification email

    return {"success": True, "message": "User settings updated successfully"}


# ============================================================================
# Organization Settings API
# ============================================================================


class UpdateOrganizationSettingsRequest(BaseModel):
    description: Optional[str] = None


@router.put("/organizations/{org_name}/settings")
async def update_organization_settings(
    org_name: str,
    req: UpdateOrganizationSettingsRequest,
    user: User = Depends(get_current_user),
):
    """Update organization settings.

    Args:
        org_name: Organization name
        req: Settings to update
        user: Current authenticated user

    Returns:
        Success message
    """
    org = get_organization(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    # Check if user is admin of the organization
    user_org = get_user_organization(user.id, org.id)
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(
            403, detail="Not authorized to update organization settings"
        )

    # Update fields if provided
    if req.description is not None:
        Organization.update(description=req.description).where(
            Organization.id == org.id
        ).execute()

    return {"success": True, "message": "Organization settings updated successfully"}


# ============================================================================
# Repository Settings API
# ============================================================================


class UpdateRepoSettingsPayload(BaseModel):
    """Payload for repository settings update."""

    private: Optional[bool] = None
    gated: Optional[str] = None  # "auto", "manual", or False/None


@router.put("/{repo_type}s/{namespace}/{name}/settings")
async def update_repo_settings(
    repo_type: str,
    namespace: str,
    name: str,
    payload: UpdateRepoSettingsPayload,
    user: User = Depends(get_current_user),
):
    """Update repository settings.

    Matches pattern: PUT /api/{repo_type}s/{namespace}/{name}/settings

    Args:
        repo_type: Repository type (model/dataset/space)
        namespace: Repository namespace
        name: Repository name
        payload: Settings to update
        user: Current authenticated user

    Returns:
        Success message
    """
    repo_id = f"{namespace}/{name}"

    # Check if repository exists
    repo_row = get_repository(repo_type, namespace, name)

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check if user has permission to update this repository
    check_repo_delete_permission(repo_row, user)

    # Update fields if provided
    if payload.private is not None:
        Repository.update(private=payload.private).where(
            Repository.id == repo_row.id
        ).execute()

    # Note: gated functionality not yet implemented in database schema
    # Would require adding a 'gated' field to Repository model

    return {"success": True, "message": "Repository settings updated successfully"}
