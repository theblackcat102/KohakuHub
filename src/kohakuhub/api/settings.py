"""User, organization, and repository settings API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from ..db import User, Organization, UserOrganization, Repository
from ..auth.dependencies import get_current_user
from ..auth.permissions import check_repo_delete_permission
from .auth import get_optional_user
from .lakefs_utils import get_lakefs_client, lakefs_repo_name
from .hf_utils import hf_error_response, HFErrorCode, hf_repo_not_found, hf_server_error

router = APIRouter()


# ============================================================================
# User Settings API
# ============================================================================
# Note: /whoami-v2 is implemented in api/utils.py


class UpdateUserSettingsRequest(BaseModel):
    email: Optional[EmailStr] = None
    fullname: Optional[str] = None


@router.put("/users/{username}/settings")
def update_user_settings(
    username: str,
    req: UpdateUserSettingsRequest,
    user: User = Depends(get_current_user),
):
    """Update user settings.

    Args:
        username: Username to update (must match authenticated user)
        req: Settings to update
        user: Current authenticated user

    Returns:
        Success message
    """
    # Verify user can only update their own settings
    if user.username != username:
        raise HTTPException(403, detail="Not authorized to update this user's settings")

    # Update fields if provided
    if req.email is not None:
        # Check if email is already taken by another user
        existing = User.get_or_none((User.email == req.email) & (User.id != user.id))
        if existing:
            raise HTTPException(400, detail="Email already in use")

        User.update(email=req.email, email_verified=False).where(
            User.id == user.id
        ).execute()
        # TODO: Send new verification email

    return {"success": True, "message": "User settings updated successfully"}


# ============================================================================
# Organization Settings API
# ============================================================================


class UpdateOrganizationSettingsRequest(BaseModel):
    description: Optional[str] = None


@router.put("/organizations/{org_name}/settings")
def update_organization_settings(
    org_name: str,
    req: UpdateOrganizationSettingsRequest,
    user: User = Depends(get_current_user),
):
    """Update organization settings.

    Args:
        org_name: Organization name
        req: Settings to update
        user: Current authenticated user

    Returns:
        Success message
    """
    org = Organization.get_or_none(Organization.name == org_name)
    if not org:
        raise HTTPException(404, detail="Organization not found")

    # Check if user is admin of the organization
    user_org = UserOrganization.get_or_none(
        (UserOrganization.user == user.id) & (UserOrganization.organization == org.id)
    )
    if not user_org or user_org.role not in ["admin", "super-admin"]:
        raise HTTPException(
            403, detail="Not authorized to update organization settings"
        )

    # Update fields if provided
    if req.description is not None:
        Organization.update(description=req.description).where(
            Organization.id == org.id
        ).execute()

    return {"success": True, "message": "Organization settings updated successfully"}


# ============================================================================
# Repository Settings API
# ============================================================================


class UpdateRepoSettingsPayload(BaseModel):
    """Payload for repository settings update."""

    private: Optional[bool] = None
    gated: Optional[str] = None  # "auto", "manual", or False/None


@router.put("/{repo_type}s/{namespace}/{name}/settings")
def update_repo_settings(
    repo_type: str,
    namespace: str,
    name: str,
    payload: UpdateRepoSettingsPayload,
    user: User = Depends(get_current_user),
):
    """Update repository settings.

    Matches pattern: PUT /api/{repo_type}s/{namespace}/{name}/settings

    Args:
        repo_type: Repository type (model/dataset/space)
        namespace: Repository namespace
        name: Repository name
        payload: Settings to update
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

    # Check if user has permission to update this repository
    check_repo_delete_permission(repo_row, user)

    # Update fields if provided
    if payload.private is not None:
        Repository.update(private=payload.private).where(
            Repository.id == repo_row.id
        ).execute()

    # Note: gated functionality not yet implemented in database schema
    # Would require adding a 'gated' field to Repository model

    return {"success": True, "message": "Repository settings updated successfully"}


class MoveRepoPayload(BaseModel):
    """Payload for repository move/rename."""

    fromRepo: str  # format: "namespace/repo-name"
    toRepo: str  # format: "namespace/repo-name"
    type: str = "model"


