"""Utility API endpoints for Kohaku Hub."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import yaml

router = APIRouter()


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
def whoami_v2():
    """Get current user information.

    TODO: Implement real user info retrieval from authentication system.

    Returns:
        User information object
    """
    # Mock response matching HuggingFace Hub format
    return {
        "name": "me",
        "type": "user",
        "displayName": "me",
        "email": None,
        "orgs": [],
        "isPro": False,
        "periodEnd": None,
    }
