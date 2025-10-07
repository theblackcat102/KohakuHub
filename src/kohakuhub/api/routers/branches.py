"""Branch and tag management API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from kohakuhub.api.utils.hf import (
    HFErrorCode,
    hf_error_response,
    hf_repo_not_found,
    hf_server_error,
)
from kohakuhub.api.utils.lakefs import get_lakefs_client, lakefs_repo_name
from kohakuhub.auth.dependencies import get_current_user
from kohakuhub.auth.permissions import check_repo_delete_permission
from kohakuhub.db_async import get_repository
from kohakuhub.db import Repository, User
from kohakuhub.logger import get_logger

logger = get_logger("BRANCHES")

router = APIRouter()


class CreateBranchPayload(BaseModel):
    """Payload for branch creation."""

    branch: str
    revision: Optional[str] = None  # Source revision (defaults to main)


@router.post("/{repo_type}s/{namespace}/{name}/branch")
async def create_branch(
    repo_type: str,
    namespace: str,
    name: str,
    payload: CreateBranchPayload,
    user: User = Depends(get_current_user),
):
    """Create a new branch.

    Args:
        repo_type: Repository type (model/dataset/space)
        namespace: Repository namespace
        name: Repository name
        payload: Branch creation parameters
        user: Current authenticated user

    Returns:
        Success message
    """
    repo_id = f"{namespace}/{name}"

    # Check if repository exists
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check if user has permission
    check_repo_delete_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)
    client = get_lakefs_client()

    try:
        # Get source revision (default to main)
        source_ref = payload.revision or "main"

        # Get commit ID from source ref
        source_branch = await client.get_branch(
            repository=lakefs_repo, branch=source_ref
        )
        source_commit = source_branch["commit_id"]

        # Create new branch
        await client.create_branch(
            repository=lakefs_repo,
            name=payload.branch,
            source=source_commit,
        )
    except Exception as e:
        return hf_server_error(f"Failed to create branch: {str(e)}")

    return {"success": True, "message": f"Branch '{payload.branch}' created"}


@router.delete("/{repo_type}s/{namespace}/{name}/branch/{branch}")
async def delete_branch(
    repo_type: str,
    namespace: str,
    name: str,
    branch: str,
    user: User = Depends(get_current_user),
):
    """Delete a branch.

    Args:
        repo_type: Repository type (model/dataset/space)
        namespace: Repository namespace
        name: Repository name
        branch: Branch name to delete
        user: Current authenticated user

    Returns:
        Success message
    """
    repo_id = f"{namespace}/{name}"

    # Check if repository exists
    repo_row = await get_repository(repo_type, namespace, name)

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check if user has permission
    check_repo_delete_permission(repo_row, user)

    # Prevent deletion of main branch
    if branch == "main":
        return hf_error_response(
            400,
            HFErrorCode.BAD_REQUEST,
            "Cannot delete main branch",
        )

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)
    client = get_lakefs_client()

    try:
        await client.delete_branch(repository=lakefs_repo, branch=branch)
    except Exception as e:
        return hf_server_error(f"Failed to delete branch: {str(e)}")

    return {"success": True, "message": f"Branch '{branch}' deleted"}


class CreateTagPayload(BaseModel):
    """Payload for tag creation."""

    tag: str
    revision: Optional[str] = None  # Source revision (defaults to main)
    message: Optional[str] = None


@router.post("/{repo_type}s/{namespace}/{name}/tag")
async def create_tag(
    repo_type: str,
    namespace: str,
    name: str,
    payload: CreateTagPayload,
    user: User = Depends(get_current_user),
):
    """Create a new tag.

    Args:
        repo_type: Repository type (model/dataset/space)
        namespace: Repository namespace
        name: Repository name
        payload: Tag creation parameters
        user: Current authenticated user

    Returns:
        Success message
    """
    repo_id = f"{namespace}/{name}"

    # Check if repository exists
    repo_row = await get_repository(repo_type, namespace, name)

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check if user has permission
    check_repo_delete_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)
    client = get_lakefs_client()

    try:
        # Get source revision (default to main)
        source_ref = payload.revision or "main"

        # Get commit ID from source ref
        source_branch = await client.get_branch(
            repository=lakefs_repo, branch=source_ref
        )
        source_commit = source_branch["commit_id"]

        # Create new tag
        await client.create_tag(
            repository=lakefs_repo,
            id=payload.tag,
            ref=source_commit,
        )
    except Exception as e:
        return hf_server_error(f"Failed to create tag: {str(e)}")

    return {"success": True, "message": f"Tag '{payload.tag}' created"}


@router.delete("/{repo_type}s/{namespace}/{name}/tag/{tag}")
async def delete_tag(
    repo_type: str,
    namespace: str,
    name: str,
    tag: str,
    user: User = Depends(get_current_user),
):
    """Delete a tag.

    Args:
        repo_type: Repository type (model/dataset/space)
        namespace: Repository namespace
        name: Repository name
        tag: Tag name to delete
        user: Current authenticated user

    Returns:
        Success message
    """
    repo_id = f"{namespace}/{name}"

    # Check if repository exists
    repo_row = await get_repository(repo_type, namespace, name)

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check if user has permission
    check_repo_delete_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)
    client = get_lakefs_client()

    try:
        await client.delete_tag(repository=lakefs_repo, tag=tag)
    except Exception as e:
        return hf_server_error(f"Failed to delete tag: {str(e)}")

    return {"success": True, "message": f"Tag '{tag}' deleted"}
