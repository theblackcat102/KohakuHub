"""Invitation management endpoints for admin API."""

import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from kohakuhub.config import cfg
from kohakuhub.db import Invitation, User
from kohakuhub.db_operations import (
    check_invitation_available,
    create_invitation,
    delete_invitation,
    get_invitation,
)
from kohakuhub.logger import get_logger
from kohakuhub.api.admin.utils import verify_admin_token

logger = get_logger("ADMIN")
router = APIRouter()


# ===== Models =====


class CreateRegisterInvitationRequest(BaseModel):
    """Request to create registration invitation."""

    org_id: int | None = None  # Optional organization to join
    role: str = "member"  # Role in organization (if org_id provided)
    max_usage: int | None = None  # None=one-time, -1=unlimited, N=max uses
    expires_days: int = 7  # Days until expiration


# ===== Endpoints =====


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
    # Validate role if org_id provided
    if request.org_id:
        if request.role not in ["visitor", "member", "admin"]:
            raise HTTPException(
                400, detail={"error": "Invalid role. Must be visitor, member, or admin"}
            )

        # Verify organization exists (using get_organization with ID)
        org = User.get_or_none((User.id == request.org_id) & (User.is_org == True))
        if not org:
            raise HTTPException(
                404, detail={"error": f"Organization not found: {request.org_id}"}
            )

        org_name = org.username
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

    # Create invitation (no created_by for admin-generated invitations)
    invitation = create_invitation(
        token=token,
        action="register_account",
        parameters=parameters,
        created_by=None,  # System/Admin generated (no specific user)
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
    query = Invitation.select()

    if action:
        query = query.where(Invitation.action == action)

    query = query.order_by(Invitation.created_at.desc()).limit(limit).offset(offset)

    invitations = []
    for inv in query:
        # Get creator username (using FK backref)
        creator_username = inv.created_by.username if inv.created_by else "System"

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
                "created_by_id": inv.created_by.id if inv.created_by else None,
                "creator_username": creator_username,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat(),
                "max_usage": inv.max_usage,
                "usage_count": inv.usage_count,
                "is_reusable": inv.max_usage is not None,
                "is_available": is_available,
                "error_message": error_msg,
                "used_at": inv.used_at.isoformat() if inv.used_at else None,
                "used_by_id": inv.used_by.id if inv.used_by else None,
                "used_by_username": inv.used_by.username if inv.used_by else None,
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

    logger.info(
        f"Admin deleted invitation: {token[:8]}... (action={invitation.action})"
    )

    return {"success": True, "message": "Invitation deleted successfully"}
