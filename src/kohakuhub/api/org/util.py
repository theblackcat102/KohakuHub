"""Utility functions for organization management.

DEPRECATED: This module is deprecated. Use db_operations.py instead.
Organizations are now User objects with is_org=True.
"""

from fastapi import HTTPException

from kohakuhub.db_operations import (
    create_organization as create_org_op,
    create_user_organization as create_user_org_op,
    get_organization,
)

# Error messages
_ERR_USER_NOT_FOUND = "User not found"


def create_organization(name: str, description: str | None, user):
    """Create organization with default quotas.

    DEPRECATED: Use db_operations.create_organization instead.

    Args:
        name: Organization name
        description: Organization description
        user: User object (FK) who creates the organization
    """
    from kohakuhub.db import db

    with db.atomic():
        existing_org = get_organization(name)
        if existing_org:
            raise HTTPException(400, detail="Organization name already exists")

        org = create_org_op(name, description)
        create_user_org_op(user, org, "super-admin")
    return org


def get_organization_details(name: str):
    """Get organization by name.

    DEPRECATED: Use db_operations.get_organization instead.

    Returns:
        User object with is_org=True or None
    """
    return get_organization(name)


def add_member_to_organization(org_id: int, username: str, role: str):
    """Add member to organization (by integer ID).

    DEPRECATED: Use db_operations functions with User objects instead.
    This function exists for backward compatibility but uses the new schema.
    """
    from kohakuhub.db_operations import (
        get_user_by_id,
        get_user_by_username,
        get_user_organization,
    )

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, detail=_ERR_USER_NOT_FOUND)

    org = get_user_by_id(org_id)
    if not org or not org.is_org:
        raise HTTPException(404, detail="Organization not found")

    if get_user_organization(user, org):
        raise HTTPException(400, detail="User is already a member of the organization")

    create_user_org_op(user, org, role)


def remove_member_from_organization(org_id: int, username: str):
    """Remove member from organization (by integer ID).

    DEPRECATED: Use db_operations functions with User objects instead.
    """
    from kohakuhub.db_operations import (
        delete_user_organization,
        get_user_by_id,
        get_user_by_username,
        get_user_organization,
    )

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, detail=_ERR_USER_NOT_FOUND)

    org = get_user_by_id(org_id)
    if not org or not org.is_org:
        raise HTTPException(404, detail="Organization not found")

    user_org = get_user_organization(user, org)
    if not user_org:
        raise HTTPException(404, detail="User is not a member of the organization")

    delete_user_organization(user_org)


def get_user_organizations(user_id: int):
    """Get user's organization memberships (by integer ID).

    DEPRECATED: Use db_operations.list_user_organizations with User object instead.
    This function exists for backward compatibility.
    """
    from kohakuhub.db_operations import get_user_by_id, list_user_organizations

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, detail=_ERR_USER_NOT_FOUND)

    return list_user_organizations(user)


def update_member_role(org_id: int, username: str, role: str):
    """Update member role in organization (by integer ID).

    DEPRECATED: Use db_operations functions with User objects instead.
    """
    from kohakuhub.db_operations import (
        get_user_by_id,
        get_user_by_username,
        get_user_organization,
        update_user_organization,
    )

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, detail=_ERR_USER_NOT_FOUND)

    org = get_user_by_id(org_id)
    if not org or not org.is_org:
        raise HTTPException(404, detail="Organization not found")

    user_org = get_user_organization(user, org)
    if not user_org:
        raise HTTPException(404, detail="User is not a member of the organization")

    update_user_organization(user_org, role=role)
