"""Authentication API tests.

Tests user registration, login, logout, token management, and whoami endpoints.
Uses actual Pydantic models from the source code.
"""

import uuid

import pytest

from tests.base import HTTPClient
from tests.config import config


class TestAuthentication:
    """Test authentication endpoints."""

    def test_version_check(self, http_client):
        """Test API version endpoint."""
        resp = http_client.get("/api/version")
        assert resp.status_code == 200
        data = resp.json()
        assert "api" in data
        assert data["api"] == "kohakuhub"
        assert "version" in data

    def test_register_login_logout_flow(self, http_client):
        """Test complete user registration, login, and logout flow."""
        # Import actual Pydantic models
        from kohakuhub.auth.routes import RegisterRequest, LoginRequest

        # Use unique username for this test
        unique_id = uuid.uuid4().hex[:6]
        test_username = f"user-{unique_id}"  # Matches ^[a-z0-9][a-z0-9-]{2,62}$
        test_email = f"test-{unique_id}@example.com"
        test_password = "testpass123"

        # 1. Register new user using actual model
        payload = RegisterRequest(
            username=test_username, email=test_email, password=test_password
        )

        resp = http_client.post("/api/auth/register", json=payload.model_dump())
        assert resp.status_code == 200, f"Registration failed: {resp.text}"
        data = resp.json()
        assert data["success"] == True

        # 2. Login using actual model
        login_payload = LoginRequest(username=test_username, password=test_password)

        resp = http_client.post("/api/auth/login", json=login_payload.model_dump())
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "username" in data
        assert data["username"] == test_username

        # Save session
        session_cookies = resp.cookies

        # 3. Get current user (with session)
        client_with_session = HTTPClient()
        client_with_session.session.cookies.update(session_cookies)

        resp = client_with_session.get("/api/auth/me")
        assert resp.status_code == 200, f"Get user failed: {resp.text}"
        data = resp.json()
        assert data["username"] == test_username

        # 4. Logout
        resp = client_with_session.post("/api/auth/logout")
        assert resp.status_code == 200

        # 5. Verify session is cleared
        resp = client_with_session.get("/api/auth/me")
        assert resp.status_code == 401, "Session should be cleared after logout"

    def test_token_creation_and_usage(self, authenticated_http_client):
        """Test API token creation and usage."""
        from kohakuhub.auth.routes import CreateTokenRequest

        # 1. Create token using actual model
        unique_id = uuid.uuid4().hex[:6]
        token_payload = CreateTokenRequest(name=f"token-{unique_id}")

        resp = authenticated_http_client.post(
            "/api/auth/tokens/create", json=token_payload.model_dump()
        )
        assert resp.status_code == 200, f"Token creation failed: {resp.text}"
        data = resp.json()
        assert "token" in data
        assert "token_id" in data
        token = data["token"]
        token_id = data["token_id"]

        # 2. Use token for authentication
        client_with_token = HTTPClient(token=token)
        resp = client_with_token.get("/api/auth/me")
        assert resp.status_code == 200, f"Token auth failed: {resp.text}"
        user_data = resp.json()
        assert user_data["username"] == config.username

        # 3. List tokens
        resp = authenticated_http_client.get("/api/auth/tokens")
        assert resp.status_code == 200
        tokens_response = resp.json()
        assert "tokens" in tokens_response
        tokens = tokens_response["tokens"]
        assert isinstance(tokens, list)
        # Our token should be in the list
        token_names = [t["name"] for t in tokens]
        assert token_payload.name in token_names

        # 4. Revoke token
        resp = authenticated_http_client.delete(f"/api/auth/tokens/{token_id}")
        assert resp.status_code == 200

        # 5. Verify token is revoked
        resp = client_with_token.get("/api/auth/me")
        assert resp.status_code == 401, "Token should be revoked"

    def test_whoami_endpoint(self, authenticated_http_client):
        """Test whoami-v2 endpoint for detailed user info."""
        resp = authenticated_http_client.get("/api/whoami-v2")
        assert resp.status_code == 200, f"whoami-v2 failed: {resp.text}"
        data = resp.json()

        # Validate response structure (based on actual implementation in misc.py)
        assert "type" in data
        assert data["type"] == "user"
        assert "name" in data
        assert data["name"] == config.username
        assert "email" in data
        assert "orgs" in data
        assert isinstance(data["orgs"], list)
        assert "emailVerified" in data
        assert "auth" in data

    def test_invalid_credentials(self, http_client):
        """Test login with invalid credentials."""
        from kohakuhub.auth.routes import LoginRequest

        payload = LoginRequest(username="nonexistent", password="wrongpass")

        resp = http_client.post("/api/auth/login", json=payload.model_dump())
        assert resp.status_code == 401, "Should reject invalid credentials"

    def test_unauthenticated_access(self, http_client):
        """Test accessing protected endpoints without authentication."""
        # Try to access protected endpoint
        resp = http_client.get("/api/auth/me")
        assert resp.status_code == 401, "Should require authentication"

        # Try to create repo without auth
        from kohakuhub.api.repo.routers.crud import CreateRepoPayload

        payload = CreateRepoPayload(type="model", name="test-repo")

        resp = http_client.post("/api/repos/create", json=payload.model_dump())
        assert resp.status_code in [401, 403], "Should require authentication"

    def test_duplicate_registration(self, http_client):
        """Test that duplicate usernames are rejected."""
        from kohakuhub.auth.routes import RegisterRequest

        unique_id = uuid.uuid4().hex[:6]
        test_username = f"dup-{unique_id}"
        test_email = f"dup-{unique_id}@example.com"

        payload = RegisterRequest(
            username=test_username, email=test_email, password="testpass123"
        )

        # First registration
        resp = http_client.post("/api/auth/register", json=payload.model_dump())
        assert resp.status_code == 200

        # Second registration with same username (different email)
        payload2 = RegisterRequest(
            username=test_username,
            email=f"different_{unique_id}@example.com",
            password="testpass123",
        )

        resp = http_client.post("/api/auth/register", json=payload2.model_dump())
        assert resp.status_code == 400
        assert "username" in resp.text.lower() or "exist" in resp.text.lower()

    def test_duplicate_email_registration(self, http_client):
        """Test that duplicate emails are rejected."""
        from kohakuhub.auth.routes import RegisterRequest

        unique_id = uuid.uuid4().hex[:6]
        test_username = f"email-{unique_id}"
        test_email = f"email-{unique_id}@example.com"

        payload = RegisterRequest(
            username=test_username, email=test_email, password="testpass123"
        )

        # First registration
        resp = http_client.post("/api/auth/register", json=payload.model_dump())
        assert resp.status_code == 200

        # Second registration with same email (different username)
        payload2 = RegisterRequest(
            username=f"different_{unique_id}",
            email=test_email,
            password="testpass123",
        )

        resp = http_client.post("/api/auth/register", json=payload2.model_dump())
        assert resp.status_code == 400
        assert "email" in resp.text.lower() or "exist" in resp.text.lower()
