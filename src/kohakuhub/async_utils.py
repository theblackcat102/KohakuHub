"""Async utilities for running blocking I/O operations in thread pool."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps, partial
from typing import Callable, TypeVar, Any

# Create a thread pool executor for blocking I/O operations
# Use a reasonable number of workers for S3/LakeFS operations
_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="kohakuhub_io")

T = TypeVar("T")


async def run_in_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """Run a blocking function in the thread pool executor.

    Args:
        func: Blocking function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result from the function

    Example:
        ```python
        result = await run_in_executor(
            client.staging.link_physical_address,
            repository=repo,
            branch=branch,
            path=path,
            staging_metadata=metadata
        )
        ```
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(_executor, func, *args)


def make_async(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """Decorator to make a blocking function async.

    Args:
        func: Blocking function to wrap

    Returns:
        Async version of the function

    Example:
        ```python
        @make_async
        def blocking_operation():
            # ... blocking code ...
            return result

        # Use it
        result = await blocking_operation()
        ```
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_executor(func, *args, **kwargs)

    return wrapper


class AsyncLakeFSClient:
    """Wrapper for LakeFS client with async methods for blocking operations.

    This wrapper only wraps the most commonly used blocking operations.
    For other operations, use run_in_executor directly.
    """

    def __init__(self, client):
        """Initialize with a LakeFS client.

        Args:
            client: LakeFS client instance
        """
        self._client = client

    async def link_physical_address(self, **kwargs):
        """Async version of staging.link_physical_address."""
        return await run_in_executor(
            self._client.staging.link_physical_address, **kwargs
        )

    async def upload_object(self, **kwargs):
        """Async version of objects.upload_object."""
        return await run_in_executor(self._client.objects.upload_object, **kwargs)

    async def commit(self, **kwargs):
        """Async version of commits.commit."""
        return await run_in_executor(self._client.commits.commit, **kwargs)

    async def delete_object(self, **kwargs):
        """Async version of objects.delete_object."""
        return await run_in_executor(self._client.objects.delete_object, **kwargs)

    async def list_objects(self, **kwargs):
        """Async version of objects.list_objects."""
        return await run_in_executor(self._client.objects.list_objects, **kwargs)

    async def stat_object(self, **kwargs):
        """Async version of objects.stat_object."""
        return await run_in_executor(self._client.objects.stat_object, **kwargs)

    async def get_object(self, **kwargs):
        """Async version of objects.get_object."""
        return await run_in_executor(self._client.objects.get_object, **kwargs)

    async def get_commit(self, **kwargs):
        """Async version of commits.get_commit."""
        return await run_in_executor(self._client.commits.get_commit, **kwargs)

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
    """Get an async-wrapped LakeFS client.

    Returns:
        AsyncLakeFSClient instance
    """
    from kohakuhub.api.utils.lakefs import get_lakefs_client

    return AsyncLakeFSClient(get_lakefs_client())