@router.post("/repos/move")
def move_repo(
    payload: MoveRepoPayload,
    user: User = Depends(get_current_user),
):
    """Move/rename a repository.

    Matches HuggingFace Hub API: POST /api/repos/move

    Args:
        payload: Move parameters
        user: Current authenticated user

    Returns:
        Success message with new URL
    """
    from_id = payload.fromRepo
    to_id = payload.toRepo
    repo_type = payload.type

    # Check if source repository exists
    repo_row = Repository.get_or_none(
        (Repository.full_id == from_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        return hf_repo_not_found(from_id, repo_type)

    # Check if user has permission to move this repository
    check_repo_delete_permission(repo_row, user)

    # Check if destination already exists
    existing = Repository.get_or_none(
        (Repository.full_id == to_id) & (Repository.repo_type == repo_type)
    )
    if existing:
        return hf_error_response(
            400,
            HFErrorCode.REPO_EXISTS,
            f"Repository {to_id} already exists",
        )

    # Parse destination namespace and name
    if "/" not in to_id:
        return hf_error_response(
            400,
            HFErrorCode.INVALID_REPO_ID,
            "Invalid repository ID format (must be namespace/name)",
        )

    to_namespace, to_name = to_id.split("/", 1)

    # Check if user has permission to use destination namespace
    from ..auth.permissions import check_namespace_permission

    check_namespace_permission(to_namespace, user)

    # Update database records
    from ..db import File, StagingUpload

    # Update repository record
    Repository.update(
        namespace=to_namespace,
        name=to_name,
        full_id=to_id,
    ).where(Repository.id == repo_row.id).execute()

    # Update related file records
    File.update(repo_full_id=to_id).where(File.repo_full_id == from_id).execute()

    # Update staging uploads
    StagingUpload.update(repo_full_id=to_id).where(
        StagingUpload.repo_full_id == from_id
    ).execute()

    # Note: LakeFS repository rename not implemented yet
    # Would require creating new LakeFS repo and migrating data

    from ..config import cfg

    return {
        "success": True,
        "url": f"{cfg.app.base_url}/{repo_type}s/{to_id}",
        "message": f"Repository moved from {from_id} to {to_id}",
    }


# ============================================================================
# Branch and Tag Management API
# ============================================================================


class CreateBranchPayload(BaseModel):
    """Payload for branch creation."""

    branch: str
    revision: Optional[str] = None  # Source revision (defaults to main)


@router.post("/{repo_type}s/{namespace}/{name}/branch")
def create_branch(
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
        source_branch = client.branches.get_branch(
            repository=lakefs_repo, branch=source_ref
        )
        source_commit = source_branch.commit_id

        # Create new branch
        client.branches.create_branch(
            repository=lakefs_repo,
            branch_creation={
                "name": payload.branch,
                "source": source_commit,
            },
        )
    except Exception as e:
        return hf_server_error(f"Failed to create branch: {str(e)}")

    return {"success": True, "message": f"Branch '{payload.branch}' created"}


@router.delete("/{repo_type}s/{namespace}/{name}/branch/{branch}")
def delete_branch(
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
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )

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
        client.branches.delete_branch(repository=lakefs_repo, branch=branch)
    except Exception as e:
        return hf_server_error(f"Failed to delete branch: {str(e)}")

    return {"success": True, "message": f"Branch '{branch}' deleted"}


class CreateTagPayload(BaseModel):
    """Payload for tag creation."""

    tag: str
    revision: Optional[str] = None  # Source revision (defaults to main)
    message: Optional[str] = None


@router.post("/{repo_type}s/{namespace}/{name}/tag")
def create_tag(
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
        source_branch = client.branches.get_branch(
            repository=lakefs_repo, branch=source_ref
        )
        source_commit = source_branch.commit_id

        # Create new tag
        client.tags.create_tag(
            repository=lakefs_repo,
            tag_creation={
                "id": payload.tag,
                "ref": source_commit,
            },
        )
    except Exception as e:
        return hf_server_error(f"Failed to create tag: {str(e)}")

    return {"success": True, "message": f"Tag '{payload.tag}' created"}


@router.delete("/{repo_type}s/{namespace}/{name}/tag/{tag}")
def delete_tag(
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
        client.tags.delete_tag(repository=lakefs_repo, tag=tag)
    except Exception as e:
        return hf_server_error(f"Failed to delete tag: {str(e)}")

    return {"success": True, "message": f"Tag '{tag}' deleted"}
