"""Basic repository management API endpoints."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from lakefs_client.models import RepositoryCreation
from pydantic import BaseModel

from ..config import cfg
from ..db import Repository, init_db
from .auth import get_current_user
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
def create_repo(payload: CreateRepoPayload, user=Depends(get_current_user)):
    """Create a new repository.

    Args:
        payload: Repository creation parameters
        user: Current authenticated user

    Returns:
        Created repository information

    Raises:
        HTTPException: If LakeFS repository creation fails
    """
    namespace = payload.organization or user.username
    full_id = f"{namespace}/{payload.name}"
    lakefs_repo = lakefs_repo_name(payload.type, full_id)

    if Repository.get_or_none(
        (Repository.full_id == full_id) & (Repository.repo_type == payload.type)
    ):
        raise HTTPException(400, detail={"error": "Repository already exists"})

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
        raise HTTPException(
            status_code=500,
            detail={"error": f"LakeFS repository creation failed: {str(e)}"},
        )

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


@router.get("/{repo_type}s/{repo_id:path}/tree/{revision}{path:path}")
def list_repo_tree(
    repo_type: RepoType,
    repo_id: str,
    revision: str = "main",
    path: str = "",
    recursive: bool = True,
    expand: bool = False,
):
    """List repository file tree.

    Args:
        repo_type: Type of repository
        repo_id: Full repository ID (namespace/name)
        revision: Branch name or commit hash
        path: Path within repository
        recursive: List recursively
        expand: Include detailed metadata

    Returns:
        File tree structure

    Raises:
        HTTPException: If listing fails
    """
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
        # Return empty tree for non-existent paths
        if "404" in str(e):
            return {
                "sha": None,
                "truncated": False,
                "tree": [],
                "commit": {"oid": None, "date": None},
            }
        raise HTTPException(
            status_code=500, detail={"error": f"Failed to list objects: {e}"}
        )

    # Convert LakeFS objects to HuggingFace format
    tree = []
    for obj in result.results:
        if obj.path_type == "object":
            tree.append(
                {
                    "path": obj.path,
                    "type": "blob",
                    "size": obj.size_bytes,
                    "oid": obj.checksum,
                    "lfs": obj.size_bytes > cfg.app.lfs_threshold_bytes,
                    "lastCommit": {
                        "id": obj.checksum,
                        "date": obj.mtime.isoformat() if obj.mtime else None,
                    },
                }
            )
        elif obj.path_type == "common_prefix":
            tree.append(
                {
                    "path": obj.path,
                    "type": "tree",
                }
            )

    return {
        "sha": None,  # Could fetch from commit info
        "truncated": result.pagination.has_more if result.pagination else False,
        "tree": tree,
        "commit": {"oid": None, "date": None},
    }


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

    Raises:
        HTTPException: If invalid route
    """
    path = request.url.path
    if "models" in path:
        rt = "model"
    elif "datasets" in path:
        rt = "dataset"
    elif "spaces" in path:
        rt = "space"
    else:
        raise HTTPException(404, detail={"error": "Unknown repository type"})

    # Query database
    q = Repository.select().where(Repository.repo_type == rt)
    if author:
        q = q.where(Repository.namespace == author)
    rows = q.limit(limit)

    # Format response
    return [
        {
            "id": r.full_id,
            "author": r.namespace,
            "private": r.private,
            "sha": None,  # Could fetch from LakeFS
            "lastModified": None,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "downloads": 0,
            "likes": 0,
            "gated": False,
            "tags": [],
        }
        for r in rows
    ]
