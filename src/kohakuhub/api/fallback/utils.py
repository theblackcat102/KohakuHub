"""Utility functions for fallback system."""

from typing import Optional

import httpx

from kohakuhub.logger import get_logger

logger = get_logger("FALLBACK_UTILS")


def is_not_found_error(response: httpx.Response) -> bool:
    """Check if response indicates resource not found.

    Args:
        response: HTTP response

    Returns:
        True if 404 or similar "not found" error
    """
    return response.status_code in (404, 410)  # 404 Not Found, 410 Gone


def is_client_error(response: httpx.Response) -> bool:
    """Check if response is a client error (4xx).

    Args:
        response: HTTP response

    Returns:
        True if status code is 4xx
    """
    return 400 <= response.status_code < 500


def is_server_error(response: httpx.Response) -> bool:
    """Check if response is a server error (5xx).

    Args:
        response: HTTP response

    Returns:
        True if status code is 5xx
    """
    return 500 <= response.status_code < 600


def extract_error_message(response: httpx.Response) -> str:
    """Extract error message from response.

    Args:
        response: HTTP response

    Returns:
        Error message string
    """
    try:
        error_data = response.json()
        if isinstance(error_data, dict):
            # Try common error field names
            for field in ("error", "message", "detail", "msg"):
                if field in error_data:
                    msg = error_data[field]
                    if isinstance(msg, str):
                        return msg
                    elif isinstance(msg, dict) and "message" in msg:
                        return msg["message"]
        return str(error_data)
    except Exception:
        return response.text or f"HTTP {response.status_code}"


def should_retry_source(response: httpx.Response) -> bool:
    """Determine if request should be retried with next source.

    Args:
        response: HTTP response

    Returns:
        True if should try next source, False if should give up
    """
    # Retry on 404 (not found) - might be in another source
    if response.status_code == 404:
        return True

    # Retry on server errors (5xx) - source might be temporarily down
    if is_server_error(response):
        return True

    # Retry on timeout/connection errors
    if response.status_code in (408, 504, 524):  # Timeout, Gateway Timeout
        return True

    # Don't retry on other client errors (401, 403, 400, etc.)
    # These indicate permission/validation issues
    if is_client_error(response):
        return False

    # Success - don't retry
    if 200 <= response.status_code < 300:
        return False

    # Default: don't retry
    return False


def add_source_headers(
    response: httpx.Response, source_name: str, source_url: str
) -> dict:
    """Generate source attribution headers.

    Args:
        response: Original response from external source
        source_name: Display name of the source
        source_url: Base URL of the source

    Returns:
        Dict of headers to add to the response
    """
    return {
        "X-Source": source_name,
        "X-Source-URL": source_url,
        "X-Source-Status": str(response.status_code),
    }
