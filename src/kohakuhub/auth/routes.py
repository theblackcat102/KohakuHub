"""Authentication API routes."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel, EmailStr

from ..config import cfg
from ..db_async import (
    create_email_verification,
    create_session,
    create_token,
    create_user,
    delete_email_verification,
    delete_session,
    delete_token,
    execute_db_query,
    get_email_verification,
    get_session,
    get_token_by_hash,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    list_user_tokens,
    update_user,
)
from ..db import User, EmailVerification, Session, Token
from ..logger import get_logger

logger = get_logger("AUTH")
from .utils import (
    hash_password,
    verify_password,
    generate_token,
    hash_token,
    generate_session_secret,
    get_expiry_time,
)
from .email import send_verification_email
from .dependencies import get_current_user, get_optional_user


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateTokenRequest(BaseModel):
    name: str


@router.post("/register")
async def register(req: RegisterRequest):
    """Register new user."""

    logger.info(f"Registration attempt for username: {req.username}")

    # Check if username or email already exists
    if await get_user_by_username(req.username):
        logger.warning(f"Registration failed: username '{req.username}' already exists")
        raise HTTPException(400, detail="Username already exists")

    if await get_user_by_email(req.email):
        logger.warning(f"Registration failed: email '{req.email}' already exists")
        raise HTTPException(400, detail="Email already exists")

    # Create user
    user = await create_user(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        email_verified=not cfg.auth.require_email_verification,
    )

    logger.success(f"User registered: {user.username} (id={user.id})")

    # Send verification email if required
    if cfg.auth.require_email_verification:
        token = generate_token()
        await create_email_verification(
            user_id=user.id, token=token, expires_at=get_expiry_time(24)
        )

        if not send_verification_email(req.email, req.username, token):
            return {
                "success": True,
                "message": "User created but failed to send verification email",
                "email_verified": False,
            }

        return {
            "success": True,
            "message": "User created. Please check your email to verify your account.",
            "email_verified": False,
        }

    return {
        "success": True,
        "message": "User created successfully",
        "email_verified": True,
    }


@router.get("/verify-email")
async def verify_email(token: str, response: Response):
    """Verify email with token and automatically log in user."""
    from fastapi.responses import RedirectResponse

    logger.info(f"Email verification attempt with token: {token[:8]}...")

    verification = await get_email_verification(token)

    if not verification or verification.expires_at <= datetime.now(timezone.utc):
        logger.warning(f"Invalid or expired verification token: {token[:8]}...")
        # Redirect to login with error message
        return RedirectResponse(
            url=f"/?error=invalid_token&message=Invalid+or+expired+verification+token",
            status_code=302,
        )

    # Get user
    user = await get_user_by_id(verification.user)
    if not user:
        logger.error(f"User not found for verification token: {token[:8]}...")
        return RedirectResponse(url="/?error=user_not_found", status_code=302)

    # Update user email verification status
    await update_user(user, email_verified=True)

    # Delete verification token
    await delete_email_verification(verification)

    logger.success(f"Email verified for user: {user.username}")

    # Create session for auto-login
    session_id = generate_token()
    session_secret = generate_session_secret()

    await create_session(
        session_id=session_id,
        user_id=user.id,
        secret=session_secret,
        expires_at=get_expiry_time(cfg.auth.session_expire_hours),
    )

    # Set session cookie
    response = RedirectResponse(url=f"/{user.username}", status_code=302)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=cfg.auth.session_expire_hours * 3600,
        samesite="lax",
    )

    logger.success(
        f"Auto-login session created for: {user.username} (session={session_id[:8]}...)"
    )

    return response


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    """Login and create session."""

    logger.info(f"Login attempt for user: {req.username}")

    user = await get_user_by_username(req.username)

    if not user or not verify_password(req.password, user.password_hash):
        logger.warning(f"Failed login attempt for: {req.username}")
        raise HTTPException(401, detail="Invalid username or password")

    if not user.is_active:
        logger.warning(f"Login attempt for disabled account: {req.username}")
        raise HTTPException(403, detail="Account is disabled")

    if cfg.auth.require_email_verification and not user.email_verified:
        logger.warning(f"Login attempt with unverified email: {req.username}")
        raise HTTPException(403, detail="Please verify your email first")

    # Create session
    session_id = generate_token()
    session_secret = generate_session_secret()

    await create_session(
        session_id=session_id,
        user_id=user.id,
        secret=session_secret,
        expires_at=get_expiry_time(cfg.auth.session_expire_hours),
    )

    # Set cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=cfg.auth.session_expire_hours * 3600,
        samesite="lax",
    )

    logger.success(f"User logged in: {user.username} (session={session_id[:8]}...)")

    return {
        "success": True,
        "message": "Logged in successfully",
        "username": user.username,
        "session_secret": session_secret,
    }


@router.post("/logout")
async def logout(response: Response, user: User = Depends(get_current_user)):
    """Logout and destroy session."""

    logger.info(f"Logout request for user: {user.username}")

    # Delete all user sessions
    def _delete_sessions():
        return Session.delete().where(Session.user_id == user.id).execute()

    deleted_count = await execute_db_query(_delete_sessions)

    # Clear cookie
    response.delete_cookie(key="session_id")

    logger.success(
        f"User logged out: {user.username} ({deleted_count} session(s) deleted)"
    )

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    """Get current user info (internal endpoint)."""

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat(),
    }


@router.get("/tokens")
async def list_tokens(user: User = Depends(get_current_user)):
    """List user's API tokens."""

    tokens = await list_user_tokens(user.id)

    return {
        "tokens": [
            {
                "id": t.id,
                "name": t.name,
                "last_used": t.last_used.isoformat() if t.last_used else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in tokens
        ]
    }


@router.post("/tokens/create")
async def create_token_endpoint(req: CreateTokenRequest, user: User = Depends(get_current_user)):
    """Create new API token."""

    # Generate token
    token_str = generate_token()
    token_hash_val = hash_token(token_str)

    # Save to database
    token = await create_token(user_id=user.id, token_hash=token_hash_val, name=req.name)

    # Get session secret for encryption (if in web session)
    def _get_session():
        return Session.get_or_none(Session.user_id == user.id)

    session = await execute_db_query(_get_session)
    session_secret = session.secret if session else None

    return {
        "success": True,
        "token": token_str,
        "token_id": token.id,
        "session_secret": session_secret,
        "message": "Token created. Save it securely - you won't see it again!",
    }


@router.delete("/tokens/{token_id}")
async def revoke_token(token_id: int, user: User = Depends(get_current_user)):
    """Revoke an API token."""

    def _get_token():
        return Token.get_or_none((Token.id == token_id) & (Token.user_id == user.id))

    token = await execute_db_query(_get_token)

    if not token:
        raise HTTPException(404, detail="Token not found")

    await delete_token(token.id)

    return {"success": True, "message": "Token revoked successfully"}
