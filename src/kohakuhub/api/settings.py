"""User, organization, and repository settings API endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from kohakuhub.db import User
from kohakuhub.db_operations import (
    get_organization,
    get_repository,
    get_user_by_email_excluding_id,
    get_user_by_username,
    get_user_organization,
    list_organization_members,
    update_organization,
    update_repository,
    update_user,
)
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_current_user
from kohakuhub.auth.permissions import check_repo_delete_permission
from kohakuhub.api.quota.util import calculate_repository_storage, check_quota
from kohakuhub.api.repo.utils.hf import hf_repo_not_found

logger = get_logger("SETTINGS")

router = APIRouter()


# ============================================================================
# User Settings API
# ============================================================================
# Note: /whoami-v2 is implemented in api/routers/misc.py


class UpdateUserSettingsRequest(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    social_media: Optional[dict] = None  # {twitter_x, threads, github, huggingface}


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
    update_fields = {}

    if req.email is not None:
        # Check if email is already taken by another user
        existing = get_user_by_email_excluding_id(req.email, user.id)
        if existing:
            raise HTTPException(400, detail="Email already in use")
        update_fields["email"] = req.email
        update_fields["email_verified"] = False
        # TODO: Send new verification email

    if req.full_name is not None:
        update_fields["full_name"] = req.full_name

    if req.bio is not None:
        update_fields["bio"] = req.bio

    if req.website is not None:
        update_fields["website"] = req.website

    if req.social_media is not None:
        # Validate social_media structure
        if not isinstance(req.social_media, dict):
            raise HTTPException(400, detail="social_media must be a dictionary")

        # Store as JSON string
        update_fields["social_media"] = json.dumps(req.social_media)

    # Execute update if there are fields to update
    if update_fields:
        update_user(user, **update_fields)

    return {"success": True, "message": "User settings updated successfully"}


@router.get("/users/{username}/profile")
async def get_user_profile(username: str):
    """Get user public profile information.

    Args:
        username: Username to query

    Returns:
        Public profile data
    """
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, detail="User not found")

    # Parse social_media JSON if exists
    social_media = None
    if user.social_media:
        try:
            social_media = json.loads(user.social_media)
        except json.JSONDecodeError:
            social_media = None

    return {
        "username": user.username,
        "full_name": user.full_name,
        "bio": user.bio,
        "website": user.website,
        "social_media": social_media,
        "created_at": user.created_at.isoformat(),
    }


# ============================================================================
# Organization Settings API
# ============================================================================


class UpdateOrganizationSettingsRequest(BaseModel):
    description: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    social_media: Optional[dict] = None  # {twitter_x, threads, github, huggingface}


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
    user_org = get_user_organization(user, org)
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(
            403, detail="Not authorized to update organization settings"
        )

    # Update fields if provided
    update_fields = {}

    if req.description is not None:
        update_fields["description"] = req.description

    if req.bio is not None:
        update_fields["bio"] = req.bio

    if req.website is not None:
        update_fields["website"] = req.website

    if req.social_media is not None:
        # Validate social_media structure
        if not isinstance(req.social_media, dict):
            raise HTTPException(400, detail="social_media must be a dictionary")

        # Store as JSON string
        update_fields["social_media"] = json.dumps(req.social_media)

    # Execute update if there are fields to update
    if update_fields:
        update_organization(org, **update_fields)

    return {"success": True, "message": "Organization settings updated successfully"}


@router.get("/organizations/{org_name}/profile")
async def get_organization_profile(org_name: str):
    """Get organization public profile information.

    Args:
        org_name: Organization name

    Returns:
        Public profile data
    """
    org = get_organization(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    # Parse social_media JSON if exists
    social_media = None
    if org.social_media:
        try:
            social_media = json.loads(org.social_media)
        except json.JSONDecodeError:
            social_media = None

    # Count members
    members = list_organization_members(org)
    member_count = len(members)

    return {
        "name": org.username,
        "description": org.description,
        "bio": org.bio,
        "website": org.website,
        "social_media": social_media,
        "member_count": member_count,
        "created_at": org.created_at.isoformat(),
    }


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
        # Check if visibility is actually changing
        if repo_row.private != payload.private:
            # Calculate repository storage
            logger.info(
                f"Checking quota for visibility change: {repo_id} from "
                f"{'private to public' if repo_row.private else 'public to private'}"
            )

            repo_storage = await calculate_repository_storage(repo_row)
            repo_size = repo_storage["total_bytes"]

            # Check if namespace is an organization
            org = get_organization(namespace)
            is_org = org is not None

            # Check quota for the new visibility setting
            # If changing to private, check private quota; if to public, check public quota
            allowed, error_msg = check_quota(
                namespace=namespace,
                additional_bytes=repo_size,
                is_private=payload.private,
                is_org=is_org,
            )

            if not allowed:
                logger.warning(
                    f"Quota check failed for {repo_id} visibility change: {error_msg}"
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": error_msg,
                        "repo_size_bytes": repo_size,
                    },
                )

        # Update repository visibility
        update_repository(repo_row, private=payload.private)

    # Note: gated functionality not yet implemented in database schema
    # Would require adding a 'gated' field to Repository model

    return {"success": True, "message": "Repository settings updated successfully"}
