"""Utility API endpoints for Kohaku Hub."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import yaml

from kohakuhub.config import cfg
from kohakuhub.db import Organization, User, UserOrganization
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_optional_user

logger = get_logger("UTILS")

router = APIRouter()


@router.get("/version")
def get_version():
    """Get KohakuHub version and site information.

    This endpoint helps client libraries (like hfutils) detect if they're
    connecting to KohakuHub vs HuggingFace Hub.

    HuggingFace Hub returns 404 for this endpoint.
    KohakuHub returns site identification and version info.

    Returns:
        Site identification and version information
    """
    return {
        "api": "kohakuhub",
        "version": "0.0.1",
        "name": cfg.app.site_name,
    }


class ValidateYamlPayload(BaseModel):
    """Payload for YAML validation endpoint."""

    content: str
    repo_type: str = "model"


@router.post("/validate-yaml")
def validate_yaml(body: ValidateYamlPayload):
    """Validate YAML content (e.g., model card, dataset card).

    Args:
        body: Validation payload with YAML content

    Returns:
        Validation result
    """
    try:
        yaml.safe_load(body.content)
    except Exception as e:
        return {"valid": False}

    return {"valid": True}


@router.get("/whoami-v2")
def whoami_v2(user: User | None = Depends(get_optional_user)):
    """Get current user information (HuggingFace compatible).

    Matches HuggingFace Hub /api/whoami-v2 endpoint format.
    Returns user info if authenticated, 401 if not.
    """
    if not user:
        raise HTTPException(401, detail="Invalid user token")

    # Get user's organizations
    user_orgs = (
        UserOrganization.select()
        .join(Organization)
        .where(UserOrganization.user == user.id)
    )

    orgs_list = []
    for uo in user_orgs:
        orgs_list.append(
            {
                "name": uo.organization.name,
                "fullname": uo.organization.name,
                "roleInOrg": uo.role,
            }
        )

    return {
        "type": "user",
        "id": str(user.id),
        "name": user.username,
        "fullname": user.username,
        "email": user.email,
        "emailVerified": user.email_verified,
        "canPay": False,
        "isPro": False,
        "orgs": orgs_list,
        "auth": {
            "type": "access_token",
            "accessToken": {"displayName": "Auto-generated token", "role": "write"},
        },
        # KohakuHub-specific fields
        "site": {
            "name": cfg.app.site_name,  # Configurable site name
            "api": "kohakuhub",  # Hardcoded API identifier
            "version": "0.0.1",  # Hardcoded version
        },
    }
