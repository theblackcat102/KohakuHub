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
    endpoint: str
    access_key: str
    secret_key: str
    repo_namespace: str = "hf"


class SMTPConfig(BaseModel):
    enabled: bool = False
    host: str = "localhost"
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = "noreply@localhost"
    use_tls: bool = True


class AuthConfig(BaseModel):
    require_email_verification: bool = False
    session_secret: str = "change-me-in-production"
    session_expire_hours: int = 168  # 7 days
    token_expire_days: int = 365


class AppConfig(BaseModel):
    base_url: str
    api_base: str = "/api"
    db_backend: str = "sqlite"
    database_url: str = "sqlite:///./hub.db"
    lfs_threshold_bytes: int = 10 * 1024 * 1024
    debug_log_payloads: bool = False


class Config(BaseModel):
    s3: S3Config
    lakefs: LakeFSConfig
    smtp: SMTPConfig = SMTPConfig()
    auth: AuthConfig = AuthConfig()
    app: AppConfig


@lru_cache(maxsize=1)
def load_config(path: str = None) -> Config:
    path = path or os.environ.get("HUB_CONFIG", None)
    if path is None:
        s3_config = S3Config(
            public_endpoint=os.environ["KOHAKU_HUB_S3_PUBLIC_ENDPOINT"],
            endpoint=os.environ["KOHAKU_HUB_S3_ENDPOINT"],
            access_key=os.environ["KOHAKU_HUB_S3_ACCESS_KEY"],
            secret_key=os.environ["KOHAKU_HUB_S3_SECRET_KEY"],
            bucket=os.environ.get("KOHAKU_HUB_S3_BUCKET", "hub_storage"),
            region=os.environ.get("KOHAKU_HUB_S3_REGION", "us-east-1"),
        )

        lakefs_config = LakeFSConfig(
            endpoint=os.environ["KOHAKU_HUB_LAKEFS_ENDPOINT"],
            access_key=os.environ["KOHAKU_HUB_LAKEFS_ACCESS_KEY"],
            secret_key=os.environ["KOHAKU_HUB_LAKEFS_SECRET_KEY"],
            repo_namespace=os.environ.get("KOHAKU_HUB_LAKEFS_REPO_NAMESPACE", ""),
        )

        smtp_config = SMTPConfig(
            enabled=os.environ.get("KOHAKU_HUB_SMTP_ENABLED", "false").lower()
            == "true",
            host=os.environ.get("KOHAKU_HUB_SMTP_HOST", "localhost"),
            port=int(os.environ.get("KOHAKU_HUB_SMTP_PORT", "587")),
            username=os.environ.get("KOHAKU_HUB_SMTP_USERNAME", ""),
            password=os.environ.get("KOHAKU_HUB_SMTP_PASSWORD", ""),
            from_email=os.environ.get("KOHAKU_HUB_SMTP_FROM", "noreply@localhost"),
            use_tls=os.environ.get("KOHAKU_HUB_SMTP_TLS", "true").lower() == "true",
        )

        auth_config = AuthConfig(
            require_email_verification=os.environ.get(
                "KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION", "false"
            ).lower()
            == "true",
            session_secret=os.environ.get(
                "KOHAKU_HUB_SESSION_SECRET", "change-me-in-production"
            ),
            session_expire_hours=int(
                os.environ.get("KOHAKU_HUB_SESSION_EXPIRE_HOURS", "168")
            ),
            token_expire_days=int(
                os.environ.get("KOHAKU_HUB_TOKEN_EXPIRE_DAYS", "365")
            ),
        )

        app_config = AppConfig(
            base_url=os.environ.get("KOHAKU_HUB_BASE_URL", "127.0.0.1:48888"),
            api_base=os.environ.get("KOHAKU_HUB_API_BASE", "/api"),
            db_backend=os.environ["KOHAKU_HUB_DB_BACKEND"],
            database_url=os.environ["KOHAKU_HUB_DATABASE_URL"],
            lfs_threshold_bytes=int(
                os.environ.get("KOHAKU_HUB_LFS_THRESHOLD_BYTES", "10000000")
            ),
        )

        return Config(
            s3=s3_config,
            lakefs=lakefs_config,
            smtp=smtp_config,
            auth=auth_config,
            app=app_config,
        )
    else:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        return Config(**raw)


cfg = load_config()
