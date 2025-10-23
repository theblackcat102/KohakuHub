"""
Rate Limiting for Dataset Viewer

Implements session-based and IP-based rate limiting to prevent abuse.
Uses sliding window algorithm with in-memory storage.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import HTTPException, Request


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    # Requests per window
    max_requests: int = 60
    # Window size in seconds
    window_seconds: int = 60
    # Max concurrent requests per session
    max_concurrent: int = 3
    # Max file size to process (bytes)
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    # Max rows to return
    max_rows: int = 10000


@dataclass
class RequestRecord:
    """Record of a request."""

    timestamp: float
    file_size: int = 0


class RateLimiter:
    """
    Sliding window rate limiter with session and IP tracking.

    Prevents abuse by limiting:
    - Requests per minute per session/IP
    - Concurrent requests per session/IP
    - Maximum file size to process
    - Maximum rows to return
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()

        # Track requests: {session_id: [RequestRecord]}
        self._requests: Dict[str, list[RequestRecord]] = defaultdict(list)

        # Track concurrent requests: {session_id: count}
        self._concurrent: Dict[str, int] = defaultdict(int)

        # Track total bytes processed: {session_id: bytes}
        self._bytes_processed: Dict[str, int] = defaultdict(int)

        # Last cleanup time
        self._last_cleanup = time.time()

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Priority:
        1. Session ID (from cookie)
        2. IP address
        3. Forwarded-For header (if behind proxy)
        """
        # Try session cookie first
        session_id = request.cookies.get("dataset_viewer_session")
        if session_id:
            return f"session:{session_id}"

        # Fall back to IP
        client_ip = request.client.host if request.client else "unknown"

        # Check for proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in chain
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    def _cleanup_old_records(self):
        """Remove records older than window (runs every minute)."""
        now = time.time()

        # Only cleanup once per minute
        if now - self._last_cleanup < 60:
            return

        cutoff = now - self.config.window_seconds

        # Remove old request records
        for identifier in list(self._requests.keys()):
            self._requests[identifier] = [
                r for r in self._requests[identifier] if r.timestamp > cutoff
            ]

            # Remove empty entries
            if not self._requests[identifier]:
                del self._requests[identifier]
                if identifier in self._bytes_processed:
                    del self._bytes_processed[identifier]

        self._last_cleanup = now

    def check_rate_limit(
        self, request: Request, file_size: Optional[int] = None
    ) -> None:
        """
        Check if request is allowed under rate limits.

        Raises HTTPException(429) if rate limit exceeded.
        """
        self._cleanup_old_records()

        identifier = self._get_identifier(request)
        now = time.time()
        cutoff = now - self.config.window_seconds

        # Get recent requests
        recent_requests = [
            r for r in self._requests[identifier] if r.timestamp > cutoff
        ]

        # Check request count limit
        if len(recent_requests) >= self.config.max_requests:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": self.config.max_requests,
                    "window_seconds": self.config.window_seconds,
                    "retry_after": int(
                        recent_requests[0].timestamp + self.config.window_seconds - now
                    ),
                },
                headers={
                    "Retry-After": str(
                        int(
                            recent_requests[0].timestamp
                            + self.config.window_seconds
                            - now
                        )
                    )
                },
            )

        # Check concurrent request limit
        if self._concurrent[identifier] >= self.config.max_concurrent:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many concurrent requests",
                    "limit": self.config.max_concurrent,
                    "current": self._concurrent[identifier],
                },
            )

        # Check file size limit
        if file_size and file_size > self.config.max_file_size:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "File too large",
                    "file_size": file_size,
                    "max_size": self.config.max_file_size,
                },
            )

    def start_request(self, request: Request, file_size: int = 0) -> str:
        """
        Mark request as started.

        Returns identifier for use in finish_request.
        """
        identifier = self._get_identifier(request)

        # Record request
        self._requests[identifier].append(RequestRecord(time.time(), file_size))

        # Increment concurrent counter
        self._concurrent[identifier] += 1

        return identifier

    def finish_request(self, identifier: str, bytes_processed: int = 0):
        """Mark request as finished."""
        # Decrement concurrent counter
        if self._concurrent[identifier] > 0:
            self._concurrent[identifier] -= 1

        # Track bytes processed
        self._bytes_processed[identifier] += bytes_processed

    def get_stats(self, identifier: str) -> dict:
        """Get rate limit stats for identifier."""
        now = time.time()
        cutoff = now - self.config.window_seconds

        recent_requests = [
            r for r in self._requests[identifier] if r.timestamp > cutoff
        ]

        return {
            "requests_used": len(recent_requests),
            "requests_limit": self.config.max_requests,
            "concurrent_requests": self._concurrent[identifier],
            "concurrent_limit": self.config.max_concurrent,
            "bytes_processed": self._bytes_processed.get(identifier, 0),
            "window_seconds": self.config.window_seconds,
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def check_rate_limit_dependency(request: Request) -> str:
    """
    FastAPI dependency for rate limiting.

    Usage:
        @router.get("/preview")
        async def preview(
            identifier: str = Depends(check_rate_limit_dependency)
        ):
            # ... do work
            get_rate_limiter().finish_request(identifier)
    """
    limiter = get_rate_limiter()
    limiter.check_rate_limit(request)
    return limiter.start_request(request)
