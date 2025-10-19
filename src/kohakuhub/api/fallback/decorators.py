"""Decorators for adding fallback functionality to endpoints."""

import asyncio
from functools import wraps
from typing import Literal

from fastapi import HTTPException
from fastapi.responses import Response

from kohakuhub.config import cfg
from kohakuhub.logger import get_logger
from kohakuhub.api.fallback.operations import (
    fetch_external_list,
    try_fallback_info,
    try_fallback_resolve,
    try_fallback_tree,
    try_fallback_user_profile,
    try_fallback_user_repos,
)
from kohakuhub.api.fallback.config import get_enabled_sources

logger = get_logger("FALLBACK_DEC")

OperationType = Literal["resolve", "tree", "info", "revision", "paths_info"]
UserOperationType = Literal["profile", "repos"]


def with_repo_fallback(operation: OperationType):
    """Decorator for endpoints that access individual repositories.

    Falls back to external sources if repository/file not found locally.

    Args:
        operation: Type of operation ("resolve", "tree", "info", "revision", "paths_info")

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if fallback is enabled
            if not cfg.fallback.enabled:
                return await func(*args, **kwargs)

            # Extract repo info from kwargs
            # Handle both "repo_type" (API endpoints) and "type" (public endpoints)
            repo_type = kwargs.get("repo_type") or kwargs.get("type")

            # If repo_type not in kwargs, try to parse from request path
            if not repo_type and "request" in kwargs:
                request = kwargs["request"]
                path = request.url.path
                logger.debug(f"Parsing repo_type from path: {path}")
                match path:
                    case _ if "/models/" in path:
                        repo_type = "model"
                    case _ if "/datasets/" in path:
                        repo_type = "dataset"
                    case _ if "/spaces/" in path:
                        repo_type = "space"
                    case _:
                        repo_type = "model"  # Default fallback
                logger.debug(f"Detected repo_type from path: {repo_type}")

            # Final fallback to "model" if still not determined
            if not repo_type:
                logger.debug("No repo_type found, defaulting to 'model'")
                repo_type = "model"

            namespace = kwargs.get("namespace")
            name = kwargs.get("name") or kwargs.get("repo_name")

            logger.debug(
                f"Fallback decorator params: repo_type={repo_type}, namespace={namespace}, name={name}"
            )

            if not namespace or not name:
                # Can't determine repo, skip fallback
                return await func(*args, **kwargs)

            is_404 = False
            original_error = None
            original_response = None

            try:
                # Try local first
                local_result = await func(*args, **kwargs)

                # Check if result is a 404 Response (any FastAPI response type)
                if (
                    isinstance(local_result, Response)
                    and getattr(local_result, "status_code", 200) == 404
                ):
                    is_404 = True
                    original_response = local_result
                    logger.info(
                        f"Local 404 response for {repo_type}/{namespace}/{name}, trying fallback sources..."
                    )
                else:
                    return local_result

            except HTTPException as e:
                # Only fallback on 404 errors
                if e.status_code != 404:
                    raise

                is_404 = True
                original_error = e
                logger.info(
                    f"Local 404 exception for {repo_type}/{namespace}/{name}, trying fallback sources..."
                )

            # If we got here, we have a 404 - try fallback
            if is_404:

                # Try fallback based on operation type
                match operation:
                    case "resolve":
                        revision = kwargs.get("revision", "main")
                        path = kwargs.get("path", "")
                        result = await try_fallback_resolve(
                            repo_type, namespace, name, revision, path
                        )

                    case "tree":
                        revision = kwargs.get("revision", "main")
                        path = kwargs.get("path", "")
                        result = await try_fallback_tree(
                            repo_type, namespace, name, revision, path
                        )

                    case "info" | "revision":
                        result = await try_fallback_info(repo_type, namespace, name)

                    case "paths_info":
                        # For paths-info, try to get info first
                        result = await try_fallback_info(repo_type, namespace, name)

                    case _:
                        logger.warning(f"Unknown fallback operation: {operation}")
                        result = None

                if result:
                    logger.success(
                        f"Fallback SUCCESS for {operation}: {repo_type}/{namespace}/{name}"
                    )
                    return result
                else:
                    # Not found in any source
                    logger.debug(
                        f"Fallback MISS for {operation}: {repo_type}/{namespace}/{name}"
                    )
                    # Return original 404 response or raise original exception
                    if original_error:
                        raise original_error
                    else:
                        # Return the original 404 JSONResponse
                        return original_response

        return wrapper

    return decorator


def with_list_aggregation(repo_type: str):
    """Decorator for list endpoints.

    Merges results from local + external sources.

    Args:
        repo_type: "model", "dataset", or "space"

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if fallback is enabled
            if not cfg.fallback.enabled:
                return await func(*args, **kwargs)

            # Get local results
            local_results = await func(*args, **kwargs)

            # Ensure results is a list
            if not isinstance(local_results, list):
                return local_results

            # Add source tag to local results
            for item in local_results:
                if isinstance(item, dict):
                    item["_source"] = "local"
                    item["_source_url"] = cfg.app.base_url

            # Get author from kwargs or args
            # Functions are called as: _list_models_with_aggregation(author, limit, sort, user)
            author = kwargs.get("author")
            if author is None and len(args) > 0:
                author = args[0]  # First positional arg is author

            # Build query params dict for external sources
            query_params = {
                "author": author,
                "limit": kwargs.get("limit", args[1] if len(args) > 1 else 50),
                "sort": kwargs.get("sort", args[2] if len(args) > 2 else "recent"),
            }

            sources = get_enabled_sources(namespace=author or "")

            if not sources:
                logger.debug("No fallback sources for list aggregation")
                return local_results

            # Fetch from external sources concurrently
            logger.info(
                f"Aggregating {repo_type} list from {len(sources)} external sources..."
            )

            external_tasks = [
                fetch_external_list(source, repo_type, query_params)
                for source in sources
            ]

            external_results_list = await asyncio.gather(
                *external_tasks, return_exceptions=True
            )

            # Merge results
            all_results = local_results.copy()
            seen_ids = {
                item.get("id")
                for item in local_results
                if isinstance(item, dict) and "id" in item
            }  # Local takes precedence

            for external_results in external_results_list:
                if isinstance(external_results, Exception):
                    logger.warning(f"External source failed: {external_results}")
                    continue

                if not isinstance(external_results, list):
                    continue

                for item in external_results:
                    if not isinstance(item, dict):
                        continue

                    item_id = item.get("id")
                    if item_id and item_id not in seen_ids:
                        all_results.append(item)
                        seen_ids.add(item_id)

            # Apply limit after merging
            limit = kwargs.get("limit", 50)
            final_results = all_results[:limit]

            logger.info(
                f"Aggregated {len(final_results)} {repo_type}s (local: {len(local_results)}, total: {len(all_results)})"
            )

            return final_results

        return wrapper

    return decorator


