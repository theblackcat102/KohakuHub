"""Fallback operations for different endpoint types."""

import asyncio
from typing import Optional

import httpx
from fastapi.responses import RedirectResponse, Response

from kohakuhub.config import cfg
from kohakuhub.logger import get_logger
from kohakuhub.api.fallback.cache import get_cache
from kohakuhub.api.fallback.client import FallbackClient
from kohakuhub.api.fallback.config import get_enabled_sources
from kohakuhub.api.fallback.utils import (
    add_source_headers,
    extract_error_message,
    is_not_found_error,
    should_retry_source,
)

logger = get_logger("FALLBACK_OPS")


async def try_fallback_resolve(
    repo_type: str,
    namespace: str,
    name: str,
    revision: str,
    path: str,
) -> Optional[Response]:
    """Try to resolve file from fallback sources.

    Args:
        repo_type: "model", "dataset", or "space"
        namespace: Repository namespace
        name: Repository name
        revision: Branch or commit
        path: File path in repository

    Returns:
        RedirectResponse to external URL or None if not found
    """
    cache = get_cache()
    sources = get_enabled_sources(namespace)

    if not sources:
        logger.debug(f"No fallback sources configured for {namespace}")
        return None

    # Check cache first
    cached = cache.get(repo_type, namespace, name)
    if cached and cached.get("exists"):
        # Cache hit - try this source first
        source_url = cached["source_url"]
        source_name = cached["source_name"]
        source_type = cached["source_type"]

        # Find source config by URL
        source_config = next((s for s in sources if s["url"] == source_url), None)
        if source_config:
            sources = [source_config] + [s for s in sources if s["url"] != source_url]
            logger.debug(
                f"Cache hit: trying {source_name} first for {namespace}/{name}"
            )

    # Construct KohakuHub path
    kohaku_path = f"/{repo_type}s/{namespace}/{name}/resolve/{revision}/{path}"

    # Try each source in priority order
    for source in sources:
        try:
            client = FallbackClient(
                source_url=source["url"],
                source_type=source["source_type"],
                token=source.get("token"),
            )

            # Make HEAD request to check if file exists
            response = await client.head(kohaku_path, repo_type)

            # Accept 2xx (success) or 3xx (redirect) as "file exists"
            # HuggingFace often returns 307 redirects to CDN
            if 200 <= response.status_code < 400:
                # File exists! Generate redirect URL
                external_url = client.map_url(kohaku_path, repo_type)

                logger.debug(
                    f"HEAD returned {response.status_code}, file exists at {source['name']}"
                )

                # Update cache
                cache.set(
                    repo_type,
                    namespace,
                    name,
                    source["url"],
                    source["name"],
                    source["source_type"],
                    exists=True,
                )

                logger.info(
                    f"Fallback SUCCESS: {repo_type}/{namespace}/{name} found in {source['name']}"
                )

                # Return redirect to external URL
                redirect_response = RedirectResponse(url=external_url, status_code=302)

                # Add source attribution headers
                for key, value in add_source_headers(
                    response, source["name"], source["url"]
                ).items():
                    redirect_response.headers[key] = value

                return redirect_response

            elif not should_retry_source(response):
                # Don't try more sources on auth/permission errors
                logger.warning(
                    f"Fallback stopped at {source['name']}: {response.status_code}"
                )
                return None

        except httpx.TimeoutException:
            logger.warning(f"Fallback source {source['name']} timed out")
            continue

        except Exception as e:
            logger.warning(f"Fallback source {source['name']} failed: {e}")
            continue

    # Not found in any source
    logger.debug(
        f"Fallback MISS: {repo_type}/{namespace}/{name} not found in any source"
    )
    return None


