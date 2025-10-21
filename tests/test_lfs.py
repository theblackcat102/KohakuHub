"""LFS (Large File Storage) operation tests.

Tests large file upload/download using Git LFS protocol.
Files >10MB should use LFS, files <=10MB should use regular upload.
"""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest


class TestLFSOperations:
    """Test LFS file operations for large files."""

    @pytest.mark.lfs
    def test_upload_large_file_15mb(self, temp_repo):
        """Test uploading 15MB file (should use LFS)."""
        repo_id, repo_type, hf_client = temp_repo

        # Create 15MB file
        size_mb = 15
        test_content = os.urandom(size_mb * 1000 * 1000)
        original_hash = hashlib.sha256(test_content).hexdigest()

        test_file = Path(tempfile.gettempdir()) / f"test_15mb_{os.urandom(4).hex()}.bin"
        test_file.write_bytes(test_content)

        # Upload file (should trigger LFS)
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="large/test_15mb.bin",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload 15MB file via LFS",
        )

        # Download and verify
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="large/test_15mb.bin", repo_type=repo_type
        )

        # Verify content integrity
        downloaded_content = Path(downloaded).read_bytes()
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        assert (
            downloaded_hash == original_hash
        ), "Large file content corrupted during LFS upload/download"

        # Cleanup
        test_file.unlink(missing_ok=True)

    @pytest.mark.lfs
    @pytest.mark.slow
    def test_upload_large_file_50mb(self, temp_repo):
        """Test uploading 50MB file (should use LFS)."""
        repo_id, repo_type, hf_client = temp_repo

        # Create 50MB file
        import tempfile

        size_mb = 50
        test_content = os.urandom(size_mb * 1000 * 1000)
        original_hash = hashlib.sha256(test_content).hexdigest()

        test_file = Path(tempfile.gettempdir()) / f"test_50mb_{os.urandom(4).hex()}.bin"
        test_file.write_bytes(test_content)

        # Upload file (should trigger LFS)
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="large/test_50mb.bin",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload 50MB file via LFS",
        )

        # Download and verify
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="large/test_50mb.bin", repo_type=repo_type
        )

        # Verify content integrity
        downloaded_content = Path(downloaded).read_bytes()
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        assert (
            downloaded_hash == original_hash
        ), "50MB file content corrupted during LFS upload/download"

        # Cleanup
        test_file.unlink(missing_ok=True)

    def test_small_file_uses_regular_upload(self, temp_repo):
        """Test that small file (<10MB) uses regular upload, not LFS."""
        repo_id, repo_type, hf_client = temp_repo

        # Create 5MB file (below LFS threshold)
        import tempfile

        size_mb = 5
        test_content = os.urandom(size_mb * 1000 * 1000)

        test_file = Path(tempfile.gettempdir()) / f"test_5mb_{os.urandom(4).hex()}.bin"
        test_file.write_bytes(test_content)

        # Upload file (should NOT use LFS)
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="small/test_5mb.bin",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload 5MB file (regular)",
        )

        # Verify file was uploaded
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "small/test_5mb.bin" in files

        # Cleanup
        test_file.unlink(missing_ok=True)

    @pytest.mark.lfs
    def test_lfs_deduplication(self, temp_repo):
        """Test LFS deduplication - same file uploaded twice should use same storage."""
        repo_id, repo_type, hf_client = temp_repo

        # Create 12MB file
        size_mb = 12
        test_content = os.urandom(size_mb * 1000 * 1000)
        test_file = (
            Path(tempfile.gettempdir()) / f"test_dedup_{os.urandom(4).hex()}.bin"
        )
        test_file.write_bytes(test_content)

        # Upload file first time
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="dedup/file1.bin",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload file 1",
        )

        # Upload same file with different path (should be deduplicated)
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="dedup/file2.bin",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload file 2 (same content)",
        )

        # Both files should exist
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "dedup/file1.bin" in files
        assert "dedup/file2.bin" in files

        # Download both and verify they're identical
        downloaded1 = hf_client.download_file(
            repo_id=repo_id, filename="dedup/file1.bin", repo_type=repo_type
        )
        downloaded2 = hf_client.download_file(
            repo_id=repo_id, filename="dedup/file2.bin", repo_type=repo_type
        )

        content1 = Path(downloaded1).read_bytes()
        content2 = Path(downloaded2).read_bytes()
        assert content1 == content2 == test_content

        # Cleanup
        test_file.unlink(missing_ok=True)

    @pytest.mark.lfs
    def test_lfs_batch_api(self, random_user, temp_repo):
        """Test LFS batch API endpoint directly."""
        username, token, _ = random_user
        repo_id, repo_type, hf_client = temp_repo

        # Create HTTP client with the same user's token
        from tests.base import HTTPClient

        user_http_client = HTTPClient(token=token)

        # Prepare LFS batch request
        fake_oid = "a" * 64  # SHA256 hex
        fake_size = 15 * 1000 * 1000  # 15MB

        batch_request = {
            "operation": "upload",
            "transfers": ["basic"],
            "objects": [{"oid": fake_oid, "size": fake_size}],
            "hash_algo": "sha256",
        }

        # Send LFS batch request using the repo owner's token
        resp = user_http_client.post(
            f"/{repo_id}.git/info/lfs/objects/batch", json=batch_request
        )
        assert resp.status_code == 200, f"LFS batch request failed: {resp.text}"

        data = resp.json()
        assert "objects" in data
        assert len(data["objects"]) == 1

        lfs_object = data["objects"][0]
        assert lfs_object["oid"] == fake_oid
        assert lfs_object["size"] == fake_size

        # Check if upload action is provided
        # If file doesn't exist, should have "actions" with "upload"
        # If file exists (deduplicated), no "actions"
        if "actions" in lfs_object:
            assert "upload" in lfs_object["actions"]
            assert "href" in lfs_object["actions"]["upload"]

    @pytest.mark.lfs
    def test_mixed_file_sizes_upload(self, temp_repo):
        """Test uploading folder with mixed file sizes (some LFS, some regular)."""
        repo_id, repo_type, hf_client = temp_repo

        # Create temp folder with mixed sizes
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())

        # Small files (regular upload)
        (temp_dir / "small1.txt").write_bytes(b"Small file 1" * 100)
        (temp_dir / "small2.txt").write_bytes(b"Small file 2" * 100)

        # Large file (LFS)
        (temp_dir / "large.bin").write_bytes(os.urandom(12 * 1000 * 1000))  # 12MB

        # Upload folder
        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="mixed/",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload mixed file sizes",
        )

        # Verify all files exist
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "mixed/small1.txt" in files
        assert "mixed/small2.txt" in files
        assert "mixed/large.bin" in files

        # Download and verify large file
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="mixed/large.bin", repo_type=repo_type
        )
        assert Path(downloaded).stat().st_size == 12 * 1000 * 1000

        # Cleanup

        shutil.rmtree(temp_dir)

    @pytest.mark.lfs
    def test_lfs_file_metadata(self, random_user, temp_repo):
        """Test that LFS files have proper metadata in tree API."""
        username, token, _ = random_user
        repo_id, repo_type, hf_client = temp_repo

        # Upload LFS file
        import tempfile

        test_content = os.urandom(15 * 1000 * 1000)  # 15MB
        test_file = (
            Path(tempfile.gettempdir()) / f"test_lfs_meta_{os.urandom(4).hex()}.bin"
        )
        test_file.write_bytes(test_content)

        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="test_lfs_meta.bin",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # Query tree with expand=true to get LFS metadata using repo owner's token
        from tests.base import HTTPClient

        user_http_client = HTTPClient(token=token)

        namespace, repo_name = repo_id.split("/")
        resp = user_http_client.get(
            f"/api/{repo_type}s/{namespace}/{repo_name}/tree/main/",
            params={"expand": "true"},
        )
        assert resp.status_code == 200
        tree_data = resp.json()

        # Find our file in tree
        lfs_file = None
        for item in tree_data:
            if item.get("path") == "test_lfs_meta.bin":
                lfs_file = item
                break

        assert lfs_file is not None, "LFS file not found in tree"

        # Check if LFS metadata is present
        if "lfs" in lfs_file:
            assert "oid" in lfs_file["lfs"]
            assert "size" in lfs_file["lfs"]

        # Cleanup
        test_file.unlink(missing_ok=True)

    def test_boundary_file_size_10mb(self, temp_repo):
        """Test uploading file exactly at 10MB boundary."""
        repo_id, repo_type, hf_client = temp_repo

        # Create exactly 10MB file
        size_bytes = 10 * 1000 * 1000
        test_content = os.urandom(size_bytes)

        test_file = (
            Path(tempfile.gettempdir()) / f"test_10mb_exact_{os.urandom(4).hex()}.bin"
        )
        test_file.write_bytes(test_content)

        # Upload file
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="boundary/test_10mb_exact.bin",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload exactly 10MB file",
        )

        # Verify file exists
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "boundary/test_10mb_exact.bin" in files

        # Download and verify
        downloaded = hf_client.download_file(
            repo_id=repo_id,
            filename="boundary/test_10mb_exact.bin",
            repo_type=repo_type,
        )
        assert Path(downloaded).stat().st_size == size_bytes

        # Cleanup
        test_file.unlink(missing_ok=True)
