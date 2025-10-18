"""Admin authentication utilities."""

import hashlib
import secrets

from fastapi import Header, HTTPException

from kohakuhub.config import cfg


async def verify_admin_token(x_admin_token: str | None = Header(None)) -> bool:
    """Verify admin secret token from header using constant-time comparison.

    Uses SHA3-512 hash with secrets.compare_digest() to prevent timing attacks.

    Args:
        x_admin_token: Admin token from X-Admin-Token header

    Returns:
        True if valid

    Raises:
        HTTPException: If admin API is disabled or token is invalid
    """
    if not cfg.admin.enabled:
        raise HTTPException(
            503,
            detail={"error": "Admin API is disabled"},
        )

    if not x_admin_token:
        raise HTTPException(
            401,
            detail={"error": "Admin token required in X-Admin-Token header"},
        )

    # Hash both tokens with SHA3-512 and compare using constant-time comparison
    # This prevents timing attacks that could leak token information
    provided_hash = hashlib.sha3_512(x_admin_token.encode()).hexdigest()
    expected_hash = hashlib.sha3_512(cfg.admin.secret_token.encode()).hexdigest()

    if not secrets.compare_digest(provided_hash, expected_hash):
        raise HTTPException(
            403,
            detail={"error": "Invalid admin token"},
        )

    return True