def with_user_fallback(operation: UserOperationType):
    """Decorator for user/org endpoints.

    Falls back to external sources if user/org not found locally.

    Args:
        operation: Type of operation ("profile", "repos")

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if fallback is enabled
            if not cfg.fallback.enabled:
                return await func(*args, **kwargs)

            # Extract username/org_name from kwargs
            username = kwargs.get("username") or kwargs.get("org_name")

            if not username:
                return await func(*args, **kwargs)

            is_404 = False
            original_error = None
            original_response = None

            try:
                # Try local first
                local_result = await func(*args, **kwargs)

                # Check if result is a 404 Response
                if (
                    isinstance(local_result, Response)
                    and getattr(local_result, "status_code", 200) == 404
                ):
                    is_404 = True
                    original_response = local_result
                    logger.info(
                        f"Local 404 response for user {username}, trying fallback sources..."
                    )
                else:
                    return local_result

            except HTTPException as e:
                # Only fallback on 404 errors
                if e.status_code != 404:
                    raise

                is_404 = True
                original_error = e
                logger.info(
                    f"Local 404 exception for user {username}, trying fallback sources..."
                )

            # If we got here, we have a 404 - try fallback
            if is_404:
                match operation:
                    case "profile":
                        result = await try_fallback_user_profile(username)

                    case "repos":
                        result = await try_fallback_user_repos(username)

                    case _:
                        logger.warning(f"Unknown user fallback operation: {operation}")
                        result = None

                if result:
                    logger.success(f"Fallback SUCCESS for user {operation}: {username}")
                    return result
                else:
                    # Not found in any source
                    logger.debug(f"Fallback MISS for user {operation}: {username}")
                    if original_error:
                        raise original_error
                    else:
                        return original_response

        return wrapper

    return decorator
