"""Configuration for KohakuBoard"""

import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Application configuration"""

    host: str = "0.0.0.0"
    port: int = 48889
    api_base: str = "/api"
    cors_origins: list = None
    board_data_dir: str = "./kohakuboard"

    # Mode configuration
    mode: str = "local"  # "local" or "remote"

    # Database configuration (for remote mode)
    db_backend: str = "sqlite"  # "sqlite" or "postgres"
    database_url: str = "sqlite:///kohakuboard.db"

    # Session configuration
    session_secret: str = "change-me-in-production"
    session_expires_days: int = 30

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:5175", "http://localhost:28080"]


@dataclass
class MockDataConfig:
    """Mock data generation configuration"""

    default_steps: int = 1000
    default_metrics_count: int = 4
    default_noise_level: float = 0.1
    max_steps: int = 100000
    max_metrics: int = 50


@dataclass
class Config:
    """Main configuration"""

    app: AppConfig
    mock: MockDataConfig

    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        mode = os.getenv("KOHAKU_BOARD_MODE", "local")

        return cls(
            app=AppConfig(
                host=os.getenv("KOHAKU_BOARD_HOST", "0.0.0.0"),
                port=int(os.getenv("KOHAKU_BOARD_PORT", "48889")),
                api_base=os.getenv("KOHAKU_BOARD_API_BASE", "/api"),
                board_data_dir=os.getenv("KOHAKU_BOARD_DATA_DIR", "./kohakuboard"),
                mode=mode,
                db_backend=os.getenv("KOHAKU_BOARD_DB_BACKEND", "sqlite"),
                database_url=os.getenv(
                    "KOHAKU_BOARD_DATABASE_URL", "sqlite:///kohakuboard.db"
                ),
                session_secret=os.getenv(
                    "KOHAKU_BOARD_SESSION_SECRET", "change-me-in-production"
                ),
                session_expires_days=int(
                    os.getenv("KOHAKU_BOARD_SESSION_EXPIRES_DAYS", "30")
                ),
            ),
            mock=MockDataConfig(
                default_steps=int(os.getenv("KOHAKU_BOARD_DEFAULT_STEPS", "1000")),
                default_metrics_count=int(
                    os.getenv("KOHAKU_BOARD_DEFAULT_METRICS", "4")
                ),
                default_noise_level=float(os.getenv("KOHAKU_BOARD_NOISE_LEVEL", "0.1")),
            ),
        )


cfg = Config.from_env()
