"""Load and manage fallback source configurations."""

from typing import Optional

from kohakuhub.config import cfg
from kohakuhub.db import FallbackSource
from kohakuhub.logger import get_logger

logger = get_logger("FALLBACK_CONFIG")


def get_enabled_sources(
    namespace: str = "", user_tokens: dict[str, str] | None = None
) -> list[dict]:
    """Get all enabled fallback sources for a namespace.

    Combines global sources (from config) and namespace-specific sources (from database).
    User tokens override admin tokens for matching URLs.
    Sources are ordered by priority (lower = higher priority).

    Args:
        namespace: User/org namespace, or "" for global only
        user_tokens: Dict of {url: token} from user (overrides admin tokens)

    Returns:
        List of source dicts with keys: url, token, priority, name, source_type, token_source
    """
    if not cfg.fallback.enabled:
        return []

    sources = []

    # 1. Load global sources from config (environment variables)
    for source_dict in cfg.fallback.sources:
        sources.append(
            {
                "url": source_dict.get("url", ""),
                "token": source_dict.get("token"),
                "priority": source_dict.get("priority", 100),
                "name": source_dict.get("name", "Unknown"),
                "source_type": source_dict.get("source_type", "huggingface"),
                "token_source": "admin",  # Track token source for debugging
            }
        )

    # 2. Load global sources from database (namespace = "")
    try:
        db_global_sources = (
            FallbackSource.select()
            .where(FallbackSource.namespace == "", FallbackSource.enabled == True)
            .order_by(FallbackSource.priority)
        )

        for source in db_global_sources:
            sources.append(
                {
                    "url": source.url,
                    "token": source.token,
                    "priority": source.priority,
                    "name": source.name,
                    "source_type": source.source_type,
                    "token_source": "admin",
                }
            )
    except Exception as e:
        logger.warning(f"Failed to load global sources from database: {e}")

    # 3. Load namespace-specific sources from database (if namespace provided)
    if namespace:
        try:
            db_namespace_sources = (
                FallbackSource.select()
                .where(
                    FallbackSource.namespace == namespace,
                    FallbackSource.enabled == True,
                )
                .order_by(FallbackSource.priority)
            )

            for source in db_namespace_sources:
                sources.append(
                    {
                        "url": source.url,
                        "token": source.token,
                        "priority": source.priority,
                        "name": source.name,
                        "source_type": source.source_type,
                        "token_source": "admin",
                    }
                )
        except Exception as e:
            logger.warning(
                f"Failed to load namespace sources from database for {namespace}: {e}"
            )

    # Remove duplicates (by URL) and sort by priority
    seen_urls = set()
    unique_sources = []
    for source in sources:
        if source["url"] not in seen_urls:
            seen_urls.add(source["url"])
            unique_sources.append(source)

    # Sort by priority (lower = higher priority)
    unique_sources.sort(key=lambda s: s["priority"])

    # 4. Override admin tokens with user tokens for matching URLs
    if user_tokens:
        for source in unique_sources:
            if source["url"] in user_tokens:
                source["token"] = user_tokens[source["url"]]
                source["token_source"] = "user"  # Mark as user-provided token
                logger.debug(f"Using user token for {source['name']} ({source['url']})")

    logger.debug(
        f"Loaded {len(unique_sources)} fallback sources for namespace='{namespace}'"
    )

    return unique_sources


def get_source_by_url(url: str, namespace: str = "") -> Optional[dict]:
    """Get a specific fallback source by URL.

    Args:
        url: Base URL of the source
        namespace: User/org namespace

    Returns:
        Source dict or None if not found
    """
    sources = get_enabled_sources(namespace)
    for source in sources:
        if source["url"] == url:
            return source
    return None
