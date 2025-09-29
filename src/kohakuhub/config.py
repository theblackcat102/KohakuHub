"""Configuration management for Kohaku Hub."""

import os
import tomllib
from functools import lru_cache

from pydantic import BaseModel, Field


class S3Config(BaseModel):
    """S3-compatible storage configuration."""

    public_endpoint: str
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    region: str = "us-east-1"
    force_path_style: bool = True  # Required for MinIO


class LakeFSConfig(BaseModel):
    """LakeFS versioning system configuration."""

    public_endpoint: str  # External URL, e.g., https://file.hub.example.com
    internal_endpoint: str  # Internal URL, e.g., http://lakefs:8000
    access_key: str
    secret_key: str
    repo_namespace: str = "hf"  # Prefix for LakeFS repo names


class AppConfig(BaseModel):
    """Application-level configuration."""

    base_url: str  # External API URL, e.g., https://api.hub.example.com
    api_base: str = "/api"  # API route prefix
    database_url: str = "sqlite:///./hub.db"
    lfs_threshold_bytes: int = 10 * 1024 * 1024  # 10MB threshold
    debug_log_payloads: bool = False


class Config(BaseModel):
    """Root configuration object."""

    s3: S3Config
    lakefs: LakeFSConfig
    app: AppConfig


@lru_cache(maxsize=1)
def load_config(path: str = None) -> Config:
    """Load configuration from TOML file.

    Args:
        path: Path to config file. If None, uses HUB_CONFIG env var or default.

    Returns:
        Parsed Config object.
    """
    cfg_path = path or os.environ.get("HUB_CONFIG", "config.toml")
    with open(cfg_path, "rb") as f:
        raw = tomllib.load(f)
    return Config(**raw)


# Global config instance
cfg = load_config()
