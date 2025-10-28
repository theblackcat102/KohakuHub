"""
File lookup utilities for XET API.

Maps file_id (SHA256) to repository and file records, with permission checks.
"""

from fastapi import HTTPException

from kohakuhub.db import File, Repository, User
from kohakuhub.auth.permissions import check_repo_read_permission


def lookup_file_by_sha256(file_id: str) -> tuple[Repository, File]:
    """
    Lookup file by SHA256 hash.

    Args:
        file_id: SHA256 hash of the file

    Returns:
        Tuple of (repository, file_record)

    Raises:
        HTTPException: 404 if file not found
    """
    # Query File table by SHA256
    file_record = File.get_or_none(File.sha256 == file_id, File.is_deleted == False)

    if not file_record:
        raise HTTPException(
            status_code=404, detail={"error": f"File with SHA256 {file_id} not found"}
        )

    # Get associated repository
    repo = file_record.repository

    return repo, file_record


def check_file_read_permission(repo: Repository, user: User | None) -> None:
    """
    Check if user has read permission for the repository containing the file.

    Args:
        repo: Repository object
        user: User object or None for anonymous access

    Raises:
        HTTPException: 403 if permission denied
    """
    check_repo_read_permission(repo, user)
