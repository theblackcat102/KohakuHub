"""Repository CRUD operations (create, delete, move)."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends
from lakefs_client.models import RepositoryCreation
from pydantic import BaseModel

from kohakuhub.api.utils.hf import (
    HFErrorCode,
    hf_error_response,
    hf_repo_not_found,
    hf_server_error,
    is_lakefs_not_found_error,
)
from kohakuhub.api.utils.lakefs import get_lakefs_client, lakefs_repo_name
from kohakuhub.auth.dependencies import get_current_user
from kohakuhub.auth.permissions import (
    check_namespace_permission,
    check_repo_delete_permission,
)
from kohakuhub.config import cfg
from kohakuhub.db_async import execute_db_query, get_repository
from kohakuhub.db import File, Repository, StagingUpload, User, init_db
from kohakuhub.logger import get_logger

logger = get_logger("REPO")
router = APIRouter()
init_db()

RepoType = Literal["model", "dataset", "space"]


class CreateRepoPayload(BaseModel):
    """Payload for repository creation."""

    type: RepoType = "model"
    name: str
    organization: Optional[str] = None
    private: bool = False
    sdk: Optional[str] = None


@router.post("/repos/create")
async def create_repo(payload: CreateRepoPayload, user: User = Depends(get_current_user)):
    """Create a new repository.

    Args:
        payload: Repository creation parameters
        user: Current authenticated user

    Returns:
        Created repository information
    """
    logger.info(
        f"Creating repository: {payload.organization or user.username}/{payload.name}"
    )
    namespace = payload.organization or user.username

    # Check if user has permission to use this namespace
    check_namespace_permission(namespace, user)

    full_id = f"{namespace}/{payload.name}"
    lakefs_repo = lakefs_repo_name(payload.type, full_id)

    existing_repo = await get_repository(payload.type, namespace, payload.name)
    if existing_repo:
        return hf_error_response(
            400,
            HFErrorCode.REPO_EXISTS,
            f"Repository {full_id} already exists",
        )

    # Create LakeFS repository
    client = get_lakefs_client()
    storage_namespace = f"s3://{cfg.s3.bucket}/{lakefs_repo}"

    try:
        client.repositories.create_repository(
            repository_creation=RepositoryCreation(
                name=lakefs_repo,
                storage_namespace=storage_namespace,
                default_branch="main",
            )
        )
    except Exception as e:
        logger.exception(f"LakeFS repository creation failed for {full_id}", e)
        return hf_server_error(f"LakeFS repository creation failed: {str(e)}")

    # Store in database for listing/metadata
    def _create_repo():
        Repository.get_or_create(
            repo_type=payload.type,
            namespace=namespace,
            name=payload.name,
            full_id=full_id,
            defaults={"private": payload.private, "owner_id": user.id},
        )

    await execute_db_query(_create_repo)

    return {
        "url": f"{cfg.app.base_url}/{payload.type}s/{full_id}",
        "repo_id": full_id,
    }


class DeleteRepoPayload(BaseModel):
    """Payload for repository deletion."""

    type: RepoType = "model"
    name: str
    organization: Optional[str] = None
    sdk: Optional[str] = None


@router.delete("/repos/delete")
async def delete_repo(
    payload: DeleteRepoPayload,
    user: User = Depends(get_current_user),
):
    """Delete a repository. (NOTE: This is IRREVERSIBLE)

    Args:
        name: Repository name.
        organization: Organization name (optional, defaults to user namespace).
        type: Repository type.
        user: Current authenticated user.

    Returns:
        Success message or error response.
    """
    repo_type = payload.type
    namespace = payload.organization or user.username
    full_id = f"{namespace}/{payload.name}"
    lakefs_repo = lakefs_repo_name(repo_type, full_id)

    # 1. Check if repository exists in database
    repo_row = await get_repository(repo_type, namespace, payload.name)

    if not repo_row:
        # NOTE: HuggingFace client expects 400 for delete repo not found
        # but 404 for getting repo not found. Use 400 with RepoNotFound code.
        return hf_repo_not_found(full_id, repo_type)

    # 2. Check if user has permission to delete this repository
    check_repo_delete_permission(repo_row, user)

    # 2. Delete LakeFS repository
    client = get_lakefs_client()
    try:
        # Note: Deleting a LakeFS repo is generally fast as it only deletes metadata
        client.repositories.delete_repository(repository=lakefs_repo)
        logger.success(f"Successfully deleted LakeFS repository: {lakefs_repo}")
    except Exception as e:
        # LakeFS returns 404 if repo doesn't exist, which is fine
        if not is_lakefs_not_found_error(e):
            # If LakeFS deletion fails for other reasons, fail the whole operation
            logger.exception(f"LakeFS repository deletion failed for {lakefs_repo}", e)
            return hf_server_error(f"LakeFS repository deletion failed: {str(e)}")
        logger.info(f"LakeFS repository {lakefs_repo} not found/already deleted (OK)")

    # 3. Delete related metadata from database (manual cascade)
    def _delete_db_records():
        try:
            # Delete related file records first
            File.delete().where(File.repo_full_id == full_id).execute()
            StagingUpload.delete().where(StagingUpload.repo_full_id == full_id).execute()
            repo_row.delete_instance()
            logger.success(f"Successfully deleted database records for: {full_id}")
        except Exception as e:
            logger.exception(f"Database deletion failed for {full_id}", e)
            raise

    try:
        await execute_db_query(_delete_db_records)
    except Exception as e:
        return hf_server_error(f"Database deletion failed for {full_id}: {str(e)}")

    # 4. Return success response (200 OK with a simple message)
    # HuggingFace Hub delete_repo returns a simple 200 OK.
    return {"message": f"Repository '{full_id}' of type '{repo_type}' deleted."}


class MoveRepoPayload(BaseModel):
    """Payload for repository move/rename."""

    fromRepo: str  # format: "namespace/repo-name"
    toRepo: str  # format: "namespace/repo-name"
    type: str = "model"


@router.post("/repos/move")
async def move_repo(
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
    from_parts = from_id.split("/", 1)
    if len(from_parts) != 2:
        return hf_error_response(400, HFErrorCode.INVALID_REPO_ID, "Invalid source repository ID")

    from_namespace, from_name = from_parts
    repo_row = await get_repository(repo_type, from_namespace, from_name)

    if not repo_row:
        return hf_repo_not_found(from_id, repo_type)

    # Check if user has permission to move this repository
    check_repo_delete_permission(repo_row, user)

    # Check if destination already exists
    to_parts = to_id.split("/", 1)
    if len(to_parts) != 2:
        return hf_error_response(400, HFErrorCode.INVALID_REPO_ID, "Invalid destination repository ID")

    to_namespace, to_name = to_parts
    existing = await get_repository(repo_type, to_namespace, to_name)
    if existing:
        return hf_error_response(
            400,
            HFErrorCode.REPO_EXISTS,
            f"Repository {to_id} already exists",
        )

    # Check if user has permission to use destination namespace
    check_namespace_permission(to_namespace, user)

    # Update database records
    def _update_db_records():
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

    await execute_db_query(_update_db_records)

    # Note: LakeFS repository rename not implemented yet
    # Would require creating new LakeFS repo and migrating data

    return {
        "success": True,
        "url": f"{cfg.app.base_url}/{repo_type}s/{to_id}",
        "message": f"Repository moved from {from_id} to {to_id}",
    }
