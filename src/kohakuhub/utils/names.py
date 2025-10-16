"""Name normalization utilities.

Shared utilities for username/organization/repository name validation and normalization.
"""


def normalize_name(name: str) -> str:
    """Normalize name for conflict checking.

    Names that normalize to the same value are considered conflicts.
    This prevents confusing names like 'My-Repo' and 'my_repo'.

    Args:
        name: Original name

    Returns:
        Normalized name (lowercase, hyphens/underscores removed)
    """
    # Convert to lowercase
    normalized = name.lower()
    # Remove hyphens and underscores
    normalized = normalized.replace("-", "").replace("_", "")
    return normalized
