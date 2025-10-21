"""Organization management tests.

Tests organization creation, member management, and organization listing.
Uses actual Pydantic models from source code.
"""

import uuid

from kohakuhub.api.org.router import (
    AddMemberPayload,
    CreateOrganizationPayload,
    UpdateMemberRolePayload,
)
from kohakuhub.auth.routes import RegisterRequest
from tests.config import config


class TestOrganization:
    """Test organization operations."""

    def test_create_organization(self, authenticated_http_client):
        """Test organization creation."""
        unique_id = uuid.uuid4().hex[:6]
        org_name = f"org-{unique_id}"

        # Create organization using actual model
        payload = CreateOrganizationPayload(
            name=org_name, description="Test organization"
        )

        resp = authenticated_http_client.post("/org/create", json=payload.model_dump())
        assert resp.status_code == 200, f"Create org failed: {resp.text}"
        data = resp.json()
        assert data["success"] == True
        assert data["name"] == org_name

    def test_get_organization_info(self, authenticated_http_client, test_org):
        """Test getting organization information."""
        resp = authenticated_http_client.get(f"/org/{test_org}")
        assert resp.status_code == 200, f"Get org info failed: {resp.text}"
        data = resp.json()
        assert "name" in data
        assert data["name"] == test_org

    def test_list_user_organizations(self, authenticated_http_client):
        """Test listing user's organizations."""
        resp = authenticated_http_client.get(f"/org/users/{config.username}/orgs")
        assert resp.status_code == 200
        data = resp.json()
        assert "organizations" in data
        assert isinstance(data["organizations"], list)

    def test_add_remove_member(self, authenticated_http_client, test_org):
        """Test adding and removing organization members."""
        # Create a new user to add as member
        unique_id = uuid.uuid4().hex[:6]
        member_username = f"mem-{unique_id}"
        member_email = f"mem-{unique_id}@example.com"

        register_payload = RegisterRequest(
            username=member_username, email=member_email, password="testpass123"
        )

        resp = authenticated_http_client.post(
            "/api/auth/register", json=register_payload.model_dump()
        )
        assert resp.status_code == 200, f"Member registration failed: {resp.text}"

        # Add member to organization using actual model
        add_payload = AddMemberPayload(username=member_username, role="member")

        resp = authenticated_http_client.post(
            f"/org/{test_org}/members", json=add_payload.model_dump()
        )
        assert resp.status_code == 200, f"Add member failed: {resp.text}"

        # Verify member was added
        resp = authenticated_http_client.get(f"/org/{test_org}/members")
        assert resp.status_code == 200
        data = resp.json()
        assert "members" in data
        member_usernames = [m["user"] for m in data["members"]]
        assert member_username in member_usernames

        # Remove member
        resp = authenticated_http_client.delete(
            f"/org/{test_org}/members/{member_username}"
        )
        assert resp.status_code == 200

        # Verify member was removed
        resp = authenticated_http_client.get(f"/org/{test_org}/members")
        assert resp.status_code == 200
        data = resp.json()
        member_usernames = [m["user"] for m in data["members"]]
        assert member_username not in member_usernames

    def test_update_member_role(self, authenticated_http_client, test_org):
        """Test updating organization member role."""
        # Create a new user
        unique_id = uuid.uuid4().hex[:6]
        member_username = f"mem-{unique_id}"
        member_email = f"mem-{unique_id}@example.com"

        register_payload = RegisterRequest(
            username=member_username, email=member_email, password="testpass123"
        )
        resp = authenticated_http_client.post(
            "/api/auth/register", json=register_payload.model_dump()
        )
        assert resp.status_code == 200

        # Add member as 'member' role
        add_payload = AddMemberPayload(username=member_username, role="member")
        resp = authenticated_http_client.post(
            f"/org/{test_org}/members", json=add_payload.model_dump()
        )
        assert resp.status_code == 200

        # Update member role to 'admin' using actual model
        update_payload = UpdateMemberRolePayload(role="admin")
        resp = authenticated_http_client.put(
            f"/org/{test_org}/members/{member_username}",
            json=update_payload.model_dump(),
        )
        assert resp.status_code == 200

        # Verify role was updated
        resp = authenticated_http_client.get(f"/org/{test_org}/members")
        assert resp.status_code == 200
        data = resp.json()
        member_data = next(
            (m for m in data["members"] if m["user"] == member_username), None
        )
        assert member_data is not None
        assert member_data["role"] == "admin"

        # Cleanup
        resp = authenticated_http_client.delete(
            f"/org/{test_org}/members/{member_username}"
        )

    def test_list_organization_members(self, authenticated_http_client, test_org):
        """Test listing organization members."""
        resp = authenticated_http_client.get(f"/org/{test_org}/members")
        assert resp.status_code == 200
        data = resp.json()
        assert "members" in data
        assert isinstance(data["members"], list)
        # Creator should be in the list as super-admin
        usernames = [m["user"] for m in data["members"]]
        assert config.username in usernames

    def test_duplicate_organization(self, authenticated_http_client, test_org):
        """Test that creating duplicate organization fails."""
        # Try to create organization with same name
        payload = CreateOrganizationPayload(name=test_org, description="Duplicate org")

        resp = authenticated_http_client.post("/org/create", json=payload.model_dump())
        assert resp.status_code == 400
        assert "exist" in resp.text.lower() or "already" in resp.text.lower()

    def test_nonexistent_organization(self, authenticated_http_client):
        """Test accessing non-existent organization."""
        unique_id = uuid.uuid4().hex[:6]
        fake_org = f"noorg-{unique_id}"

        resp = authenticated_http_client.get(f"/org/{fake_org}")
        assert resp.status_code == 404
