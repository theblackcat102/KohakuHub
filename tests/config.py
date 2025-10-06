"""Test configuration for KohakuHub API tests.

Configuration can be set via environment variables:
- TEST_ENDPOINT: API endpoint URL (default: http://localhost:28080)
- TEST_USERNAME: Test user username (default: testuser)
- TEST_EMAIL: Test user email (default: test@example.com)
- TEST_PASSWORD: Test user password (default: testpass123)
- TEST_ORG_NAME: Test organization name (default: testorg)
"""

import os
from dataclasses import dataclass


@dataclass
class TestConfig:
    """Test configuration."""

    # API endpoint (should be the nginx port, not backend port)
    endpoint: str = os.getenv("TEST_ENDPOINT", "http://localhost:28080")

    # Test user credentials (for session-scoped shared user)
    username: str = os.getenv("TEST_USERNAME", "testuser")
    email: str = os.getenv("TEST_EMAIL", "test@example.com")
    password: str = os.getenv("TEST_PASSWORD", "testpass123")

    # Test organization (lowercase, matches ^[a-z0-9][a-z0-9-]{2,62}$)
    org_name: str = os.getenv("TEST_ORG_NAME", "testorg")

    # Test repository prefix (to avoid conflicts, lowercase)
    repo_prefix: str = os.getenv("TEST_REPO_PREFIX", "tst")

    # Timeout for HTTP requests
    timeout: int = int(os.getenv("TEST_TIMEOUT", "30"))

    # Cleanup after tests
    cleanup_on_success: bool = os.getenv("TEST_CLEANUP", "true").lower() == "true"

    def __post_init__(self):
        """Validate configuration."""
        if not self.endpoint:
            raise ValueError("TEST_ENDPOINT must be set")
        if not self.username or not self.password:
            raise ValueError("TEST_USERNAME and TEST_PASSWORD must be set")


# Global config instance
config = TestConfig()
