"""File operation tests.

Tests file upload, download, deletion, and listing.
Covers both small files (inline) and large files (LFS).
"""

import hashlib
import os
from pathlib import Path

import pytest


class TestFileOperations:
    """Test file upload, download, and deletion operations."""

    def test_upload_small_file_hf_client(self, temp_repo):
        """Test uploading small file (<10MB) using HuggingFace Hub client."""
        repo_id, repo_type, hf_client = temp_repo

        # Create small test file in temp directory
        import tempfile

        test_content = b"Hello, KohakuHub! This is a small test file."
        test_file = (
            Path(tempfile.gettempdir()) / f"test_small_{os.urandom(4).hex()}.txt"
        )
        test_file.write_bytes(test_content)

        # Upload file
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="test_small.txt",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Add small test file",
        )

        # Download and verify
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="test_small.txt", repo_type=repo_type
        )
        assert Path(downloaded).exists()
        content = Path(downloaded).read_bytes()
        assert content == test_content

        # Cleanup temp file
        test_file.unlink(missing_ok=True)

    def test_upload_folder_hf_client(self, temp_repo):
        """Test uploading folder using HuggingFace Hub client."""
        repo_id, repo_type, hf_client = temp_repo

        # Create temp folder with files
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "file1.txt").write_bytes(b"File 1 content")
        (temp_dir / "file2.txt").write_bytes(b"File 2 content")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file3.txt").write_bytes(b"File 3 content")

        # Upload folder
        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="uploaded_folder/",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Upload folder",
        )

        # Verify files exist
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "uploaded_folder/file1.txt" in files
        assert "uploaded_folder/file2.txt" in files
        assert "uploaded_folder/subdir/file3.txt" in files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    def test_download_file_hf_client(self, temp_repo):
        """Test downloading file using HuggingFace Hub client."""
        repo_id, repo_type, hf_client = temp_repo

        # Upload a file first
        import tempfile

        test_content = b"Download test content"
        test_file = (
            Path(tempfile.gettempdir()) / f"test_download_{os.urandom(4).hex()}.txt"
        )
        test_file.write_bytes(test_content)

        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="test_download.txt",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # Download file
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="test_download.txt", repo_type=repo_type
        )

        # Verify content
        assert Path(downloaded).exists()
        content = Path(downloaded).read_bytes()
        assert content == test_content

        # Cleanup
        test_file.unlink(missing_ok=True)

    def test_delete_file_hf_client(self, temp_repo):
        """Test deleting file using HuggingFace Hub client."""
        repo_id, repo_type, hf_client = temp_repo

        # Upload a file first
        import tempfile

        test_content = b"File to be deleted"
        test_file = (
            Path(tempfile.gettempdir()) / f"test_delete_{os.urandom(4).hex()}.txt"
        )
        test_file.write_bytes(test_content)

        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="test_delete.txt",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # Verify file exists
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "test_delete.txt" in files

        # Delete file
        hf_client.delete_file(
            path_in_repo="test_delete.txt",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Delete test file",
        )

        # Verify file is deleted
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "test_delete.txt" not in files

        # Cleanup
        test_file.unlink(missing_ok=True)

    def test_list_repo_files(self, temp_repo):
        """Test listing repository files."""
        repo_id, repo_type, hf_client = temp_repo

        # Upload multiple files
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        files_to_upload = {
            "file1.txt": b"Content 1",
            "file2.txt": b"Content 2",
            "subdir/file3.txt": b"Content 3",
        }

        for file_path, content in files_to_upload.items():
            full_path = temp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)

        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # List files
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert isinstance(files, list)
        assert "file1.txt" in files
        assert "file2.txt" in files
        assert "subdir/file3.txt" in files

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    def test_file_metadata_head_request(self, random_user, temp_repo):
        """Test getting file metadata via HEAD request."""
        username, token, _ = random_user
        repo_id, repo_type, hf_client = temp_repo

        # Upload a file
        import tempfile

        test_content = b"Metadata test content"
        test_file = (
            Path(tempfile.gettempdir()) / f"test_metadata_{os.urandom(4).hex()}.txt"
        )
        test_file.write_bytes(test_content)

        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="test_metadata.txt",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # HEAD request to get metadata using repo owner's token
        from tests.base import HTTPClient

        user_http_client = HTTPClient(token=token)

        namespace, repo_name = repo_id.split("/")
        resp = user_http_client.head(
            f"/{repo_type}s/{namespace}/{repo_name}/resolve/main/test_metadata.txt"
        )
        assert resp.status_code == 200

        # Check headers
        assert "X-Repo-Commit" in resp.headers or "ETag" in resp.headers
        if "Content-Length" in resp.headers:
            assert int(resp.headers["Content-Length"]) == len(test_content)

        # Cleanup
        test_file.unlink(missing_ok=True)

    def test_upload_with_commit_message(self, temp_repo):
        """Test uploading file with custom commit message."""
        repo_id, repo_type, hf_client = temp_repo

        # Upload file with custom message
        import tempfile

        test_content = b"Commit message test"
        test_file = (
            Path(tempfile.gettempdir()) / f"test_commit_{os.urandom(4).hex()}.txt"
        )
        test_file.write_bytes(test_content)

        commit_message = "Custom commit message for testing"
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="test_commit.txt",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message=commit_message,
        )

        # Note: Verifying commit message would require commit history API
        # Just verify file was uploaded
        files = hf_client.list_repo_files(repo_id=repo_id, repo_type=repo_type)
        assert "test_commit.txt" in files

        # Cleanup
        test_file.unlink(missing_ok=True)

    def test_file_content_integrity(self, temp_repo):
        """Test that file content integrity is preserved through upload/download."""
        repo_id, repo_type, hf_client = temp_repo

        # Create file with random content
        import tempfile

        test_content = os.urandom(1024 * 100)  # 100KB random data
        original_hash = hashlib.sha256(test_content).hexdigest()

        test_file = (
            Path(tempfile.gettempdir()) / f"test_integrity_{os.urandom(4).hex()}.bin"
        )
        test_file.write_bytes(test_content)

        # Upload
        hf_client.upload_file(
            path_or_fileobj=str(test_file),
            path_in_repo="test_integrity.bin",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # Download
        downloaded = hf_client.download_file(
            repo_id=repo_id, filename="test_integrity.bin", repo_type=repo_type
        )

        # Verify integrity
        downloaded_content = Path(downloaded).read_bytes()
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        assert (
            downloaded_hash == original_hash
        ), "File content corrupted during upload/download"

        # Cleanup
        test_file.unlink(missing_ok=True)

    def test_nonexistent_file_download(self, temp_repo):
        """Test downloading non-existent file."""
        repo_id, repo_type, hf_client = temp_repo

        # Try to download non-existent file
        with pytest.raises(Exception) as exc_info:
            hf_client.download_file(
                repo_id=repo_id, filename="nonexistent.txt", repo_type=repo_type
            )

        # Should be an error (404 or file not found)
        error_msg = str(exc_info.value).lower()
        assert (
            "404" in error_msg or "not found" in error_msg or "cannot find" in error_msg
        )

    def test_tree_endpoint(self, random_user, temp_repo):
        """Test tree endpoint for listing files."""
        username, token, _ = random_user
        repo_id, repo_type, hf_client = temp_repo

        # Upload some files
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "file1.txt").write_bytes(b"Content 1")
        (temp_dir / "dir1").mkdir()
        (temp_dir / "dir1" / "file2.txt").write_bytes(b"Content 2")

        hf_client.upload_folder(
            folder_path=str(temp_dir),
            path_in_repo="",
            repo_id=repo_id,
            repo_type=repo_type,
        )

        # Query tree endpoint using repo owner's token
        from tests.base import HTTPClient

        user_http_client = HTTPClient(token=token)

        namespace, repo_name = repo_id.split("/")
        resp = user_http_client.get(
            f"/api/{repo_type}s/{namespace}/{repo_name}/tree/main/"
        )
        assert resp.status_code == 200
        tree_data = resp.json()
        assert isinstance(tree_data, list)

        # Check files are in tree
        paths = [item["path"] for item in tree_data]
        assert "file1.txt" in paths

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)
