"""FastAPI dependencies for authentication."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Cookie, Header, HTTPException

from ..db import User, Session, Token
from .utils import hash_token


def get_current_user(
    session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> User:
    """Get current authenticated user from session or token."""

    session_id = str(session_id) if session_id is not None else None
    authorization = str(authorization) if authorization is not None else None

    print(f"session_id: {session_id}, authorization: {authorization}")

    # Try session-based auth first (web UI)
    if session_id:
        session = Session.get_or_none(
            (Session.session_id == session_id)
            & (Session.expires_at > datetime.now(timezone.utc))
        )
        if session:
            user = User.get_or_none(User.id == session.user_id)
            if user and user.is_active:
                return user

    # Try token-based auth (API)
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, detail="Invalid authorization header")

        token_str = authorization[7:]  # Remove "Bearer "
        token_hash = hash_token(token_str)

        token = Token.get_or_none(Token.token_hash == token_hash)
        if token:
            # Update last used
            Token.update(last_used=datetime.now(timezone.utc)).where(
                Token.id == token.id
            ).execute()

            user = User.get_or_none(User.id == token.user_id)
            if user and user.is_active:
                return user

    raise HTTPException(401, detail="Not authenticated")


def get_optional_user(
    session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    try:
        return get_current_user(session_id, authorization)
    except HTTPException:
        return None
