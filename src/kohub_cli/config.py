"""Configuration management for KohakuHub CLI."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Manage KohakuHub CLI configuration."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Configuration directory path. Defaults to ~/.kohub
        """
        if config_dir is None:
            config_dir = Path(
                os.environ.get("KOHUB_CONFIG_DIR", Path.home() / ".kohub")
            )

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "config.json"
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except Exception:
                return {}
        return {}

    def _save(self):
        """Save configuration to file."""
        self.config_file.write_text(json.dumps(self._data, indent=2))
        try:
            os.chmod(self.config_file, 0o600)
        except Exception:
            pass  # Best effort on non-POSIX systems

    def get(self, key: str, default=None):
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._data[key] = value
        self._save()

    def delete(self, key: str):
        """Delete configuration value.

        Args:
            key: Configuration key
        """
        if key in self._data:
            del self._data[key]
            self._save()

    def clear(self):
        """Clear all configuration."""
        self._data = {}
        self._save()

    def all(self) -> Dict[str, Any]:
        """Get all configuration values.

        Returns:
            Dictionary of all configuration values
        """
        return self._data.copy()

    @property
    def endpoint(self) -> str:
        """Get KohakuHub endpoint URL.

        Returns endpoint from:
        1. HF_ENDPOINT environment variable
        2. Config file
        3. Default: http://localhost:8000
        """
        return os.environ.get("HF_ENDPOINT") or self.get(
            "endpoint", "http://localhost:8000"
        )

    @endpoint.setter
    def endpoint(self, value: str):
        """Set KohakuHub endpoint URL."""
        self.set("endpoint", value.rstrip("/"))

    @property
    def token(self) -> Optional[str]:
        """Get API token.

        Returns token from:
        1. HF_TOKEN environment variable
        2. Config file
        3. None
        """
        return os.environ.get("HF_TOKEN") or self.get("token")

    @token.setter
    def token(self, value: Optional[str]):
        """Set API token."""
        if value:
            self.set("token", value)
        else:
            self.delete("token")
