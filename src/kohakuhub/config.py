from pydantic import BaseModel, Field
from typing import Optional
from functools import lru_cache
import os, tomllib


class S3Config(BaseModel):
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    region: str = "us-east-1"
    force_path_style: bool = True  # MinIO 建議 path-style


class LakeFSConfig(BaseModel):
    public_endpoint: str  # 對外，例如 https://file.hub.kohaku-lab.org
    internal_endpoint: str  # 內網，例如 http://lakefs:28000
    access_key: str
    secret_key: str
    repo_namespace: str = "hf"  # 物件key前綴


class AppConfig(BaseModel):
    base_url: str  # 你的 API 對外 URL，例如 https://api.hub.kohaku-lab.org
    api_base: str = "/api"  # 路由前綴
    database_url: str = "sqlite:///./hub.db"  # ✅ 加回
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


# 方便直接 import 使用
cfg = load_config()
