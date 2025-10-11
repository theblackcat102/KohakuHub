"""Organization related API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from kohakuhub.db import Organization, User, UserOrganization
from kohakuhub.db_operations import (
    create_organization as create_org_async,
    create_user_organization,
    get_organization,
    get_user_by_username,
    get_user_organization,
    list_organization_members as list_org_members_async,
)
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_current_user
from kohakuhub.api.org.util import (
    add_member_to_organization as add_member_util,
    get_organization_details as get_org_details_util,
    get_user_organizations,
    remove_member_from_organization,
    update_member_role as update_member_role_util,
)

# Error messages
_ERR_ORG_NOT_FOUND = "Organization not found"

logger = get_logger("ORG")

router = APIRouter()


class CreateOrganizationPayload(BaseModel):
    name: str
    description: str | None = None


@router.post("/create")
async def create_organization(
    payload: CreateOrganizationPayload, user: User = Depends(get_current_user)
):
    """Create a new organization with default quotas."""

    # Check if organization already exists
    existing_org = Organization.get_or_none(Organization.name == payload.name)
    if existing_org:
        raise HTTPException(400, detail="Organization name already exists")

    # Create organization with default quotas
    org = create_org_async(payload.name, payload.description)

    # Add creator as super-admin
    create_user_organization(user.id, org.id, "super-admin")

    logger.info(f"User {user.username} created organization: {org.name}")

    return {"success": True, "name": org.name}


@router.get("/{org_name}")
async def get_organization_info(org_name: str):
    """Get organization details."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail=_ERR_ORG_NOT_FOUND)
    return {
        "name": org.name,
        "description": org.description,
        "created_at": org.created_at,
    }


class AddMemberPayload(BaseModel):
    username: str
    role: str


@router.post("/{org_name}/members")
async def add_member(
    org_name: str,
    payload: AddMemberPayload,
    current_user: User = Depends(get_current_user),
):
    """Add a member to an organization."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail=_ERR_ORG_NOT_FOUND)

    # Check if the current user is an admin of the organization
    user_org = get_user_organization(current_user.id, org.id)
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to add members")

    add_member_util(org.id, payload.username, payload.role)
    return {"success": True, "message": "Member added successfully"}


@router.delete("/{org_name}/members/{username}")
async def remove_member(
    org_name: str,
    username: str,
    current_user: User = Depends(get_current_user),
):
    """Remove a member from an organization."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail=_ERR_ORG_NOT_FOUND)

    # Check if the current user is an admin of the organization
    user_org = get_user_organization(current_user.id, org.id)
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to remove members")

    remove_member_from_organization(org.id, username)
    return {"success": True, "message": "Member removed successfully"}


@router.get("/users/{username}/orgs")
async def list_user_organizations(username: str):
    """List organizations a user belongs to."""
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, detail="User not found")

    orgs = get_user_organizations(user.id)
    return {
        "organizations": [
            {
                "name": org.organization.name,
                "description": org.organization.description,
                "role": org.role,
            }
            for org in orgs
        ]
    }


class UpdateMemberRolePayload(BaseModel):
    role: str


@router.put("/{org_name}/members/{username}")
async def update_member_role(
    org_name: str,
    username: str,
    payload: UpdateMemberRolePayload,
    current_user: User = Depends(get_current_user),
):
    """Update a member's role in an organization."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail=_ERR_ORG_NOT_FOUND)

    # Check if the current user is an admin of the organization
    user_org = get_user_organization(current_user.id, org.id)
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to update member roles")

    update_member_role_util(org.id, username, payload.role)
    return {"success": True, "message": "Member role updated successfully"}


@router.get("/{org_name}/members")
async def list_organization_members(org_name: str):
    """List organization members."""
    org = get_organization(org_name)
    if not org:
        raise HTTPException(404, detail=_ERR_ORG_NOT_FOUND)

    # Get all members
    members = list_org_members_async(org.id)

    return {
        "members": [
            {
                "user": m.user.username,
                "role": m.role,
            }
            for m in members
        ]
    }
