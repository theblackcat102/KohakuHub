"""Organization related API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..db import User, UserOrganization
from ..auth.dependencies import get_current_user
from .utils import (
    create_organization as create_org_util,
    get_organization_details as get_org_details_util,
    add_member_to_organization as add_member_util,
    remove_member_from_organization,
    get_user_organizations,
    update_member_role as update_member_role_util,
)

router = APIRouter()


class CreateOrganizationPayload(BaseModel):
    name: str
    description: str | None = None


@router.post("/create")
def create_organization(
    payload: CreateOrganizationPayload, user: User = Depends(get_current_user)
):
    """Create a new organization."""
    org = create_org_util(payload.name, payload.description, user)
    return {"success": True, "name": org.name}


@router.get("/{org_name}")
def get_organization(org_name: str):
    """Get organization details."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")
    return {
        "name": org.name,
        "description": org.description,
        "created_at": org.created_at,
    }


class AddMemberPayload(BaseModel):
    username: str
    role: str


@router.post("/{org_name}/members")
def add_member(
    org_name: str,
    payload: AddMemberPayload,
    current_user: User = Depends(get_current_user),
):
    """Add a member to an organization."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    # Check if the current user is an admin of the organization
    user_org = UserOrganization.get_or_none(
        (UserOrganization.user == current_user.id)
        & (UserOrganization.organization == org.id)
    )
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to add members")

    add_member_util(org.id, payload.username, payload.role)
    return {"success": True, "message": "Member added successfully"}


@router.delete("/{org_name}/members/{username}")
def remove_member(
    org_name: str,
    username: str,
    current_user: User = Depends(get_current_user),
):
    """Remove a member from an organization."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    # Check if the current user is an admin of the organization
    user_org = UserOrganization.get_or_none(
        (UserOrganization.user == current_user.id)
        & (UserOrganization.organization == org.id)
    )
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to remove members")

    remove_member_from_organization(org.id, username)
    return {"success": True, "message": "Member removed successfully"}


@router.get("/users/{username}/orgs")
def list_user_organizations(username: str):
    """List organizations a user belongs to."""
    user = User.get_or_none(User.username == username)
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
def update_member_role(
    org_name: str,
    username: str,
    payload: UpdateMemberRolePayload,
    current_user: User = Depends(get_current_user),
):
    """Update a member's role in an organization."""
    org = get_org_details_util(org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    # Check if the current user is an admin of the organization
    user_org = UserOrganization.get_or_none(
        (UserOrganization.user == current_user.id)
        & (UserOrganization.organization == org.id)
    )
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(403, detail="Not authorized to update member roles")

    update_member_role_util(org.id, username, payload.role)
    return {"success": True, "message": "Member role updated successfully"}
