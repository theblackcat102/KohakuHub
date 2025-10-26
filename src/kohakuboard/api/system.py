"""System information API endpoints"""

from fastapi import APIRouter, Depends, Request

from kohakuboard.auth import get_optional_user
from kohakuboard.config import cfg
from kohakuboard.db import User

router = APIRouter()


@router.get("/system/info")
async def get_system_info(
    request: Request, current_user: User | None = Depends(get_optional_user)
):
    """Get system information for frontend configuration

    Returns mode, authentication requirements, and user info if authenticated.
    Frontend uses this to determine UI behavior.

    Returns:
        dict: System info with mode, require_auth, version, and optional user
    """
    info = {
        "mode": cfg.app.mode,
        "require_auth": cfg.app.mode == "remote",
        "version": "0.1.0",
    }

    # If remote mode and authenticated, include user info
    if cfg.app.mode == "remote" and current_user:
        info["user"] = {
            "username": current_user.username,
            "email": current_user.email,
        }

    return info
