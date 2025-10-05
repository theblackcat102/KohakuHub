"""Commit history API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from kohakuhub.api.utils.hf import hf_repo_not_found, hf_server_error
from kohakuhub.api.utils.lakefs import get_lakefs_client, lakefs_repo_name
from kohakuhub.async_utils import get_async_lakefs_client, run_in_executor
from kohakuhub.auth.dependencies import get_optional_user
from kohakuhub.auth.permissions import check_repo_read_permission
from kohakuhub.db import Repository, User
from kohakuhub.logger import get_logger

logger = get_logger("COMMITS")
router = APIRouter()


@router.get("/{repo_type}s/{namespace}/{name}/commits/{branch}")
async def list_commits(
    repo_type: str,
    namespace: str,
    name: str,
    branch: str = "main",
    limit: int = Query(20, ge=1, le=100),
    after: Optional[str] = None,
    user: User = Depends(get_optional_user),
):
    """List commits for a repository branch.

    Args:
        repo_type: Repository type (model/dataset/space)
        namespace: Repository namespace
        name: Repository name
        branch: Branch name (default: main)
        limit: Number of commits to return (max 100)
        after: Pagination cursor (commit ID to start after)
        user: Current authenticated user (optional)

    Returns:
        List of commits with metadata
    """
    repo_id = f"{namespace}/{name}"

    # Check if repository exists
    repo_row = Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type)
    )

    if not repo_row:
        return hf_repo_not_found(repo_id, repo_type)

    # Check read permission
    check_repo_read_permission(repo_row, user)

    lakefs_repo = lakefs_repo_name(repo_type, repo_id)

    try:
        # Get commits from LakeFS using refs.log_commits
        client = get_lakefs_client()

        logger.debug(
            f"Fetching commits for {lakefs_repo}/{branch}, limit={limit}, after={after}"
        )

        # Call log_commits with proper keyword arguments
        kwargs = {
            "amount": limit,
        }
        if after:
            kwargs["after"] = after

        log_result = await run_in_executor(
            client.refs.log_commits,
            lakefs_repo,  # repository (positional)
            branch,  # ref (positional)
            **kwargs,  # amount, after (keyword)
        )

        logger.debug(
            f"Got {len(log_result.results) if log_result and log_result.results else 0} commits"
        )

        # Format commits for HuggingFace Hub compatibility
        commits = []

        if not log_result or not log_result.results:
            logger.warning(f"No commits found for {lakefs_repo}/{branch}")
            return {
                "commits": [],
                "hasMore": False,
                "nextCursor": None,
            }

        for commit in log_result.results:
            try:
                commits.append(
                    {
                        "id": commit.id,
                        "oid": commit.id,
                        "title": commit.message,
                        "message": commit.message,
                        "date": commit.creation_date,
                        "author": commit.committer or "unknown",
                        "email": (
                            commit.metadata.get("email", "") if commit.metadata else ""
                        ),
                        "parents": commit.parents or [],
                    }
                )
            except Exception as ex:
                logger.warning(f"Failed to parse commit {commit.id}: {str(ex)}")
                continue

        response = {
            "commits": commits,
            "hasMore": (
                log_result.pagination.has_more if log_result.pagination else False
            ),
            "nextCursor": (
                log_result.pagination.next_offset
                if (log_result.pagination and log_result.pagination.has_more)
                else None
            ),
        }

        logger.success(f"Returned {len(commits)} commits for {repo_id}/{branch}")
        return response

    except Exception as e:
        logger.exception(f"Failed to list commits for {repo_id}/{branch}", e)
        return hf_server_error(f"Failed to list commits: {str(e)}")
