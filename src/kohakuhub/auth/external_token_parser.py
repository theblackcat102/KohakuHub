"""Parser for external fallback tokens in Authorization header.

Format: "Bearer token|url1,token1|url2,token2..."

This allows users to pass their own tokens for external fallback sources
(HuggingFace, other KohakuHub instances) via the standard Authorization header.

Examples:
- Regular token: "Bearer hf_abc123"
  → ("hf_abc123", {})

- With one external token: "Bearer hf_abc123|https://huggingface.co,hf_external"
  → ("hf_abc123", {"https://huggingface.co": "hf_external"})

- With empty auth token: "Bearer |https://huggingface.co,hf_external"
  → (None, {"https://huggingface.co": "hf_external"})

- With empty external token: "Bearer hf_abc123|https://example.com,"
  → ("hf_abc123", {"https://example.com": ""})
"""

from typing import Optional

from kohakuhub.logger import get_logger

logger = get_logger("AUTH_PARSER")


def parse_auth_header(auth_header: str | None) -> tuple[str | None, dict[str, str]]:
    """Parse Authorization header into auth token and external tokens.

    Args:
        auth_header: Authorization header value (e.g., "Bearer token|url1,token1|...")

    Returns:
        Tuple of (auth_token, external_tokens_dict)
        - auth_token: Main authentication token (or None if empty/missing)
        - external_tokens_dict: Dict mapping URL -> token for external sources

    Examples:
        >>> parse_auth_header("Bearer hf_abc")
        ("hf_abc", {})

        >>> parse_auth_header("Bearer hf_abc|https://huggingface.co,hf_ext")
        ("hf_abc", {"https://huggingface.co": "hf_ext"})

        >>> parse_auth_header("Bearer |https://huggingface.co,hf_ext")
        (None, {"https://huggingface.co": "hf_ext"})

        >>> parse_auth_header(None)
        (None, {})
    """
    if not auth_header:
        return (None, {})

    # Check if it starts with "Bearer "
    if not auth_header.startswith("Bearer "):
        logger.debug("Auth header does not start with 'Bearer '")
        return (None, {})

    # Remove "Bearer " prefix
    token_string = auth_header[7:]  # len("Bearer ") = 7

    if not token_string:
        return (None, {})

    # Check if it contains external tokens (has "|")
    if "|" not in token_string:
        # Regular token format: "Bearer token"
        return (token_string, {})

    # Split by "|" to get parts
    parts = token_string.split("|")

    # First part is the auth token (can be empty)
    auth_token = parts[0] if parts[0] else None

    # Remaining parts are external tokens in format "url,token"
    external_tokens = {}
    for part in parts[1:]:
        if "," not in part:
            logger.warning(f"Invalid external token format (missing comma): {part}")
            continue

        # Split by first comma only (URL may contain commas in query params)
        url, token = part.split(",", 1)

        if not url:
            logger.warning(f"Invalid external token format (empty URL): {part}")
            continue

        # Add to dict (token can be empty string)
        external_tokens[url] = token
        logger.debug(
            f"Parsed external token for {url} (token length: {len(token) if token else 0})"
        )

    logger.debug(
        f"Parsed auth header: auth_token={'present' if auth_token else 'none'}, "
        f"external_tokens={len(external_tokens)} sources"
    )

    return (auth_token, external_tokens)


def format_auth_header(
    auth_token: str | None, external_tokens: dict[str, str] | None = None
) -> str:
    """Format auth token and external tokens into Authorization header.

    This is the inverse operation of parse_auth_header().

    Args:
        auth_token: Main authentication token (can be None)
        external_tokens: Dict mapping URL -> token for external sources

    Returns:
        Formatted Authorization header value

    Examples:
        >>> format_auth_header("hf_abc")
        "Bearer hf_abc"

        >>> format_auth_header("hf_abc", {"https://huggingface.co": "hf_ext"})
        "Bearer hf_abc|https://huggingface.co,hf_ext"

        >>> format_auth_header(None, {"https://huggingface.co": "hf_ext"})
        "Bearer |https://huggingface.co,hf_ext"

        >>> format_auth_header(None, {})
        "Bearer "
    """
    parts = [auth_token or ""]

    if external_tokens:
        for url, token in external_tokens.items():
            parts.append(f"{url},{token}")

    return f"Bearer {'|'.join(parts)}"