async def try_fallback_info(
    repo_type: str,
    namespace: str,
    name: str,
) -> Optional[dict]:
    """Try to get repository info from fallback sources.

    Args:
        repo_type: "model", "dataset", or "space"
        namespace: Repository namespace
        name: Repository name

    Returns:
        Repository info dict or None if not found
    """
    cache = get_cache()
    sources = get_enabled_sources(namespace)

    if not sources:
        return None

    # Check cache first
    cached = cache.get(repo_type, namespace, name)
    if cached and cached.get("exists"):
        source_url = cached["source_url"]
        source_config = next((s for s in sources if s["url"] == source_url), None)
        if source_config:
            sources = [source_config] + [s for s in sources if s["url"] != source_url]

    # Construct API path
    kohaku_path = f"/api/{repo_type}s/{namespace}/{name}"

    # Try each source
    for source in sources:
        try:
            client = FallbackClient(
                source_url=source["url"],
                source_type=source["source_type"],
                token=source.get("token"),
            )

            response = await client.get(kohaku_path, repo_type)

            if response.status_code == 200:
                data = response.json()

                # Add source tag
                data["_source"] = source["name"]
                data["_source_url"] = source["url"]

                # Update cache
                cache.set(
                    repo_type,
                    namespace,
                    name,
                    source["url"],
                    source["name"],
                    source["source_type"],
                    exists=True,
                )

                logger.info(
                    f"Fallback info SUCCESS: {repo_type}/{namespace}/{name} from {source['name']}"
                )
                return data

            elif not should_retry_source(response):
                return None

        except Exception as e:
            logger.warning(f"Fallback info failed for {source['name']}: {e}")
            continue

    return None


async def try_fallback_tree(
    repo_type: str,
    namespace: str,
    name: str,
    revision: str,
    path: str = "",
) -> Optional[list]:
    """Try to get repository tree from fallback sources.

    Args:
        repo_type: "model", "dataset", or "space"
        namespace: Repository namespace
        name: Repository name
        revision: Branch or commit
        path: Path within repository

    Returns:
        List of file/folder objects or None if not found
    """
    sources = get_enabled_sources(namespace)

    if not sources:
        return None

    # Construct API path
    kohaku_path = f"/api/{repo_type}s/{namespace}/{name}/tree/{revision}{path}"

    # Try each source
    for source in sources:
        try:
            client = FallbackClient(
                source_url=source["url"],
                source_type=source["source_type"],
                token=source.get("token"),
            )

            response = await client.get(kohaku_path, repo_type)

            if response.status_code == 200:
                data = response.json()

                logger.info(
                    f"Fallback tree SUCCESS: {repo_type}/{namespace}/{name}/tree from {source['name']}"
                )
                return data

            elif not should_retry_source(response):
                return None

        except Exception as e:
            logger.warning(f"Fallback tree failed for {source['name']}: {e}")
            continue

    return None


async def fetch_external_list(
    source: dict, repo_type: str, query_params: dict
) -> list[dict]:
    """Fetch repository list from external source.

    Args:
        source: Source config dict
        repo_type: "model", "dataset", or "space"
        query_params: Query parameters (author, limit, sort, etc.)

    Returns:
        List of repository dicts with _source and _source_url added
    """
    try:
        # Construct API path
        kohaku_path = f"/api/{repo_type}s"

        # Build query string
        params = {}
        if query_params.get("author"):
            params["author"] = query_params["author"]
        if query_params.get("limit"):
            params["limit"] = query_params["limit"]
        if query_params.get("sort"):
            params["sort"] = query_params["sort"]

        client = FallbackClient(
            source_url=source["url"],
            source_type=source["source_type"],
            token=source.get("token"),
        )

        # Make request with query params
        external_url = client.map_url(kohaku_path, repo_type)

        async with httpx.AsyncClient(timeout=client.timeout) as http_client:
            response = await http_client.get(external_url, params=params)

        if response.status_code == 200:
            results = response.json()

            # Add source tags to each item
            if isinstance(results, list):
                for item in results:
                    item["_source"] = source["name"]
                    item["_source_url"] = source["url"]

                logger.info(
                    f"Fetched {len(results)} {repo_type}s from {source['name']}"
                )
                return results

        logger.warning(
            f"Failed to fetch list from {source['name']}: {response.status_code}"
        )
        return []

    except Exception as e:
        logger.warning(f"Failed to fetch list from {source['name']}: {e}")
        return []
