"""Basic repository management API endpoints."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from lakefs_client.models import RepositoryCreation
from pydantic import BaseModel

from ..config import cfg
from ..db import Repository, init_db, File, StagingUpload, User
from .auth import get_current_user
from .hf_utils import (
    HFErrorCode,
    hf_error_response,
    hf_repo_not_found,
    hf_bad_request,
    hf_server_error,
    format_hf_datetime,
    is_lakefs_not_found_error,
    is_lakefs_revision_error,
)
from .lakefs_utils import get_lakefs_client, lakefs_repo_name

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
def create_repo(payload: CreateRepoPayload, user: User = Depends(get_current_user)):
    """Create a new repository.

    Args:
        payload: Repository creation parameters
        user: Current authenticated user

    Returns:
        Created repository information
    """
    namespace = payload.organization or user.username
    full_id = f"{namespace}/{payload.name}"
    lakefs_repo = lakefs_repo_name(payload.type, full_id)

    if Repository.get_or_none(
        (Repository.full_id == full_id) & (Repository.repo_type == payload.type)
    ):
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
        return hf_server_error(f"LakeFS repository creation failed: {str(e)}")

    # Store in database for listing/metadata
    Repository.get_or_create(
        repo_type=payload.type,
        namespace=namespace,
        name=payload.name,
        full_id=full_id,
        defaults={"private": payload.private},
    )

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
    repo_row = Repository.get_or_none(
        (Repository.full_id == full_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        # NOTE: HuggingFace client expects 400 for delete repo not found
        # but 404 for getting repo not found. Use 400 with RepoNotFound code.
        return hf_repo_not_found(full_id, repo_type)

    # 2. Delete LakeFS repository
    client = get_lakefs_client()
    try:
        # Note: Deleting a LakeFS repo is generally fast as it only deletes metadata
        client.repositories.delete_repository(repository=lakefs_repo)
        print(f"Successfully deleted LakeFS repository: {lakefs_repo}")
    except Exception as e:
        # LakeFS returns 404 if repo doesn't exist, which is fine
        if not is_lakefs_not_found_error(e):
            # If LakeFS deletion fails for other reasons, fail the whole operation
            return hf_server_error(f"LakeFS repository deletion failed: {str(e)}")
        print(f"LakeFS repository {lakefs_repo} not found/already deleted (OK)")

    # 3. Delete related metadata from database (manual cascade)
    try:
        # Delete related file records first
        File.delete().where(File.repo_full_id == full_id).execute()
        StagingUpload.delete().where(StagingUpload.repo_full_id == full_id).execute()
        repo_row.delete_instance()
        print(f"Successfully deleted database records for: {full_id}")
    except Exception as e:
        return hf_server_error(f"Database deletion failed for {full_id}: {str(e)}")

    # 4. Return success response (200 OK with a simple message)
    # HuggingFace Hub delete_repo returns a simple 200 OK.
    return {"message": f"Repository '{full_id}' of type '{repo_type}' deleted."}


@router.get("/models/{namespace}/{repo_name}")
@router.get("/datasets/{namespace}/{repo_name}")
@router.get("/spaces/{namespace}/{repo_name}")
def get_repo_info(namespace: str, repo_name: str, request: Request):
    """Get repository information (without revision).

    This endpoint matches HuggingFace Hub API format:
    - /api/models/{namespace}/{repo_name}
    - /api/datasets/{namespace}/{repo_name}
    - /api/spaces/{namespace}/{repo_name}

    Note: For revision-specific info, use /{repo_type}s/{namespace}/{repo_name}/revision/{revision}
          which is handled in file.py

    Args:
        namespace: Repository namespace (user or organization)
        repo_name: Repository name
        request: FastAPI request object

    Returns:
        Repository metadata or error response with headers
    """
    # Construct full repo ID
    repo_id = f"{namespace}/{repo_name}"

    # Determine repo type from path
    path = request.url.path
    if "/models/" in path:
        repo_type = "model"
    elif "/datasets/" in path:
        repo_type = "dataset"
    elif "/spaces/" in path:
        repo_type = "space"
    else:
        return hf_error_response(
            404,
            HFErrorCode.INVALID_REPO_TYPE,
            "Invalid repository type",
        )

    # Check if repository exists in database
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Get LakeFS info for default branch
    lakefs_repo = lakefs_repo_name(repo_type, repo_id)
    client = get_lakefs_client()

    # Get default branch info
    commit_id = None
    last_modified = None

    try:
        branch = client.branches.get_branch(repository=lakefs_repo, branch="main")
        commit_id = branch.commit_id

        # Get commit details if available
        if commit_id:
            try:
                commit_info = client.commits.get_commit(
                    repository=lakefs_repo, commit_id=commit_id
                )
                if commit_info and commit_info.creation_date:
                    from datetime import datetime

                    last_modified = datetime.fromtimestamp(
                        commit_info.creation_date
                    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            except Exception:
                pass
    except Exception as e:
        # Log warning but continue - repo exists even if LakeFS has issues
        print(f"Warning: Could not get branch info for {lakefs_repo}/main: {e}")

    # Format created_at
    created_at = format_hf_datetime(repo_row.created_at)

    # Return repository info in HuggingFace format
    return {
        "_id": repo_row.id,
        "id": repo_id,
        "modelId": repo_id if repo_type == "model" else None,
        "author": repo_row.namespace,
        "sha": commit_id,
        "lastModified": last_modified,
        "createdAt": created_at,
        "private": repo_row.private,
        "disabled": False,
        "gated": False,
        "downloads": 0,
        "likes": 0,
        "tags": [],
        "pipeline_tag": None,
        "library_name": None,
        "siblings": [],
        "spaces": [],
        "models": [],
        "datasets": [],
    }


# NOTE: /{repo_type}s/{namespace}/{repo_name}/revision/{revision} is handled in file.py
# to avoid duplication


@router.get("/{repo_type}s/{namespace}/{repo_name}/tree/{revision}{path:path}")
def list_repo_tree(
    repo_type: RepoType,
    namespace: str,
    repo_name: str,
    revision: str = "main",
    path: str = "",
    recursive: bool = False,
    expand: bool = False,
):
    """List repository file tree.

    Returns a flat list of files and folders in HuggingFace format.

    Response format matches HuggingFace API:
    [
        {
            "type": "file",  # or "directory"
            "oid": "sha256_hash",
            "size": 1234,
            "path": "relative/path/to/file.txt",
            "lfs": {"oid": "...", "size": ..., "pointerSize": ...}  # if LFS file
        },
        ...
    ]

    Args:
        repo_type: Type of repository
        namespace: Repository namespace
        repo_name: Repository name
        revision: Branch name or commit hash (default: "main")
        path: Path within repository (default: root)
        recursive: List recursively (default: False)
        expand: Include detailed metadata (default: False)

    Returns:
        Flat list of file/folder objects
    """
    # Construct full repo ID
    repo_id = f"{namespace}/{repo_name}"

    # Check if repository exists
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)
    client = get_lakefs_client()

    # Clean path
    prefix = path.lstrip("/") if path and path != "/" else ""

    try:
        # List objects from LakeFS
        result = client.objects.list_objects(
            repository=lakefs_repo,
            ref=revision,
            prefix=prefix,
            delimiter="" if recursive else "/",
        )
    except Exception as e:
        # Check for specific error types
        if is_lakefs_not_found_error(e):
            if is_lakefs_revision_error(e):
                from .hf_utils import hf_revision_not_found

                return hf_revision_not_found(repo_id, revision)
            else:
                # Return empty list for non-existent paths
                return []

        # Other errors are server errors
        return hf_server_error(f"Failed to list objects: {str(e)}")

    # Convert LakeFS objects to HuggingFace format (flat list)
    result_list = []

    for obj in result.results:
        if obj.path_type == "object":
            # File object
            is_lfs = obj.size_bytes > cfg.app.lfs_threshold_bytes

            file_obj = {
                "type": "file",
                "oid": obj.checksum,
                "size": obj.size_bytes,
                "path": obj.path,
            }

            # Add LFS metadata if it's an LFS file
            if is_lfs:
                file_obj["lfs"] = {
                    "oid": obj.checksum,  # Use checksum as LFS oid
                    "size": obj.size_bytes,
                    "pointerSize": 134,  # Standard Git LFS pointer size
                }

            result_list.append(file_obj)

        elif obj.path_type == "common_prefix":
            # Directory object
            result_list.append(
                {
                    "type": "directory",
                    "oid": (
                        obj.checksum
                        if hasattr(obj, "checksum") and obj.checksum
                        else ""
                    ),
                    "size": 0,
                    "path": obj.path.rstrip("/"),  # Remove trailing slash
                }
            )

    return result_list


@router.get("/models")
@router.get("/datasets")
@router.get("/spaces")
def list_repos(
    author: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    request: Request = None,
):
    """List repositories of a specific type.

    Args:
        author: Filter by author/namespace
        limit: Maximum number of results
        request: FastAPI request object

    Returns:
        List of repositories
    """
    path = request.url.path
    if "models" in path:
        rt = "model"
    elif "datasets" in path:
        rt = "dataset"
    elif "spaces" in path:
        rt = "space"
    else:
        return hf_error_response(
            404,
            HFErrorCode.INVALID_REPO_TYPE,
            "Unknown repository type",
        )

    # Query database
    q = Repository.select().where(Repository.repo_type == rt)
    # [TODO] User auth system with correct namespace system
    # if author:
    #     q = q.where(Repository.namespace == author)
    rows = q.limit(limit)

    # Format response
    return [
        {
            "id": r.full_id,
            "author": r.namespace,
            "private": r.private,
            "sha": None,
            "lastModified": None,
            "createdAt": (
                r.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if r.created_at else None
            ),
            "downloads": 0,
            "likes": 0,
            "gated": False,
            "tags": [],
        }
        for r in rows
    ]
