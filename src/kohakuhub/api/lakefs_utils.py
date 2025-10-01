"""LakeFS client utilities and helper functions."""

import lakefs_client
from lakefs_client.client import LakeFSClient

from ..config import cfg
from ..db import Repository


def get_lakefs_client() -> LakeFSClient:
    """Create configured LakeFS client.

    Returns:
        Configured LakeFSClient instance.
    """
    config = lakefs_client.Configuration()
    config.username = cfg.lakefs.access_key
    config.password = cfg.lakefs.secret_key
    config.host = f"{cfg.lakefs.endpoint}/api/v1"
    return LakeFSClient(config)


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
    repo = Repository.get_or_none(full_id=repo_id, repo_type=repo_type)
    if repo:
        return f"{basename}-{repo.id}"
    return basename
