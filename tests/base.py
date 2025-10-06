"""Base test classes and utilities for KohakuHub API tests."""

import os
import tempfile
from pathlib import Path
from typing import Any

import requests
from huggingface_hub import HfApi

from tests.config import config


class HTTPClient:
    """Custom HTTP client for direct API testing.

    This client is used to test API endpoints directly without the HuggingFace
    client abstraction, ensuring our API matches the intended schema.
    """

    def __init__(self, endpoint: str = None, token: str = None):
        """Initialize HTTP client.

        Args:
            endpoint: API endpoint URL
            token: API token for authentication
        """
        self.endpoint = endpoint or config.endpoint
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def request(
        self,
        method: str,
        path: str,
        json: dict = None,
        data: Any = None,
        headers: dict = None,
        params: dict = None,
        **kwargs,
    ) -> requests.Response:
        """Make HTTP request.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            path: API path (will be joined with endpoint)
            json: JSON payload
            data: Raw data payload
            headers: Additional headers
            params: Query parameters
            **kwargs: Additional requests arguments

        Returns:
            Response object
        """
        url = f"{self.endpoint.rstrip('/')}/{path.lstrip('/')}"
        request_headers = dict(self.session.headers)
        if headers:
            request_headers.update(headers)

        return self.session.request(
            method=method,
            url=url,
            json=json,
            data=data,
            headers=request_headers,
            params=params,
            timeout=config.timeout,
            **kwargs,
        )

    def get(self, path: str, **kwargs) -> requests.Response:
        """GET request."""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """POST request."""
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        """PUT request."""
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE request."""
        return self.request("DELETE", path, **kwargs)

    def head(self, path: str, **kwargs) -> requests.Response:
        """HEAD request."""
        return self.request("HEAD", path, **kwargs)


class HFClientWrapper:
    """Wrapper around HuggingFace Hub client for testing.

    This wrapper ensures we're using the correct endpoint and provides
    utilities for testing HF API compatibility.
    """

    def __init__(self, endpoint: str = None, token: str = None):
        """Initialize HF client wrapper.

        Args:
            endpoint: API endpoint URL
            token: API token for authentication
        """
        # Remove trailing slash from endpoint to avoid double slash in URLs
        self.endpoint = (endpoint or config.endpoint).rstrip("/")
        self.token = token

        # Set environment variable for HuggingFace client
        os.environ["HF_ENDPOINT"] = self.endpoint
        if self.token:
            os.environ["HF_TOKEN"] = self.token

        self.api = HfApi(endpoint=self.endpoint, token=self.token)

    def create_repo(
        self, repo_id: str, repo_type: str = "model", private: bool = False
    ):
        """Create repository."""
        return self.api.create_repo(
            repo_id=repo_id, repo_type=repo_type, private=private
        )

    def delete_repo(self, repo_id: str, repo_type: str = "model"):
        """Delete repository."""
        return self.api.delete_repo(repo_id=repo_id, repo_type=repo_type)

    def repo_info(self, repo_id: str, repo_type: str = "model", revision: str = None):
        """Get repository info."""
        return self.api.repo_info(
            repo_id=repo_id, repo_type=repo_type, revision=revision
        )

    def list_repo_files(
        self, repo_id: str, repo_type: str = "model", revision: str = None
    ):
        """List repository files."""
        return self.api.list_repo_files(
            repo_id=repo_id, repo_type=repo_type, revision=revision
        )

    def upload_file(
        self,
        path_or_fileobj,
        path_in_repo: str,
        repo_id: str,
        repo_type: str = "model",
        commit_message: str = None,
    ):
        """Upload single file."""
        return self.api.upload_file(
            path_or_fileobj=path_or_fileobj,
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message=commit_message or "Upload file",
        )

    def upload_folder(
        self,
        folder_path: str,
        path_in_repo: str,
        repo_id: str,
        repo_type: str = "model",
        commit_message: str = None,
    ):
        """Upload folder."""
        return self.api.upload_folder(
            folder_path=folder_path,
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message=commit_message or "Upload folder",
        )

    def download_file(
        self,
        repo_id: str,
        filename: str,
        repo_type: str = "model",
        revision: str = None,
    ) -> str:
        """Download file and return local path."""
        return self.api.hf_hub_download(
            repo_id=repo_id, filename=filename, repo_type=repo_type, revision=revision
        )

    def delete_file(
        self,
        path_in_repo: str,
        repo_id: str,
        repo_type: str = "model",
        commit_message: str = None,
    ):
        """Delete file."""
        return self.api.delete_file(
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message=commit_message or "Delete file",
        )


class BaseTestCase:
    """Base test case with common utilities."""

    @classmethod
    def setup_class(cls):
        """Setup test class."""
        cls.config = config
        cls.http_client = HTTPClient()
        cls.temp_dir = tempfile.mkdtemp(prefix="kohakuhub_test_")

    @classmethod
    def teardown_class(cls):
        """Cleanup test class."""
        import shutil

        if hasattr(cls, "temp_dir") and Path(cls.temp_dir).exists():
            shutil.rmtree(cls.temp_dir)

    def create_temp_file(self, name: str, content: bytes) -> str:
        """Create temporary file for testing.

        Args:
            name: File name
            content: File content

        Returns:
            Path to created file
        """
        path = Path(self.temp_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def create_random_file(self, name: str, size_mb: float) -> str:
        """Create temporary file with random content.

        Args:
            name: File name
            size_mb: File size in megabytes

        Returns:
            Path to created file
        """
        size_bytes = int(size_mb * 1024 * 1024)
        content = os.urandom(size_bytes)
        return self.create_temp_file(name, content)

    def assert_response_ok(
        self, response: requests.Response, expected_status: int = 200
    ):
        """Assert HTTP response is successful.

        Args:
            response: HTTP response
            expected_status: Expected status code
        """
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.text}"

    def assert_response_error(
        self,
        response: requests.Response,
        expected_status: int,
        expected_error_code: str = None,
    ):
        """Assert HTTP response is an error.

        Args:
            response: HTTP response
            expected_status: Expected status code
            expected_error_code: Expected HF error code (e.g., "RepoNotFound")
        """
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}"

        if expected_error_code:
            error_code = response.headers.get("X-Error-Code")
            assert (
                error_code == expected_error_code
            ), f"Expected error code {expected_error_code}, got {error_code}"

    def get_test_repo_id(self, name: str) -> str:
        """Generate test repository ID.

        Args:
            name: Repository name

        Returns:
            Full repository ID with test prefix
        """
        return f"{config.username}/{config.repo_prefix}-{name}"

    def get_test_org_repo_id(self, name: str) -> str:
        """Generate test organization repository ID.

        Args:
            name: Repository name

        Returns:
            Full repository ID with organization
        """
        return f"{config.org_name}/{config.repo_prefix}-{name}"
