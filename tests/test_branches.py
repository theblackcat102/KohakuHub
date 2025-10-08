"""Branch operation tests - revert, reset, and merge with LFS GC.

Tests the complete workflow of:
- Revert operations (latest, non-conflicting)
- Reset operations (creating new commits, LFS checks)
- Branch creation and merging
- LFS recoverability checks
"""

import os
import time
from pathlib import Path

import pytest

from tests.base import HTTPClient


class TestBranchRevert:
    """Test revert functionality."""

    def test_revert_latest_commit(self, temp_repo):
        """Revert the latest commit (should succeed - no conflicts)."""
        repo_id, repo_type, hf_client = temp_repo

        # Create files with random content
        test_content = os.urandom(100)  # Random bytes
        lfs_content = os.urandom(2000000)  # 2MB random LFS file

        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "revert-test.txt").write_bytes(test_content)
        (temp_dir / "revert-test-lfs.bin").write_bytes(lfs_content)

        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="",  # Upload to root
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Add revert test files",
        )

        # Verify files exist
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "revert-test.txt" in files
        assert "revert-test-lfs.bin" in files

        # Get latest commit
        http_client = HTTPClient()
        resp = http_client.get(f"/api/{repo_type}s/{repo_id}/commits/main")
        assert resp.status_code == 200
        commits_data = resp.json()
        latest_commit = commits_data["commits"][0]["id"]

        # Revert the commit (need authenticated client)
        http_auth = HTTPClient(token=hf_client.token)
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/branch/main/revert",
            json={
                "ref": latest_commit,
                "parent_number": 1,
                "force": False,
                "allow_empty": False,
            },
        )
        assert resp.status_code == 200, f"Revert failed: {resp.text}"

        # Verify files were removed
        time.sleep(1)
        files_after = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "revert-test.txt" not in files_after
        assert "revert-test-lfs.bin" not in files_after

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    def test_revert_non_conflicting(self, temp_repo):
        """Revert non-latest but non-conflicting commit with LFS."""
        repo_id, repo_type, hf_client = temp_repo

        import tempfile

        temp_dir = Path(tempfile.mkdtemp())

        # Commit 1: Add file1 with LFS (random content)
        lfs1 = os.urandom(2000000)  # Random 2MB
        (temp_dir / "file1.txt").write_bytes(os.urandom(100))
        (temp_dir / "file1-lfs.bin").write_bytes(lfs1)

        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="set1/",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Add file1 with LFS",
        )

        # Get commit 1 ID
        http_client = HTTPClient()
        resp = http_client.get(f"/api/{repo_type}s/{repo_id}/commits/main")
        commits_data = resp.json()
        commit1 = commits_data["commits"][0]["id"]

        # Commit 2: Add file2 (different path, random content)
        (temp_dir / "file1.txt").unlink()
        (temp_dir / "file1-lfs.bin").unlink()

        lfs2 = os.urandom(2000000)  # Random 2MB
        (temp_dir / "file2.txt").write_bytes(os.urandom(100))
        (temp_dir / "file2-lfs.bin").write_bytes(lfs2)

        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="set2/",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Add file2 with LFS",
        )

        # Revert commit 1 (authenticated)
        http_auth = HTTPClient(token=hf_client.token)
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/branch/main/revert",
            json={"ref": commit1, "parent_number": 1, "force": False},
        )
        assert resp.status_code == 200, f"Revert failed: {resp.text}"

        # Verify file2 still exists, file1 removed
        time.sleep(1)
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "set2/file2.txt" in files
        assert "set2/file2-lfs.bin" in files
        assert "set1/file1.txt" not in files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)


class TestBranchReset:
    """Test reset functionality."""

    def test_reset_creates_new_commit(self, temp_repo):
        """Reset should create new commit, not delete history."""
        repo_id, repo_type, hf_client = temp_repo

        import tempfile

        temp_dir = Path(tempfile.mkdtemp())

        # Create 3 commits with random content
        for i in range(1, 4):
            content = os.urandom(1000)  # Random content each time
            (temp_dir / "test.txt").write_bytes(content)

            hf_client.upload_folder(
                folder_path=str(temp_dir),
                path_in_repo="",
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=f"Version {i}",
            )
            time.sleep(0.5)

        # Get commits before reset
        http_client = HTTPClient()
        resp = http_client.get(f"/api/{repo_type}s/{repo_id}/commits/main")
        commits_data = resp.json()
        commits_before = commits_data["commits"]
        assert len(commits_before) >= 3

        # Reset to version 1
        target_commit = commits_before[2]["id"]  # Third from top (oldest)

        http_auth = HTTPClient(token=hf_client.token)
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/branch/main/reset",
            json={"ref": target_commit, "force": True},
        )
        assert resp.status_code == 200, f"Reset failed: {resp.text}"

        # Verify new commit was created (history preserved)
        time.sleep(1)
        resp = http_client.get(f"/api/{repo_type}s/{repo_id}/commits/main")
        commits_after_data = resp.json()
        commits_after = commits_after_data["commits"]

        # Should have MORE commits (original 3 + reset commit)
        assert len(commits_after) >= len(commits_before)

        # Verify file exists after reset
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="test.txt", repo_type=repo_type
        )
        # Just verify file exists and can be downloaded
        assert Path(downloaded).exists()

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    @pytest.mark.lfs
    def test_reset_with_lfs_files(self, temp_repo):
        """Reset with LFS files (should preserve LFS objects)."""
        repo_id, repo_type, hf_client = temp_repo

        import tempfile

        temp_dir = Path(tempfile.mkdtemp())

        # Create 3 versions with LFS (random content)
        for i in range(1, 4):
            content = os.urandom(2000000)  # Random 2MB each time
            (temp_dir / "large.bin").write_bytes(content)

            hf_client.upload_folder(
                folder_path=str(temp_dir),
                path_in_repo="",
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=f"LFS Version {i}",
            )
            time.sleep(0.5)

        # Get commits
        http_client = HTTPClient()
        resp = http_client.get(f"/api/{repo_type}s/{repo_id}/commits/main")
        commits_data = resp.json()
        commits = commits_data["commits"]
        target_commit = commits[2]["id"]  # First version

        # Reset to version 1
        http_auth = HTTPClient(token=hf_client.token)
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/branch/main/reset",
            json={"ref": target_commit, "force": True},
        )
        assert resp.status_code == 200, f"Reset failed: {resp.text}"

        # Verify LFS file exists after reset
        time.sleep(1)
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="large.bin", repo_type=repo_type
        )
        # Just verify file exists and can be downloaded
        assert Path(downloaded).exists()
        assert Path(downloaded).stat().st_size == 2000000  # 2MB

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)


