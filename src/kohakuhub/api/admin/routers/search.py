"""Global search endpoints for admin API."""

from fastapi import APIRouter, Depends, Query

from kohakuhub.db import Commit, Repository, User
from kohakuhub.logger import get_logger
from kohakuhub.api.admin.utils import verify_admin_token

logger = get_logger("ADMIN")
router = APIRouter()


@router.get("/search")
async def global_search(
    q: str,
    types: list[str] = Query(default=["users", "repos", "commits"]),
    limit: int = 20,
    _admin: bool = Depends(verify_admin_token),
):
    """Global search across users, repositories, and commits.

    Args:
        q: Search query string
        types: Types to search (users, repos, commits)
        limit: Maximum results per type
        _admin: Admin authentication (dependency)

    Returns:
        Grouped search results by type
    """
    results = {"users": [], "repositories": [], "commits": []}

    # Search users
    if "users" in types:
        users_query = (
            User.select()
            .where(
                ((User.username.contains(q)) | (User.email.contains(q)))
                & (User.is_org == False)
            )
            .limit(limit)
        )

        results["users"] = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "email_verified": u.email_verified,
                "is_active": u.is_active,
            }
            for u in users_query
        ]

    # Search repositories
    if "repos" in types or "repositories" in types:
        repos_query = (
            Repository.select()
            .where((Repository.full_id.contains(q)) | (Repository.name.contains(q)))
            .limit(limit)
        )

        results["repositories"] = [
            {
                "id": r.id,
                "full_id": r.full_id,
                "repo_type": r.repo_type,
                "namespace": r.namespace,
                "name": r.name,
                "private": r.private,
                "owner_username": r.owner.username if r.owner else "unknown",
            }
            for r in repos_query
        ]

    # Search commits
    if "commits" in types:
        commits_query = (
            Commit.select()
            .where((Commit.message.contains(q)) | (Commit.username.contains(q)))
            .limit(limit)
        )

        results["commits"] = [
            {
                "id": c.id,
                "commit_id": c.commit_id,
                "message": c.message,
                "username": c.username,
                "repo_full_id": c.repository.full_id if c.repository else None,
                "repo_type": c.repo_type,
                "branch": c.branch,
                "created_at": c.created_at.isoformat(),
            }
            for c in commits_query
        ]

    return {
        "query": q,
        "results": results,
        "result_counts": {
            "users": len(results["users"]),
            "repositories": len(results["repositories"]),
            "commits": len(results["commits"]),
        },
    }
