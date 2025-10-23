"""
HTTP-based file-like object for reading remote files with range requests.

Allows libraries like PyArrow to read files from HTTP/S3 URLs without
downloading the entire file into memory.
"""

import httpx
from typing import Optional


class HTTPFile:
    """
    File-like object that reads from HTTP URL using range requests.

    Compatible with PyArrow's ParquetFile and other libraries that expect
    a file-like object with seek() and read() methods.
    """

    def __init__(self, url: str, timeout: float = 60.0):
        """
        Initialize HTTP file.

        Args:
            url: HTTP/HTTPS URL (including S3 presigned URLs)
            timeout: Request timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self._pos = 0
        self._size = None
        self._closed = False

        # Synchronous client for compatibility with file-like interface
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

        # Get file size with HEAD request
        try:
            head_response = self._client.head(url)
            head_response.raise_for_status()
            self._size = int(head_response.headers.get("content-length", 0))
        except Exception as e:
            # If HEAD fails, we'll get size on first read
            pass

    def read(self, size: int = -1) -> bytes:
        """
        Read bytes from current position.

        Args:
            size: Number of bytes to read (-1 = read to end)

        Returns:
            Bytes read
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # Read to end
        if size == -1:
            if self._size is None:
                # Download entire file (fallback)
                response = self._client.get(self.url)
                response.raise_for_status()
                data = response.content
                self._size = len(data)
                self._pos = self._size
                return data
            else:
                size = self._size - self._pos

        if size <= 0:
            return b""

        # Read with range request
        start = self._pos
        end = self._pos + size - 1

        # Make sure we don't read past end
        if self._size and end >= self._size:
            end = self._size - 1

        headers = {"Range": f"bytes={start}-{end}"}

        try:
            response = self._client.get(self.url, headers=headers)
            response.raise_for_status()

            # Update position
            self._pos += len(response.content)

            # Update size if we didn't have it
            if self._size is None:
                content_range = response.headers.get("content-range")
                if content_range:
                    # Format: "bytes 0-1023/5000"
                    parts = content_range.split("/")
                    if len(parts) == 2:
                        self._size = int(parts[1])

            return response.content

        except Exception as e:
            raise IOError(f"Failed to read from {self.url}: {e}")

    def seek(self, offset: int, whence: int = 0) -> int:
        """
        Seek to position.

        Args:
            offset: Byte offset
            whence: 0=absolute, 1=relative, 2=from end

        Returns:
            New position
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if whence == 0:  # Absolute
            self._pos = offset
        elif whence == 1:  # Relative
            self._pos += offset
        elif whence == 2:  # From end
            if self._size is None:
                raise IOError("Cannot seek from end without knowing file size")
            self._pos = self._size + offset
        else:
            raise ValueError(f"Invalid whence: {whence}")

        # Clamp to valid range
        self._pos = max(0, self._pos)
        if self._size is not None:
            self._pos = min(self._pos, self._size)

        return self._pos

    def tell(self) -> int:
        """Return current position."""
        return self._pos

    def close(self):
        """Close file and cleanup."""
        if not self._closed:
            self._client.close()
            self._closed = True

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    @property
    def closed(self) -> bool:
        """Check if file is closed."""
        return self._closed

    def readable(self) -> bool:
        """Check if file is readable."""
        return not self._closed

    def seekable(self) -> bool:
        """Check if file is seekable."""
        return not self._closed

    def writable(self) -> bool:
        """Check if file is writable."""
        return False


class AsyncHTTPFile:
    """
    Async version of HTTPFile for use with async libraries.

    Note: PyArrow doesn't support async file-like objects,
    so this is for future use with other libraries.
    """

    def __init__(self, url: str, timeout: float = 60.0):
        self.url = url
        self.timeout = timeout
        self._pos = 0
        self._size = None
        self._closed = False
        self._client = None

    async def _ensure_client(self):
        """Ensure async client is created."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True
            )

    async def read(self, size: int = -1) -> bytes:
        """Read bytes asynchronously."""
        if self._closed:
            raise ValueError("I/O operation on closed file")

        await self._ensure_client()

        # Get size if we don't have it
        if self._size is None:
            try:
                head_response = await self._client.head(self.url)
                head_response.raise_for_status()
                self._size = int(head_response.headers.get("content-length", 0))
            except Exception:
                pass

        # Read to end
        if size == -1:
            if self._size is None:
                response = await self._client.get(self.url)
                response.raise_for_status()
                data = response.content
                self._size = len(data)
                self._pos = self._size
                return data
            else:
                size = self._size - self._pos

        if size <= 0:
            return b""

        # Range request
        start = self._pos
        end = self._pos + size - 1

        if self._size and end >= self._size:
            end = self._size - 1

        headers = {"Range": f"bytes={start}-{end}"}

        response = await self._client.get(self.url, headers=headers)
        response.raise_for_status()

        self._pos += len(response.content)

        return response.content

    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek to position."""
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            if self._size is None:
                raise IOError("Cannot seek from end without size")
            self._pos = self._size + offset

        self._pos = max(0, self._pos)
        if self._size is not None:
            self._pos = min(self._pos, self._size)

        return self._pos

    def tell(self) -> int:
        """Return current position."""
        return self._pos

    async def close(self):
        """Close file."""
        if not self._closed and self._client:
            await self._client.aclose()
            self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
