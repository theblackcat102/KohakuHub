"""Authentication module."""

from .routes import router
from .dependencies import get_current_user, get_optional_user

__all__ = ["router", "get_current_user", "get_optional_user"]