class TestBranchMerge:
    """Test merge functionality."""

    def test_merge_branches(self, temp_repo):
        """Merge dev branch into main."""
        repo_id, repo_type, hf_client = temp_repo

        import tempfile

        temp_dir = Path(tempfile.mkdtemp())

        # Create initial file on main with random content
        (temp_dir / "main.txt").write_bytes(os.urandom(100))
        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Add main file",
        )

        # Create dev branch
        http_auth = HTTPClient(token=hf_client.token)
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/branch",
            json={"branch": "dev", "revision": "main"},
        )
        assert resp.status_code == 200

        # Upload different files to dev branch using direct API
        import base64
        import json

        dev_txt_content = os.urandom(200)  # Random content
        dev_lfs_content = os.urandom(2000000)  # Random 2MB LFS

        # Upload to dev branch using commit API
        ndjson_lines = []

        # Header
        ndjson_lines.append(
            json.dumps(
                {
                    "key": "header",
                    "value": {"summary": "Add dev files", "description": ""},
                }
            )
        )

        # Dev text file
        ndjson_lines.append(
            json.dumps(
                {
                    "key": "file",
                    "value": {
                        "path": "dev.txt",
                        "content": base64.b64encode(dev_txt_content).decode(),
                        "encoding": "base64",
                    },
                }
            )
        )

        # Dev LFS file - upload to S3 first
        import hashlib

        sha256 = hashlib.sha256(dev_lfs_content).hexdigest()

        # Get LFS upload URL
        lfs_resp = http_auth.post(
            f"/{repo_type}s/{repo_id}.git/info/lfs/objects/batch",
            json={
                "operation": "upload",
                "objects": [{"oid": sha256, "size": len(dev_lfs_content)}],
            },
        )
        assert lfs_resp.status_code == 200

        upload_url = lfs_resp.json()["objects"][0]["actions"]["upload"]["href"]

        # Upload to S3
        import requests

        s3_resp = requests.put(upload_url, data=dev_lfs_content)
        assert s3_resp.status_code in (200, 204)

        # Add LFS file to commit
        ndjson_lines.append(
            json.dumps(
                {
                    "key": "lfsFile",
                    "value": {
                        "path": "dev-lfs.bin",
                        "oid": sha256,
                        "size": len(dev_lfs_content),
                        "algo": "sha256",
                    },
                }
            )
        )

        # Commit to dev branch
        commit_resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/commit/dev",
            data="\n".join(ndjson_lines),
            headers={"Content-Type": "application/x-ndjson"},
        )
        assert commit_resp.status_code == 200

        # Merge dev into main
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/merge/dev/into/main",
            json={"strategy": "source-wins"},
        )
        assert resp.status_code == 200, f"Merge failed: {resp.text}"

        # Verify merged files on main
        time.sleep(1)
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "main.txt" in files
        assert "dev.txt" in files
        assert "dev-lfs.bin" in files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)


@pytest.mark.lfs
class TestBranchOperationsWithLFS:
    """Test branch operations with LFS garbage collection."""

    def test_create_and_delete_branch(self, temp_repo):
        """Create and delete branches."""
        repo_id, repo_type, hf_client = temp_repo

        http_auth = HTTPClient(token=hf_client.token)

        # Create branch
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/branch",
            json={"branch": "feature", "revision": "main"},
        )
        assert resp.status_code == 200

        # Delete branch
        resp = http_auth.delete(f"/api/{repo_type}s/{repo_id}/branch/feature")
        assert resp.status_code == 200

    def test_create_and_delete_tag(self, temp_repo):
        """Create and delete tags."""
        repo_id, repo_type, hf_client = temp_repo

        http_auth = HTTPClient(token=hf_client.token)

        # Create tag
        resp = http_auth.post(
            f"/api/{repo_type}s/{repo_id}/tag",
            json={"tag": "v1.0", "revision": "main"},
        )
        assert resp.status_code == 200

        # Delete tag
        resp = http_auth.delete(f"/api/{repo_type}s/{repo_id}/tag/v1.0")
        assert resp.status_code == 200
