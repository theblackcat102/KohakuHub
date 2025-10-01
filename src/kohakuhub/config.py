"""Configuration management for Kohaku Hub."""

import os
import tomllib
from functools import lru_cache
from pydantic import BaseModel


class S3Config(BaseModel):
    public_endpoint: str
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    region: str = "us-east-1"
    force_path_style: bool = True


class LakeFSConfig(BaseModel):
    public_endpoint: str
    internal_endpoint: str
    access_key: str
    secret_key: str
    repo_namespace: str = "hf"


class AppConfig(BaseModel):
    base_url: str
    api_base: str = "/api"
    db_backend: str = "sqlite"  # "sqlite" or "postgres"
    database_url: str = "sqlite:///./hub.db"
    lfs_threshold_bytes: int = 10 * 1024 * 1024
    debug_log_payloads: bool = False


class Config(BaseModel):
    s3: S3Config
    lakefs: LakeFSConfig
    app: AppConfig


@lru_cache(maxsize=1)
def load_config(path: str = None) -> Config:
    cfg_path = path or os.environ.get("HUB_CONFIG", "config.toml")
    with open(cfg_path, "rb") as f:
        raw = tomllib.load(f)
    return Config(**raw)


cfg = load_config()
