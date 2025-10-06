"""Repository information and listing tests.

Tests repository metadata, listing, filtering, and privacy.
"""

import pytest

from tests.base import HTTPClient
from tests.config import config


class TestRepositoryInfo:
    """Test repository information and listing endpoints."""

    def test_get_repo_info_hf_client(self, temp_repo):
        """Test getting repository info using HF client."""
        repo_id, repo_type, hf_client = temp_repo

        # Get repository info
        info = hf_client.repo_info(repo_id=repo_id, repo_type=repo_type)
        assert info is not None

        # Check basic fields
        repo_field = getattr(info, "id", getattr(info, "repo_id", None))
        assert repo_id in str(repo_field)

    def test_get_repo_info_http_client(self, random_user, temp_repo):
        """Test getting repository info using HTTP client."""
        username, token, _ = random_user
        repo_id, repo_type, hf_client = temp_repo
        namespace, repo_name = repo_id.split("/")

        # Get repository info using repo owner's token
        user_http_client = HTTPClient(token=token)
        resp = user_http_client.get(f"/api/{repo_type}s/{namespace}/{repo_name}")
        assert resp.status_code == 200, f"Get repo info failed: {resp.text}"

        data = resp.json()
        assert isinstance(data, dict)
        # Should contain repository metadata

    def test_list_repos_by_author(self, random_user):
        """Test listing repositories by author."""
        import uuid

        username, token, hf_client = random_user

        unique_id = uuid.uuid4().hex[:6]
        # Create test repository
        repo_id = f"{username}/lst-{unique_id}"
        hf_client.create_repo(repo_id=repo_id, repo_type="model", private=False)

        # List repos by author
        http_client = HTTPClient(token=token)
        resp = http_client.get("/api/models", params={"author": username, "limit": 100})
        assert resp.status_code == 200
        repos = resp.json()
        assert isinstance(repos, list)

        # Our repo should be in the list
        repo_ids = [r.get("id") or r.get("repo_id") for r in repos]
        assert repo_id in repo_ids

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")

    def test_list_repos_with_limit(self, authenticated_http_client):
        """Test listing repositories with limit parameter."""
        # List repos with small limit
        resp = authenticated_http_client.get("/api/models", params={"limit": 5})
        assert resp.status_code == 200
        repos = resp.json()
        assert isinstance(repos, list)
        assert len(repos) <= 5

    def test_list_namespace_repos(self, random_user):
        """Test listing all repos under a namespace (user)."""
        import uuid

        username, token, hf_client = random_user

        unique_id = uuid.uuid4().hex[:6]
        # Create test repos of different types
        model_id = f"{username}/nsm-{unique_id}"  # namespace-model
        dataset_id = f"{username}/nsd-{unique_id}"  # namespace-dataset

        hf_client.create_repo(repo_id=model_id, repo_type="model", private=False)
        hf_client.create_repo(repo_id=dataset_id, repo_type="dataset", private=False)

        # List all repos for namespace
        http_client = HTTPClient(token=token)
        resp = http_client.get(f"/api/users/{username}/repos")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

        # Should have models and datasets grouped
        if "models" in data:
            model_ids = [r.get("id") or r.get("repo_id") for r in data["models"]]
            assert model_id in model_ids

        if "datasets" in data:
            dataset_ids = [r.get("id") or r.get("repo_id") for r in data["datasets"]]
            assert dataset_id in dataset_ids

        # Cleanup
        hf_client.delete_repo(repo_id=model_id, repo_type="model")
        hf_client.delete_repo(repo_id=dataset_id, repo_type="dataset")

    def test_private_repo_visibility(self, random_user):
        """Test that private repositories are only visible to owner."""
        import uuid

        username, token, hf_client = random_user

        unique_id = uuid.uuid4().hex[:6]
        # Create private repository
        repo_id = f"{username}/prv-{unique_id}"
        hf_client.create_repo(repo_id=repo_id, repo_type="model", private=True)

        # Owner should see it
        owner_client = HTTPClient(token=token)
        resp = owner_client.get("/api/models", params={"author": username})
        assert resp.status_code == 200
        repos = resp.json()
        repo_ids = [r.get("id") or r.get("repo_id") for r in repos]
        assert repo_id in repo_ids, "Owner should see private repo"

        # Unauthenticated user should NOT see it
        unauth_client = HTTPClient()
        resp = unauth_client.get("/api/models", params={"author": username})
        assert resp.status_code == 200
        repos = resp.json()
        repo_ids = [r.get("id") or r.get("repo_id") for r in repos]
        # Private repo should NOT be in list for unauthenticated user
        assert (
            repo_id not in repo_ids
        ), "Unauthenticated user should NOT see private repo"

        # Cleanup
        hf_client.delete_repo(repo_id=repo_id, repo_type="model")

    def test_repo_revision_info(self, random_user, temp_repo):
        """Test getting repository info for specific revision."""
        username, token, _ = random_user
        repo_id, repo_type, hf_client = temp_repo

        # Upload file to create commit
        import tempfile
        from pathlib import Path

        temp_file = Path(tempfile.mktemp())
        temp_file.write_bytes(b"Test content")

        hf_client.upload_file(
            path_or_fileobj=str(temp_file),
            path_in_repo="test.txt",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # Get info for specific revision (main) using repo owner's token
        user_http_client = HTTPClient(token=token)
        namespace, repo_name = repo_id.split("/")
        resp = user_http_client.get(
            f"/api/{repo_type}s/{namespace}/{repo_name}/revision/main"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

        # Cleanup
        temp_file.unlink(missing_ok=True)

    @pytest.mark.skip(reason="Form(list[str]) encoding not yet working - returns 422")
    def test_repo_paths_info(self, random_user, temp_repo):
        """Test getting info for specific paths in repository.

        SKIPPED: FastAPI Form(list[str]) requires special encoding that current
        requests library usage doesn't handle correctly.

        Error: {"detail":[{"type":"missing","loc":["body","paths"],"msg":"Field required"}]}

        TODO: Need to determine correct multipart/form-data encoding for list[str].
        Endpoint signature: paths: list[str] = Form(...), expand: bool = Form(False)
        """
        pass

    def test_nonexistent_repo_info(self, authenticated_http_client):
        """Test getting info for non-existent repository."""
        namespace = config.username
        repo_name = "nonexistent-repo-xyz"

        resp = authenticated_http_client.get(f"/api/models/{namespace}/{repo_name}")
        assert resp.status_code == 404

        # Check for HF error headers
        error_code = resp.headers.get("X-Error-Code")
        if error_code:
            assert error_code == "RepoNotFound"

    def test_list_repo_files(self, temp_repo):
        """Test listing files in repository."""
        repo_id, repo_type, hf_client = temp_repo

        # Upload some files
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "README.md").write_bytes(b"# Test Repo")
        (temp_dir / "config.json").write_bytes(b'{"key": "value"}')
        (temp_dir / "data").mkdir()
        (temp_dir / "data" / "file.txt").write_bytes(b"Data file")

        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # List files
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert isinstance(files, list)
        assert "README.md" in files
        assert "config.json" in files
        assert "data/file.txt" in files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    def test_tree_recursive_listing(self, random_user, temp_repo):
        """Test recursive tree listing."""
        username, token, _ = random_user
        repo_id, repo_type, hf_client = temp_repo

        # Upload nested structure
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "level1").mkdir()
        (temp_dir / "level1" / "file1.txt").write_bytes(b"File 1")
        (temp_dir / "level1" / "level2").mkdir()
        (temp_dir / "level1" / "level2" / "file2.txt").write_bytes(b"File 2")

        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # Query tree with recursive=true using repo owner's token
        user_http_client = HTTPClient(token=token)
        namespace, repo_name = repo_id.split("/")
        resp = user_http_client.get(
            f"/api/{repo_type}s/{namespace}/{repo_name}/tree/main/",
            params={"recursive": "true"},
        )
        assert resp.status_code == 200
        tree_data = resp.json()
        assert isinstance(tree_data, list)

        # Should include nested files
        paths = [item["path"] for item in tree_data]
        assert any("level1/file1.txt" in p for p in paths)
        assert any("level1/level2/file2.txt" in p for p in paths)

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)
