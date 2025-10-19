"""Cache system for repository→source mappings.

Caches which external source has a given repository to reduce external API calls.
Does NOT cache actual content, only the mapping.
"""

import time
from typing import Optional

from cachetools import TTLCache

from kohakuhub.config import cfg
from kohakuhub.logger import get_logger

logger = get_logger("FALLBACK_CACHE")


class RepoSourceCache:
    """TTL cache for repo→source mappings."""

    def __init__(self, ttl_seconds: int = 300, maxsize: int = 10000):
        """Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cache entries
            maxsize: Maximum number of entries
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self.ttl = ttl_seconds

    def get_key(self, repo_type: str, namespace: str, name: str) -> str:
        """Generate cache key.

        Args:
            repo_type: "model", "dataset", or "space"
            namespace: Repository namespace
            name: Repository name

        Returns:
            Cache key string
        """
        return f"fallback:repo:{repo_type}:{namespace}/{name}"

    def get(
        self, repo_type: str, namespace: str, name: str
    ) -> Optional[dict[str, any]]:
        """Get cached source information.

        Args:
            repo_type: "model", "dataset", or "space"
            namespace: Repository namespace
            name: Repository name

        Returns:
            Cached source info dict or None if not found/expired
        """
        key = self.get_key(repo_type, namespace, name)
        cached = self.cache.get(key)

        if cached:
            logger.debug(
                f"Cache HIT: {repo_type}/{namespace}/{name} -> {cached.get('source_name')}"
            )
            return cached
        else:
            logger.debug(f"Cache MISS: {repo_type}/{namespace}/{name}")
            return None

    def set(
        self,
        repo_type: str,
        namespace: str,
        name: str,
        source_url: str,
        source_name: str,
        source_type: str,
        exists: bool = True,
    ):
        """Cache source information.

        Args:
            repo_type: "model", "dataset", or "space"
            namespace: Repository namespace
            name: Repository name
            source_url: Base URL of the source
            source_name: Display name of the source
            source_type: "huggingface" or "kohakuhub"
            exists: Whether the repo exists at this source
        """
        key = self.get_key(repo_type, namespace, name)
        value = {
            "source_url": source_url,
            "source_name": source_name,
            "source_type": source_type,
            "checked_at": int(time.time()),
            "exists": exists,
        }

        self.cache[key] = value
        logger.debug(
            f"Cache SET: {repo_type}/{namespace}/{name} -> {source_name} (TTL={self.ttl}s)"
        )

    def invalidate(self, repo_type: str, namespace: str, name: str):
        """Invalidate cache entry.

        Args:
            repo_type: "model", "dataset", or "space"
            namespace: Repository namespace
            name: Repository name
        """
        key = self.get_key(repo_type, namespace, name)
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache INVALIDATE: {repo_type}/{namespace}/{name}")

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        logger.info("Cache cleared")

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dict with cache stats (size, maxsize, ttl)
        """
        return {
            "size": len(self.cache),
            "maxsize": self.cache.maxsize,
            "ttl_seconds": self.ttl,
        }


# Global cache instance
_cache = None


def get_cache() -> RepoSourceCache:
    """Get global cache instance (singleton).

    Returns:
        Global RepoSourceCache instance
    """
    global _cache
    if _cache is None:
        ttl = cfg.fallback.cache_ttl_seconds
        _cache = RepoSourceCache(ttl_seconds=ttl)
        logger.info(f"Initialized fallback cache (TTL={ttl}s)")
    return _cache
