"""Repository CRUD operation tests.

Tests repository creation, deletion, listing, moving, and info retrieval.
Uses actual Pydantic models from source code and validates HF API compatibility.
"""

import uuid

import pytest
from huggingface_hub.utils import HfHubHTTPError

from tests.config import config


class TestRepositoryCRUD:
    """Test repository CRUD operations."""

    def test_create_repo_hf_client(self, hf_client):
        """Test repository creation using HuggingFace Hub client."""
        unique_id = uuid.uuid4().hex[:6]
        repo_id = f"{config.username}/hfc-{unique_id}"  # hfc = hf-create

        # Create repository
        result = hf_client.create_repo(
            repo_id=repo_id, repo_type="model", private=False
        )
        assert result is not None

        # Verify repository exists
        info = hf_client.repo_info(repo_id=repo_id, repo_type="model")
        assert info is not None
        # Check if repo_id or id field contains our repo
        repo_field = getattr(info, "id", getattr(info, "repo_id", None))
        assert repo_id in str(repo_field)

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")

    def test_create_repo_http_client(self, authenticated_http_client):
        """Test repository creation using custom HTTP client with Pydantic model."""
        from kohakuhub.api.routers.repo_crud import CreateRepoPayload

        unique_id = uuid.uuid4().hex[:6]
        repo_name = f"htc-{unique_id}"  # htc = http-create

        # Create repository using actual Pydantic model
        payload = CreateRepoPayload(
            type="model",
            name=repo_name,
            organization=None,  # Use user's own namespace
            private=False,
        )

        resp = authenticated_http_client.post(
            "/api/repos/create", json=payload.model_dump()
        )
        assert resp.status_code == 200, f"Create repo failed: {resp.text}"
        data = resp.json()
        assert "url" in data or "repo_id" in data

        # Verify via GET endpoint
        resp = authenticated_http_client.get(
            f"/api/models/{config.username}/{repo_name}"
        )
        assert resp.status_code == 200, f"Get repo info failed: {resp.text}"

        # Cleanup using actual delete model
        from kohakuhub.api.routers.repo_crud import DeleteRepoPayload

        delete_payload = DeleteRepoPayload(
            type="model", name=repo_name, organization=None
        )

        resp = authenticated_http_client.delete(
            "/api/repos/delete", json=delete_payload.model_dump()
        )
        assert resp.status_code == 200

    def test_create_duplicate_repo(self, hf_client):
        """Test that creating duplicate repository fails."""
        unique_id = uuid.uuid4().hex[:6]
        repo_id = f"{config.username}/dup-{unique_id}"

        # Create first time
        hf_client.create_repo(repo_id=repo_id, repo_type="model", private=False)

        # Try to create again
        with pytest.raises(Exception) as exc_info:
            hf_client.create_repo(repo_id=repo_id, repo_type="model", private=False)

        # Verify it's the right error
        assert "exist" in str(exc_info.value).lower() or "400" in str(exc_info.value)

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")

    def test_create_private_repo(self, hf_client):
        """Test creating private repository."""
        unique_id = uuid.uuid4().hex[:6]
        repo_id = f"{config.username}/prv-{unique_id}"

        # Create private repository
        hf_client.create_repo(repo_id=repo_id, repo_type="model", private=True)

        # Verify it exists
        info = hf_client.repo_info(repo_id=repo_id, repo_type="model")
        assert info is not None

        # Check if private field exists (may vary by HF client version)
        if hasattr(info, "private"):
            assert info.private == True

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")

    def test_delete_repo_hf_client(self, hf_client):
        """Test repository deletion using HuggingFace Hub client."""
        unique_id = uuid.uuid4().hex[:6]
        repo_id = f"{config.username}/del-{unique_id}"

        # Create repository
        hf_client.create_repo(repo_id=repo_id, repo_type="model", private=False)

        # Delete repository
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")

        # Verify it's deleted
        with pytest.raises(HfHubHTTPError) as exc_info:
            hf_client.repo_info(repo_id=repo_id, repo_type="model")
        assert exc_info.value.response.status_code == 404

    def test_delete_nonexistent_repo(self, hf_client):
        """Test deleting non-existent repository."""
        unique_id = uuid.uuid4().hex[:6]
        repo_id = f"{config.username}/nonexistent-repo-{unique_id}"

        # Try to delete non-existent repo
        with pytest.raises(HfHubHTTPError) as exc_info:
            hf_client.delete_repo(repo_id=repo_id, repo_type="model")
        assert exc_info.value.response.status_code == 404

    def test_list_repos(self, authenticated_http_client, hf_client):
        """Test listing repositories."""
        # Create test repos with unique names
        unique_id = uuid.uuid4().hex[:6]
        repo_ids = [
            f"{config.username}/lst-{unique_id}-1",
            f"{config.username}/lst-{unique_id}-2",
        ]

        for repo_id in repo_ids:
            hf_client.create_repo(repo_id=repo_id, repo_type="model", private=False)

        # List repositories
        resp = authenticated_http_client.get(
            "/api/models", params={"author": config.username, "limit": 100}
        )
        assert resp.status_code == 200
        repos = resp.json()
        assert isinstance(repos, list)

        # Verify our repos are in the list
        repo_ids_in_list = [repo.get("id") or repo.get("repo_id") for repo in repos]
        for repo_id in repo_ids:
            assert repo_id in repo_ids_in_list, f"{repo_id} not found in repo list"

        # Cleanup
        for repo_id in repo_ids:
            hf_client.delete_repo(repo_id=repo_id, repo_type="model")

    def test_get_repo_info(self, hf_client):
        """Test getting repository information."""
        unique_id = uuid.uuid4().hex[:6]
        repo_id = f"{config.username}/inf-{unique_id}"

        # Create repository
        hf_client.create_repo(repo_id=repo_id, repo_type="model", private=False)

        # Get repository info
        info = hf_client.repo_info(repo_id=repo_id, repo_type="model")
        assert info is not None

        # Check basic fields
        repo_field = getattr(info, "id", getattr(info, "repo_id", None))
        assert repo_id in str(repo_field)

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")

    def test_move_repo(self, authenticated_http_client, hf_client):
        """Test moving/renaming repository."""
        from kohakuhub.api.routers.repo_crud import MoveRepoPayload

        unique_id = uuid.uuid4().hex[:6]
        old_name = f"old-{unique_id}"
        new_name = f"new-{unique_id}"
        old_repo_id = f"{config.username}/{old_name}"
        new_repo_id = f"{config.username}/{new_name}"

        # Create repository with old name
        hf_client.create_repo(repo_id=old_repo_id, repo_type="model", private=False)

        # Move repository using actual model
        payload = MoveRepoPayload(
            fromRepo=old_repo_id, toRepo=new_repo_id, type="model"
        )

        resp = authenticated_http_client.post(
            "/api/repos/move", json=payload.model_dump()
        )
        assert resp.status_code == 200, f"Move repo failed: {resp.text}"

        # Verify new name exists
        resp = authenticated_http_client.get(
            f"/api/models/{config.username}/{new_name}"
        )
        assert resp.status_code == 200, "New repo name should exist"

        # Verify old name doesn't exist (or redirects)
        resp = authenticated_http_client.get(
            f"/api/models/{config.username}/{old_name}", allow_redirects=False
        )
        # Should be 404 or 301/302 redirect
        assert resp.status_code in [301, 302, 404]

        # Cleanup
        hf_client.delete_repo(repo_id=new_repo_id, repo_type="model")

    @pytest.mark.parametrize("repo_type", ["model", "dataset"])
    def test_create_different_repo_types(self, hf_client, repo_type):
        """Test creating different repository types."""
        unique_id = uuid.uuid4().hex[:6]
        repo_id = f"{config.username}/typ-{unique_id}"  # Different types

        # Create repository
        hf_client.create_repo(repo_id=repo_id, repo_type=repo_type, private=False)

        # Verify it exists
        info = hf_client.repo_info(repo_id=repo_id, repo_type=repo_type)
        assert info is not None

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type=repo_type)

    def test_create_org_repo(self, authenticated_http_client, hf_client, test_org):
        """Test creating repository under organization."""
        from kohakuhub.api.routers.repo_crud import CreateRepoPayload

        unique_id = uuid.uuid4().hex[:6]
        repo_name = f"org-{unique_id}"

        # Create repository under organization using actual model
        payload = CreateRepoPayload(
            type="model", name=repo_name, organization=test_org, private=False
        )

        resp = authenticated_http_client.post(
            "/api/repos/create", json=payload.model_dump()
        )
        assert resp.status_code == 200, f"Create org repo failed: {resp.text}"

        # Verify it exists under organization
        repo_id = f"{test_org}/{repo_name}"
        info = hf_client.repo_info(repo_id=repo_id, repo_type="model")
        assert info is not None

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")
