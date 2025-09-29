"""Authentication and authorization for Kohaku Hub API.

TODO: Implement real authentication system.
Currently returns mock user for development.
"""

from ..db import User, db


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

    TODO: Implement real authentication:
    - Parse Authorization header (Bearer token)
    - Validate token against database or JWT
    - Return actual User object
    - Raise HTTPException(401) if invalid

    Returns:
        Mock user object for development.
    """

    # Mock user for development
    class MockUser:
        username = "me"
        id = 1

    return MockUser()
