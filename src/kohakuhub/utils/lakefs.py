"""LakeFS client utilities and helper functions."""

from kohakuhub.config import cfg
from kohakuhub.lakefs_rest_client import LakeFSRestClient, get_lakefs_rest_client


def get_lakefs_client() -> LakeFSRestClient:
    """Get configured LakeFS REST client.

    Returns:
        Configured LakeFSRestClient instance.
    """
    return get_lakefs_rest_client()


def lakefs_repo_name(repo_type: str, repo_id: str) -> str:
    """Generate LakeFS repository name from HuggingFace repo ID.

    Args:
        repo_type: Repository type (model/dataset/space)
        repo_id: Full repository ID (e.g., "org/repo-name")

    Returns:
        LakeFS-safe repository name (e.g., "hf-model-org-repo-name")
    """
    # Replace slashes with hyphens for LakeFS compatibility
    safe_id = repo_id.replace("/", "-")
    basename = f"{cfg.lakefs.repo_namespace}-{repo_type}-{safe_id}".lower()
    return basename
