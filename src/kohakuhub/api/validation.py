"""Name validation and conflict checking endpoints."""

import re

from fastapi import APIRouter
from pydantic import BaseModel

from kohakuhub.db import Organization, Repository, User

router = APIRouter()


def normalize_name(name: str) -> str:
    """Normalize name for conflict checking.

    Names that normalize to the same value are considered conflicts.
    This prevents confusing names like 'My-Repo' and 'my_repo'.

    Args:
        name: Original name

    Returns:
        Normalized name (lowercase, hyphens/underscores removed)
    """
    # Convert to lowercase
    normalized = name.lower()
    # Remove hyphens and underscores
    normalized = normalized.replace("-", "").replace("_", "")
    return normalized


class CheckNameRequest(BaseModel):
    """Request to check if name is available."""

    name: str
    namespace: str | None = None  # For repository names
    type: str | None = None  # For repository type (model/dataset/space)


class CheckNameResponse(BaseModel):
    """Response for name availability check."""

    available: bool
    normalized_name: str
    conflict_with: str | None = None  # What the name conflicts with
    message: str


@router.post("/api/validate/check-name")
async def check_name_availability(req: CheckNameRequest) -> CheckNameResponse:
    """Check if a username, organization name, or repository name is available.

    This endpoint checks for:
    - Exact matches
    - Normalized conflicts (e.g., 'My-Repo' conflicts with 'my_repo')

    Args:
        req: Name check request

    Returns:
        Availability information
    """
    name = req.name.strip()
    normalized = normalize_name(name)

    # Check repository name
    if req.namespace and req.type:
        # Check if repository exists with this name
        existing = Repository.get_or_none(
            (Repository.repo_type == req.type)
            & (Repository.namespace == req.namespace)
            & (Repository.name == name)
        )

        if existing:
            return CheckNameResponse(
                available=False,
                normalized_name=normalized,
                conflict_with=f"{req.namespace}/{name}",
                message=f"Repository {req.namespace}/{name} already exists",
            )

        # Check for normalized conflicts
        all_repos = Repository.select().where(
            (Repository.repo_type == req.type) & (Repository.namespace == req.namespace)
        )

        for repo in all_repos:
            if normalize_name(repo.name) == normalized:
                return CheckNameResponse(
                    available=False,
                    normalized_name=normalized,
                    conflict_with=f"{req.namespace}/{repo.name}",
                    message=f"Repository name conflicts with existing repository: {repo.name}",
                )

        return CheckNameResponse(
            available=True,
            normalized_name=normalized,
            message="Repository name is available",
        )

    # Check username
    existing_user = User.get_or_none(User.username == name)
    if existing_user:
        return CheckNameResponse(
            available=False,
            normalized_name=normalized,
            conflict_with=name,
            message=f"Username {name} is already taken",
        )

    # Check for normalized username conflicts
    all_users = User.select()
    for user in all_users:
        if normalize_name(user.username) == normalized:
            return CheckNameResponse(
                available=False,
                normalized_name=normalized,
                conflict_with=user.username,
                message=f"Username conflicts with existing user: {user.username}",
            )

    # Check organization name
    existing_org = Organization.get_or_none(Organization.name == name)
    if existing_org:
        return CheckNameResponse(
            available=False,
            normalized_name=normalized,
            conflict_with=name,
            message=f"Organization name {name} is already taken",
        )

    # Check for normalized organization conflicts
    all_orgs = Organization.select()
    for org in all_orgs:
        if normalize_name(org.name) == normalized:
            return CheckNameResponse(
                available=False,
                normalized_name=normalized,
                conflict_with=org.name,
                message=f"Name conflicts with existing organization: {org.name}",
            )

    return CheckNameResponse(
        available=True, normalized_name=normalized, message="Name is available"
    )
