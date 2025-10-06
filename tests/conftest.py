"""Pytest configuration and fixtures for KohakuHub API tests."""

import os
import pytest
import requests
from huggingface_hub import HfApi

from tests.base import HFClientWrapper, HTTPClient
from tests.config import config


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return config


@pytest.fixture(scope="function")
def http_client():
    """HTTP client fixture for direct API testing (unauthenticated).

    Function-scoped to prevent session contamination between tests.
    """
    return HTTPClient()


@pytest.fixture(scope="session")
def api_token():
    """Create and return API token for the test user.

    This fixture:
    1. Registers a test user (if not exists)
    2. Logs in to get session
    3. Creates an API token
    4. Returns the token for use in tests
    """
    from kohakuhub.auth.routes import RegisterRequest, LoginRequest, CreateTokenRequest

    # Create a dedicated HTTP client for this session setup
    setup_client = HTTPClient()

    # Try to register (will fail if user exists, which is fine)
    try:
        payload = RegisterRequest(
            username=config.username, email=config.email, password=config.password
        )
        resp = setup_client.post("/api/auth/register", json=payload.model_dump())
        if resp.status_code == 200:
            print(f"✓ Registered test user: {config.username}")
    except Exception as e:
        print(f"User registration skipped (may already exist): {e}")

    # Login to get session
    login_payload = LoginRequest(username=config.username, password=config.password)
    resp = setup_client.post("/api/auth/login", json=login_payload.model_dump())
    assert resp.status_code == 200, f"Login failed: {resp.text}"

    # Update session cookies
    setup_client.session.cookies.update(resp.cookies)

    # Create API token
    import uuid

    token_id = uuid.uuid4().hex[:6]
    token_payload = CreateTokenRequest(name=f"tok-{token_id}")
    resp = setup_client.post("/api/auth/tokens/create", json=token_payload.model_dump())
    assert resp.status_code == 200, f"Token creation failed: {resp.text}"

    token_data = resp.json()
    token = token_data["token"]
    print(f"✓ Created API token for testing")

    yield token

    # Cleanup: revoke token (optional)
    if config.cleanup_on_success:
        try:
            token_id = token_data.get("token_id")
            if token_id:
                setup_client.delete(f"/api/auth/tokens/{token_id}")
                print(f"✓ Revoked test token")
        except Exception as e:
            print(f"Token cleanup failed: {e}")


@pytest.fixture(scope="session")
def authenticated_http_client(api_token):
    """HTTP client with authentication."""
    return HTTPClient(token=api_token)


@pytest.fixture(scope="session")
def hf_client(api_token):
    """HuggingFace Hub client fixture."""
    return HFClientWrapper(token=api_token)


@pytest.fixture(scope="function")
def random_user():
    """Create a random user for testing.

    Returns:
        Tuple of (username, token, hf_client_wrapper)

    Each test gets a fresh user to avoid conflicts.
    """
    import uuid
    from kohakuhub.auth.routes import RegisterRequest, LoginRequest, CreateTokenRequest

    # Generate short random ID (6 chars, lowercase hex)
    unique_id = uuid.uuid4().hex[:6]
    username = f"user-{unique_id}"  # Matches ^[a-z0-9][a-z0-9-]{2,62}$
    email = f"test-{unique_id}@example.com"
    password = "testpass123"

    # Create HTTP client for setup
    setup_client = HTTPClient()

    # Register user
    payload = RegisterRequest(username=username, email=email, password=password)
    resp = setup_client.post("/api/auth/register", json=payload.model_dump())
    assert resp.status_code == 200, f"Registration failed: {resp.text}"

    # Login
    login_payload = LoginRequest(username=username, password=password)
    resp = setup_client.post("/api/auth/login", json=login_payload.model_dump())
    assert resp.status_code == 200, f"Login failed: {resp.text}"

    # Update session cookies
    setup_client.session.cookies.update(resp.cookies)

    # Create API token
    token_payload = CreateTokenRequest(name=f"tok-{unique_id}")
    resp = setup_client.post("/api/auth/tokens/create", json=token_payload.model_dump())
    assert resp.status_code == 200, f"Token creation failed: {resp.text}"

    token = resp.json()["token"]

    # Create HF client for this user
    user_hf_client = HFClientWrapper(token=token)

    yield username, token, user_hf_client

    # Cleanup happens automatically when user is deleted (if needed)


@pytest.fixture(scope="function")
def temp_repo(random_user, request):
    """Create temporary repository for testing.

    Usage:
        def test_something(temp_repo):
            repo_id, repo_type, hf_client = temp_repo
            # repo will be cleaned up after test
    """
    username, token, hf_client = random_user

    # Get repo type from test marker or default to "model"
    marker = request.node.get_closest_marker("repo_type")
    repo_type = marker.args[0] if marker else "model"

    # Generate unique repo name (short, lowercase)
    import uuid

    unique_id = uuid.uuid4().hex[:6]
    repo_name = f"repo-{unique_id}"  # Matches ^[a-z0-9][a-z0-9-]{2,62}$
    repo_id = f"{username}/{repo_name}"

    # Create repository
    try:
        hf_client.create_repo(repo_id=repo_id, repo_type=repo_type, private=False)
        print(f"✓ Created test repo: {repo_id}")
    except Exception as e:
        pytest.fail(f"Failed to create test repo: {e}")

    yield repo_id, repo_type, hf_client

    # Cleanup
    if config.cleanup_on_success:
        try:
            hf_client.delete_repo(repo_id=repo_id, repo_type=repo_type)
            print(f"✓ Cleaned up test repo: {repo_id}")
        except Exception as e:
            print(f"Repo cleanup failed: {e}")


@pytest.fixture(scope="session")
def test_org(authenticated_http_client):
    """Create test organization.

    This fixture creates an organization for testing org-related features.
    """
    from kohakuhub.org.routes import CreateOrganizationPayload

    client = authenticated_http_client

    # Try to create organization using actual model
    try:
        payload = CreateOrganizationPayload(
            name=config.org_name, description="Organization for testing"
        )
        resp = client.post("/org/create", json=payload.model_dump())
        if resp.status_code == 200:
            print(f"✓ Created test organization: {config.org_name}")
        elif resp.status_code == 400 and "exists" in resp.text.lower():
            print(f"✓ Test organization already exists: {config.org_name}")
        else:
            print(f"Warning: Org creation returned {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Org creation skipped: {e}")

    yield config.org_name

    # Cleanup: delete organization (if API supports it)
    # Note: Current API may not support org deletion
    if config.cleanup_on_success:
        try:
            # Organization deletion endpoint may not exist yet
            # resp = client.delete(f"/org/{config.org_name}")
            # print(f"✓ Deleted test organization")
            pass
        except Exception as e:
            print(f"Org cleanup skipped: {e}")


def pytest_configure(config):
    """Pytest configuration hook."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "repo_type(type): mark test to use specific repo type"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "lfs: mark test as requiring LFS")

    # Print test configuration
    print("\n" + "=" * 70)
    print("KohakuHub API Test Configuration")
    print("=" * 70)
    print(f"Endpoint: {test_config.endpoint}")
    print(f"Username: {test_config.username}")
    print(f"Org Name: {test_config.org_name}")
    print(f"Cleanup: {test_config.cleanup_on_success}")
    print("=" * 70 + "\n")


# Get test_config for pytest_configure
test_config = config
