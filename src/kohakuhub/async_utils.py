"""Async utilities for running blocking I/O operations in thread pool."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from typing import Callable, TypeVar

# Create separate thread pool executors for different types of operations
# S3 operations can be I/O intensive and benefit from multiple workers
_s3_executor = ThreadPoolExecutor(max_workers=32, thread_name_prefix="kohakuhub_s3")

# LakeFS operations can also use multiple workers
_lakefs_executor = ThreadPoolExecutor(
    max_workers=32, thread_name_prefix="kohakuhub_lakefs"
)

# DEPRECATED: DB operations are now synchronous and don't need thread pool
# Database operations use db.atomic() for transactions instead
# Keeping this for backward compatibility only
_db_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kohakuhub_db")

T = TypeVar("T")


async def run_in_s3_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """Run S3 operation in dedicated S3 thread pool.

    Args:
        func: S3 operation to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result from the function
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(_s3_executor, func, *args)


async def run_in_lakefs_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """Run LakeFS operation in dedicated LakeFS thread pool.

    Args:
        func: LakeFS operation to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result from the function
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(_lakefs_executor, func, *args)


async def run_in_db_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """DEPRECATED: Run database operation in dedicated single-worker DB thread pool.

    Database operations are now synchronous and use db.atomic() for transactions.
    This function is kept for backward compatibility only.

    Args:
        func: Database operation to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result from the function
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(_db_executor, func, *args)


# Backward compatibility alias
async def run_in_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """Run a blocking function in the LakeFS thread pool executor (legacy).

    DEPRECATED: Use run_in_lakefs_executor, run_in_s3_executor, or run_in_db_executor instead.

    Args:
        func: Blocking function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result from the function
    """
    return await run_in_lakefs_executor(func, *args, **kwargs)


def make_async_s3(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """Decorator to make a blocking S3 function async.

    Args:
        func: Blocking S3 function to wrap

    Returns:
        Async version of the function
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_s3_executor(func, *args, **kwargs)

    return wrapper


def make_async_lakefs(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """Decorator to make a blocking LakeFS function async.

    Args:
        func: Blocking LakeFS function to wrap

    Returns:
        Async version of the function
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_lakefs_executor(func, *args, **kwargs)

    return wrapper


def make_async_db(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """Decorator to make a blocking database function async.

    Args:
        func: Blocking database function to wrap

    Returns:
        Async version of the function
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_db_executor(func, *args, **kwargs)

    return wrapper


# Backward compatibility alias
def make_async(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """DEPRECATED: Use make_async_lakefs, make_async_s3, or make_async_db instead."""
    return make_async_lakefs(func)


class AsyncLakeFSClient:
    """Wrapper for LakeFS client with async methods for blocking operations.

    This wrapper only wraps the most commonly used blocking operations.
    For other operations, use run_in_lakefs_executor directly.
    """

    def __init__(self, client):
        """Initialize with a LakeFS client.

        Args:
            client: LakeFS client instance
        """
        self._client = client

    async def link_physical_address(self, **kwargs):
        """Async version of staging.link_physical_address."""
        return await run_in_lakefs_executor(
            self._client.staging.link_physical_address, **kwargs
        )

    async def upload_object(self, **kwargs):
        """Async version of objects.upload_object."""
        return await run_in_lakefs_executor(
            self._client.objects.upload_object, **kwargs
        )

    async def commit(self, **kwargs):
        """Async version of commits.commit."""
        return await run_in_lakefs_executor(self._client.commits.commit, **kwargs)

    async def delete_object(self, **kwargs):
        """Async version of objects.delete_object."""
        return await run_in_lakefs_executor(
            self._client.objects.delete_object, **kwargs
        )

    async def list_objects(self, **kwargs):
        """Async version of objects.list_objects."""
        return await run_in_lakefs_executor(self._client.objects.list_objects, **kwargs)

    async def stat_object(self, **kwargs):
        """Async version of objects.stat_object."""
        return await run_in_lakefs_executor(self._client.objects.stat_object, **kwargs)

    async def get_object(self, **kwargs):
        """Async version of objects.get_object."""
        return await run_in_lakefs_executor(self._client.objects.get_object, **kwargs)

    async def get_commit(self, **kwargs):
        """Async version of commits.get_commit."""
        return await run_in_lakefs_executor(self._client.commits.get_commit, **kwargs)

    async def create_repository(self, **kwargs):
        """Async version of repositories.create_repository."""
        return await run_in_lakefs_executor(
            self._client.repositories.create_repository, **kwargs
        )

    async def delete_repository(self, **kwargs):
        """Async version of repositories.delete_repository."""
        return await run_in_lakefs_executor(
            self._client.repositories.delete_repository, **kwargs
        )

    async def create_branch(self, **kwargs):
        """Async version of branches.create_branch."""
        return await run_in_lakefs_executor(
            self._client.branches.create_branch, **kwargs
        )

    async def delete_branch(self, **kwargs):
        """Async version of branches.delete_branch."""
        return await run_in_lakefs_executor(
            self._client.branches.delete_branch, **kwargs
        )

    async def create_tag(self, **kwargs):
        """Async version of tags.create_tag."""
        return await run_in_lakefs_executor(self._client.tags.create_tag, **kwargs)

    async def delete_tag(self, **kwargs):
        """Async version of tags.delete_tag."""
        return await run_in_lakefs_executor(self._client.tags.delete_tag, **kwargs)

    async def log_commits(self, **kwargs):
        """Async version of commits.log_commits."""
        return await run_in_lakefs_executor(self._client.commits.log_commits, **kwargs)

    # Synchronous passthrough for other methods
    @property
    def repositories(self):
        """Access to repositories API (sync)."""
        return self._client.repositories

    @property
    def branches(self):
        """Access to branches API (sync)."""
        return self._client.branches

    @property
    def commits(self):
        """Access to commits API (sync - use async wrapper for commit)."""
        return self._client.commits

    @property
    def staging(self):
        """Access to staging API (sync - use async wrapper for link)."""
        return self._client.staging

    @property
    def objects(self):
        """Access to objects API (sync - use async wrapper for heavy ops)."""
        return self._client.objects


def get_async_lakefs_client():
    """Get LakeFS REST client.

    Returns:
        LakeFSRestClient instance (already async, no wrapping needed)
    """
    # Import here to avoid circular dependency
    from kohakuhub.lakefs_rest_client import get_lakefs_rest_client

    return get_lakefs_rest_client()
