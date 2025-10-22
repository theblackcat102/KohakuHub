"""FastAPI dependencies for authentication."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Cookie, Header, HTTPException, Request

from kohakuhub.db import Session, Token, User
from kohakuhub.logger import get_logger
from kohakuhub.auth.utils import hash_token
from kohakuhub.auth.external_token_parser import parse_auth_header

logger = get_logger("AUTH")


def get_current_user(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> User:
    """Get current authenticated user from session or token.

    Also parses external fallback tokens from Authorization header and stores
    them in request.state for use by fallback system.
    """

    session_id = str(session_id) if session_id is not None else None
    authorization = str(authorization) if authorization is not None else None

    # Parse external tokens from Authorization header
    auth_token, external_tokens = parse_auth_header(authorization)

    # Store external tokens in request.state for fallback decorators
    request.state.external_tokens = external_tokens

    # Log authentication attempt
    auth_method = []
    if session_id:
        auth_method.append(f"session={session_id[:8]}...")
    if auth_token:
        auth_method.append("token=Bearer ***")
    if external_tokens:
        auth_method.append(f"external_tokens={len(external_tokens)} sources")

    if auth_method:
        logger.debug(f"Auth attempt: {', '.join(auth_method)}")

    # Try session-based auth first (web UI)
    if session_id:
        session = Session.get_or_none(
            (Session.session_id == session_id)
            & (Session.expires_at > datetime.now(timezone.utc))
        )
        if session:
            user = session.user  # Use ForeignKey relationship
            if user and user.is_active:
                logger.debug(
                    f"Authenticated via session: {user.username} (session={session_id[:8]}...)"
                )
                return user
            else:
                logger.warning(
                    f"Session {session_id[:8]}... found but user inactive or not found"
                )
        else:
            logger.debug(f"Session {session_id[:8]}... not found or expired")

    # Try token-based auth (API) - use parsed auth_token
    if auth_token:
        token_hash = hash_token(auth_token)

        token = Token.get_or_none(Token.token_hash == token_hash)
        if token:
            # Update last used
            Token.update(last_used=datetime.now(timezone.utc)).where(
                Token.id == token.id
            ).execute()

            user = token.user  # Use ForeignKey relationship
            if user and user.is_active:
                logger.debug(
                    f"Authenticated via token: {user.username} (token_id={token.id})"
                )
                return user
            else:
                logger.warning(f"Token {token.id} found but user inactive or not found")
        else:
            logger.debug("Token not found or invalid")

    logger.debug("Authentication failed - no valid session or token")
    raise HTTPException(401, detail="Not authenticated")


def get_optional_user(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None.

    Also parses external fallback tokens from Authorization header and stores
    them in request.state for use by fallback system (even if auth fails).
    """
    try:
        return get_current_user(request, session_id, authorization)
    except HTTPException:
        # Still parse external tokens even if auth fails (for fallback access)
        _, external_tokens = parse_auth_header(authorization)
        request.state.external_tokens = external_tokens
        return None


def get_external_tokens(request: Request) -> dict[str, str]:
    """Extract external tokens from request state (populated by auth).

    Returns empty dict if no external tokens were provided.
    """
    return getattr(request.state, "external_tokens", {})
