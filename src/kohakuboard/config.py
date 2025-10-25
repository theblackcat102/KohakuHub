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
        return cls(
            app=AppConfig(
                host=os.getenv("KOHAKU_BOARD_HOST", "0.0.0.0"),
                port=int(os.getenv("KOHAKU_BOARD_PORT", "48889")),
                api_base=os.getenv("KOHAKU_BOARD_API_BASE", "/api"),
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
