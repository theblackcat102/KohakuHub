"""
Colored logger for dataset viewer (independent from main KohakuHub).

Licensed under Kohaku Software License.
"""

import os
import sys
from datetime import datetime
from enum import Enum


class Color:
    """ANSI color codes for terminal output."""

    # Text colors
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background colors
    BG_RED = "\033[41m"

    # Text styles
    BOLD = "\033[1m"


class LogLevel(Enum):
    """Log levels with associated colors."""

    DEBUG = ("DEBUG", Color.BRIGHT_BLACK)
    INFO = ("INFO", Color.BRIGHT_CYAN)
    SUCCESS = ("SUCCESS", Color.BRIGHT_GREEN)
    WARNING = ("WARNING", Color.BRIGHT_YELLOW)
    ERROR = ("ERROR", Color.BRIGHT_RED)


class Logger:
    """Colored logger for dataset viewer."""

    def __init__(self, name: str):
        """Initialize logger with module name.

        Args:
            name: Name of the module (e.g., "Parser", "SQLQuery", "Router")
        """
        self.name = name.upper()

    def _get_timestamp(self) -> str:
        """Get current timestamp in HH:MM:SS format."""
        return datetime.now().strftime("%H:%M:%S")

    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format log message with colors and structure.

        Format: [LEVEL][MODULE][Worker:PID][HH:MM:SS] message

        Args:
            level: Log level
            message: Message to log

        Returns:
            Formatted colored string
        """
        level_name, level_color = level.value
        timestamp = self._get_timestamp()
        worker_id = os.getpid()

        # Build formatted message
        parts = [
            f"{level_color}[{level_name}]{Color.RESET}",
            f"{Color.BRIGHT_MAGENTA}[{self.name}]{Color.RESET}",
            f"{Color.BLUE}[W:{worker_id}]{Color.RESET}",
            f"{Color.BRIGHT_BLACK}[{timestamp}]{Color.RESET}",
            message,
        ]

        return " ".join(parts)

    def _log(self, level: LogLevel, message: str):
        """Internal log method."""
        formatted = self._format_message(level, message)
        print(
            formatted,
            file=(sys.stderr if level == LogLevel.ERROR else sys.stdout),
        )

    def debug(self, message: str):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str):
        """Log info message."""
        self._log(LogLevel.INFO, message)

    def success(self, message: str):
        """Log success message."""
        self._log(LogLevel.SUCCESS, message)

    def warning(self, message: str):
        """Log warning message."""
        self._log(LogLevel.WARNING, message)

    def error(self, message: str):
        """Log error message."""
        self._log(LogLevel.ERROR, message)


def get_logger(name: str) -> Logger:
    """Get logger instance.

    Args:
        name: Module name (e.g., "Parser", "SQLQuery")

    Returns:
        Logger instance
    """
    return Logger(name)
