"""Utility functions for organization management."""

from fastapi import HTTPException

from kohakuhub.db import Organization, User, UserOrganization

# Error messages
_ERR_USER_NOT_FOUND = "User not found"


def create_organization(name: str, description: str | None, user: User):
    """Create organization with default quotas (synchronous version).

    Note: This function is deprecated. Use async version from db_async instead.
    """
    from kohakuhub.config import cfg

    if Organization.get_or_none(Organization.name == name):
        raise HTTPException(400, detail="Organization name already exists")

    # Apply default quotas
    org = Organization.create(
        name=name,
        description=description,
        private_quota_bytes=cfg.quota.default_org_private_quota_bytes,
        public_quota_bytes=cfg.quota.default_org_public_quota_bytes,
    )
    UserOrganization.create(user=user.id, organization=org.id, role="super-admin")
    return org


def get_organization_details(name: str):
    return Organization.get_or_none(Organization.name == name)


def add_member_to_organization(org_id: int, username: str, role: str):
    user = User.get_or_none(User.username == username)
    if not user:
        raise HTTPException(404, detail=_ERR_USER_NOT_FOUND)

    if UserOrganization.get_or_none(
        (UserOrganization.user == user.id) & (UserOrganization.organization == org_id)
    ):
        raise HTTPException(400, detail="User is already a member of the organization")

    UserOrganization.create(user=user.id, organization=org_id, role=role)


def remove_member_from_organization(org_id: int, username: str):
    user = User.get_or_none(User.username == username)
    if not user:
        raise HTTPException(404, detail=_ERR_USER_NOT_FOUND)

    user_org = UserOrganization.get_or_none(
        (UserOrganization.user == user.id) & (UserOrganization.organization == org_id)
    )
    if not user_org:
        raise HTTPException(404, detail="User is not a member of the organization")

    user_org.delete_instance()


def get_user_organizations(user_id: int):
    """
    Return the user's organization memberships with joined Organization rows.
    Using FK + join allows attribute access like uo.organization.name.
    """
    query = (
        UserOrganization.select(UserOrganization, Organization)
        .join(Organization)  # FK-based join now works implicitly
        .where(UserOrganization.user == user_id)
    )
    return list(query)


def update_member_role(org_id: int, username: str, role: str):
    user = User.get_or_none(User.username == username)
    if not user:
        raise HTTPException(404, detail=_ERR_USER_NOT_FOUND)

    user_org = UserOrganization.get_or_none(
        (UserOrganization.user == user.id) & (UserOrganization.organization == org_id)
    )
    if not user_org:
        raise HTTPException(404, detail="User is not a member of the organization")

    user_org.role = role
    user_org.save()
