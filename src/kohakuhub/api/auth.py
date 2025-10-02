"""Authentication and authorization for Kohaku Hub API.

Integrates with the new auth system in kohakuhub.auth module.
"""

from ..db import db, User
from ..auth.dependencies import (
    get_current_user as auth_get_current_user,
    get_optional_user,
)


def get_db():
    """Database connection dependency for FastAPI."""
    try:
        db.connect(reuse_if_open=True)
        yield db
    finally:
        if not db.is_closed():
            db.close()


def get_current_user():
    """Get current authenticated user.

    Now delegates to the real auth system.
    """
    return auth_get_current_user()
