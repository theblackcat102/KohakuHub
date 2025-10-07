"""Configuration management for Kohaku Hub."""

import os
import tomllib
from functools import lru_cache
from pydantic import BaseModel


class S3Config(BaseModel):
    public_endpoint: str = "http://localhost:9000"
    endpoint: str = "http://localhost:9000"
    access_key: str = "test-access-key"
    secret_key: str = "test-secret-key"
    bucket: str = "test-bucket"
    region: str = "us-east-1"
    force_path_style: bool = True


class LakeFSConfig(BaseModel):
    endpoint: str = "http://localhost:8000"
    access_key: str = "test-access-key"
    secret_key: str = "test-secret-key"
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


class AdminConfig(BaseModel):
    """Admin API configuration."""

    enabled: bool = True
    secret_token: str = "change-me-in-production"


class QuotaConfig(BaseModel):
    """Storage quota configuration."""

    default_user_private_quota_bytes: int | None = None  # None = unlimited
    default_user_public_quota_bytes: int | None = None  # None = unlimited
    default_org_private_quota_bytes: int | None = None  # None = unlimited
    default_org_public_quota_bytes: int | None = None  # None = unlimited


class AppConfig(BaseModel):
    base_url: str = "http://localhost:48888"
    api_base: str = "/api"
    db_backend: str = "sqlite"
    database_url: str = "sqlite:///./hub.db"
    # Lower threshold to 5MB to account for base64 encoding overhead (~33%)
    # 5MB file -> ~6.7MB base64, leaving room for multiple files in one commit
    lfs_threshold_bytes: int = 5 * 1024 * 1024
    debug_log_payloads: bool = False
    # LFS Garbage Collection settings
    lfs_keep_versions: int = 5  # Keep last K versions of each file
    lfs_auto_gc: bool = False  # Auto-delete old LFS objects on commit
    # Site identification
    site_name: str = "KohakuHub"  # Configurable site name (e.g., "MyCompany Hub")


class Config(BaseModel):
    s3: S3Config
    lakefs: LakeFSConfig
    smtp: SMTPConfig = SMTPConfig()
    auth: AuthConfig = AuthConfig()
    admin: AdminConfig = AdminConfig()
    quota: QuotaConfig = QuotaConfig()
    app: AppConfig

    def validate_production_safety(self) -> list[str]:
        """Check if configuration uses unsafe default values.

        Returns:
            List of warning messages for unsafe defaults
        """
        warnings = []

        # S3 credentials
        if self.s3.access_key == "test-access-key":
            warnings.append("S3 access_key is using test default value")
        if self.s3.secret_key == "test-secret-key":
            warnings.append("S3 secret_key is using test default value")
        if self.s3.bucket == "test-bucket":
            warnings.append("S3 bucket is using test default value")

        # LakeFS credentials
        if self.lakefs.access_key == "test-access-key":
            warnings.append("LakeFS access_key is using test default value")
        if self.lakefs.secret_key == "test-secret-key":
            warnings.append("LakeFS secret_key is using test default value")

        # Auth secrets
        if self.auth.session_secret == "change-me-in-production":
            warnings.append("Session secret is using default value - SECURITY RISK!")
        if self.admin.secret_token == "change-me-in-production":
            warnings.append(
                "Admin secret token is using default value - SECURITY RISK!"
            )

        return warnings


@lru_cache(maxsize=1)
def load_config(path: str = None) -> Config:
    path = path or os.environ.get("HUB_CONFIG", None)
    if path is None:
        s3_config = S3Config(
            public_endpoint=os.environ.get(
                "KOHAKU_HUB_S3_PUBLIC_ENDPOINT", "http://localhost:9000"
            ),
            endpoint=os.environ.get("KOHAKU_HUB_S3_ENDPOINT", "http://localhost:9000"),
            access_key=os.environ.get("KOHAKU_HUB_S3_ACCESS_KEY", "test-access-key"),
            secret_key=os.environ.get("KOHAKU_HUB_S3_SECRET_KEY", "test-secret-key"),
            bucket=os.environ.get("KOHAKU_HUB_S3_BUCKET", "test-bucket"),
            region=os.environ.get("KOHAKU_HUB_S3_REGION", "us-east-1"),
        )

        lakefs_config = LakeFSConfig(
            endpoint=os.environ.get(
                "KOHAKU_HUB_LAKEFS_ENDPOINT", "http://localhost:8000"
            ),
            access_key=os.environ.get(
                "KOHAKU_HUB_LAKEFS_ACCESS_KEY", "test-access-key"
            ),
            secret_key=os.environ.get(
                "KOHAKU_HUB_LAKEFS_SECRET_KEY", "test-secret-key"
            ),
            repo_namespace=os.environ.get("KOHAKU_HUB_LAKEFS_REPO_NAMESPACE", "hf"),
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

        admin_config = AdminConfig(
            enabled=os.environ.get("KOHAKU_HUB_ADMIN_ENABLED", "true").lower()
            == "true",
            secret_token=os.environ.get(
                "KOHAKU_HUB_ADMIN_SECRET_TOKEN", "change-me-in-production"
            ),
        )

        def _parse_quota(value: str | None) -> int | None:
            """Parse quota value from environment variable."""
            if value is None or value.lower() in ("", "none", "unlimited"):
                return None
            return int(value)

        quota_config = QuotaConfig(
            default_user_private_quota_bytes=_parse_quota(
                os.environ.get("KOHAKU_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES")
            ),
            default_user_public_quota_bytes=_parse_quota(
                os.environ.get("KOHAKU_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES")
            ),
            default_org_private_quota_bytes=_parse_quota(
                os.environ.get("KOHAKU_HUB_DEFAULT_ORG_PRIVATE_QUOTA_BYTES")
            ),
            default_org_public_quota_bytes=_parse_quota(
                os.environ.get("KOHAKU_HUB_DEFAULT_ORG_PUBLIC_QUOTA_BYTES")
            ),
        )

        app_config = AppConfig(
            base_url=os.environ.get("KOHAKU_HUB_BASE_URL", "http://localhost:48888"),
            api_base=os.environ.get("KOHAKU_HUB_API_BASE", "/api"),
            db_backend=os.environ.get("KOHAKU_HUB_DB_BACKEND", "sqlite"),
            database_url=os.environ.get(
                "KOHAKU_HUB_DATABASE_URL", "sqlite:///./hub.db"
            ),
            lfs_threshold_bytes=int(
                os.environ.get("KOHAKU_HUB_LFS_THRESHOLD_BYTES", "5242880")
            ),
            lfs_keep_versions=int(os.environ.get("KOHAKU_HUB_LFS_KEEP_VERSIONS", "5")),
            lfs_auto_gc=os.environ.get("KOHAKU_HUB_LFS_AUTO_GC", "false").lower()
            == "true",
            site_name=os.environ.get("KOHAKU_HUB_SITE_NAME", "KohakuHub"),
            debug_log_payloads=os.environ.get(
                "KOHAKU_HUB_DEBUG_LOG_PAYLOADS", "false"
            ).lower()
            == "true",
        )

        return Config(
            s3=s3_config,
            lakefs=lakefs_config,
            smtp=smtp_config,
            auth=auth_config,
            admin=admin_config,
            quota=quota_config,
            app=app_config,
        )
    else:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        return Config(**raw)


cfg = load_config()
