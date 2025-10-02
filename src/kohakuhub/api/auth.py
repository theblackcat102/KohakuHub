"""Authentication and authorization for Kohaku Hub API.

Integrates with the new auth system in kohakuhub.auth module.
"""
from ..auth.dependencies import (
    get_current_user,
    get_optional_user,
)
