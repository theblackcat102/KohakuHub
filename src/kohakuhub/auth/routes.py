"""Authentication API routes."""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from kohakuhub.config import cfg
from kohakuhub.db import EmailVerification, Organization, Session, Token, User, db
from kohakuhub.db_operations import (
    create_email_verification,
    create_session,
    create_token,
    create_user,
    delete_email_verification,
    delete_session,
    delete_token,
    get_email_verification,
    get_session,
    get_token_by_hash,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    list_user_tokens,
    update_user,
)
from kohakuhub.logger import get_logger
from kohakuhub.auth.dependencies import get_current_user, get_optional_user
from kohakuhub.auth.email import send_verification_email
from kohakuhub.auth.utils import (
    generate_session_secret,
    generate_token,
    get_expiry_time,
    hash_password,
    hash_token,
    verify_password,
)
from kohakuhub.api.validation import normalize_name

logger = get_logger("AUTH")


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
async def register(req: RegisterRequest, invitation_token: str | None = None):
    """Register new user.

    Args:
        req: Registration request data
        invitation_token: Optional invitation token (required if invitation_only mode)

    Returns:
        Success response
    """
    # Check if registration requires invitation
    if cfg.auth.invitation_only:
        if not invitation_token:
            raise HTTPException(
                403,
                detail="Registration is invitation-only. Please use an invitation link or contact the administrator.",
            )

        # Validate invitation token
        from kohakuhub.db_operations import check_invitation_available, get_invitation

        invitation = get_invitation(invitation_token)
        if not invitation:
            raise HTTPException(400, detail="Invalid invitation token")

        # Check if invitation is for registration
        if invitation.action != "register_account":
            raise HTTPException(400, detail="Invalid invitation type for registration")

        # Check if invitation is available
        is_available, error_msg = check_invitation_available(invitation)
        if not is_available:
            raise HTTPException(400, detail=error_msg)

    logger.info(f"Registration attempt for username: {req.username}")

    # Check if username or email already exists and create user atomically
    with db.atomic():
        if get_user_by_username(req.username):
            logger.warning(
                f"Registration failed: username '{req.username}' already exists"
            )
            raise HTTPException(400, detail="Username already exists")

        if get_user_by_email(req.email):
            logger.warning(f"Registration failed: email '{req.email}' already exists")
            raise HTTPException(400, detail="Email already exists")

        # Check for normalized name conflicts with users and organizations
        normalized = normalize_name(req.username)

        # Check other users
        all_users = User.select()
        for user in all_users:
            if normalize_name(user.username) == normalized:
                logger.warning(
                    f"Registration failed: username conflicts with '{user.username}'"
                )
                raise HTTPException(
                    400,
                    detail=f"Username conflicts with existing user: {user.username}",
                )

        # Check organizations
        all_orgs = Organization.select()
        for org in all_orgs:
            if normalize_name(org.name) == normalized:
                logger.warning(
                    f"Registration failed: username conflicts with organization '{org.name}'"
                )
                raise HTTPException(
                    400,
                    detail=f"Username conflicts with existing organization: {org.name}",
                )

        # Create user
        user = create_user(
            username=req.username,
            email=req.email,
            password_hash=hash_password(req.password),
            email_verified=not cfg.auth.require_email_verification,
        )

    logger.success(f"User registered: {user.username} (id={user.id})")

    # If registration used an invitation, mark it and add to org if specified
    if cfg.auth.invitation_only and invitation_token:
        from kohakuhub.db_operations import get_invitation, mark_invitation_used
        import json

        invitation = get_invitation(invitation_token)
        if invitation:
            try:
                params = json.loads(invitation.parameters)
                org_id = params.get("org_id")

                with db.atomic():
                    mark_invitation_used(invitation, user.id)

                    # Add user to organization if specified
                    if org_id:
                        from kohakuhub.db_operations import create_user_organization

                        role = params.get("role", "member")
                        create_user_organization(user.id, org_id, role)
                        logger.success(
                            f"User {user.username} added to org (id={org_id}) as {role}"
                        )
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to process invitation on registration: {e}")

    # Send verification email if required
    if cfg.auth.require_email_verification:
        token = generate_token()
        create_email_verification(
            user_id=user.id, token=token, expires_at=get_expiry_time(24)
        )

        verification_email = await asyncio.to_thread(
            send_verification_email, req.email, req.username, token
        )
        if not verification_email:
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
    logger.info(f"Email verification attempt with token: {token[:8]}...")

    verification = get_email_verification(token)

    if not verification:
        logger.warning(f"Invalid verification token: {token[:8]}...")
        return RedirectResponse(
            url=f"/?error=invalid_token&message=Invalid+or+expired+verification+token",
            status_code=302,
        )

    # Ensure expires_at is timezone-aware for comparison
    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        logger.warning(f"Expired verification token: {token[:8]}...")
        # Redirect to login with error message
        return RedirectResponse(
            url=f"/?error=invalid_token&message=Invalid+or+expired+verification+token",
            status_code=302,
        )

    # Get user
    user = get_user_by_id(verification.user)
    if not user:
        logger.error(f"User not found for verification token: {token[:8]}...")
        return RedirectResponse(url="/?error=user_not_found", status_code=302)

    # Update user, delete verification, and create session atomically
    with db.atomic():
        update_user(user, email_verified=True)
        delete_email_verification(verification)

        logger.success(f"Email verified for user: {user.username}")

        # Create session for auto-login
        session_id = generate_token()
        session_secret = generate_session_secret()

        create_session(
            session_id=session_id,
            user_id=user.id,
            secret=session_secret,
            expires_at=get_expiry_time(cfg.auth.session_expire_hours),
        )

    # Set session cookie
    redirect_response = RedirectResponse(url=f"/{user.username}", status_code=302)
    redirect_response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=cfg.auth.session_expire_hours * 3600,
        samesite="lax",
    )

    logger.success(
        f"Auto-login session created for: {user.username} (session={session_id[:8]}...)"
    )

    return redirect_response


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    """Login and create session."""

    logger.info(f"Login attempt for user: {req.username}")

    user = get_user_by_username(req.username)

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

    create_session(
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
    deleted_count = Session.delete().where(Session.user_id == user.id).execute()

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

    tokens = list_user_tokens(user.id)

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
async def create_token_endpoint(
    req: CreateTokenRequest, user: User = Depends(get_current_user)
):
    """Create new API token."""

    # Generate token
    token_str = generate_token()
    token_hash_val = hash_token(token_str)

    # Save to database
    token = create_token(user_id=user.id, token_hash=token_hash_val, name=req.name)

    # Get session secret for encryption (if in web session)
    session = Session.get_or_none(Session.user_id == user.id)
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

    token = Token.get_or_none((Token.id == token_id) & (Token.user_id == user.id))

    if not token:
        raise HTTPException(404, detail="Token not found")

    delete_token(token.id)

    return {"success": True, "message": "Token revoked successfully"}
