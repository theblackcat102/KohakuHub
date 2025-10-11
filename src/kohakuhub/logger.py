"""Custom logging module for KohakuHub with colored output and formatted tracebacks."""

import os
import sys
import traceback as tb
from datetime import datetime
from enum import Enum
from typing import Optional


class Color:
    """ANSI color codes for terminal output."""

    # Text colors
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    # Text styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"


class LogLevel(Enum):
    """Log levels with associated colors."""

    DEBUG = ("DEBUG", Color.BRIGHT_BLACK)
    INFO = ("INFO", Color.BRIGHT_CYAN)
    SUCCESS = ("SUCCESS", Color.BRIGHT_GREEN)
    WARNING = ("WARNING", Color.BRIGHT_YELLOW)
    ERROR = ("ERROR", Color.BRIGHT_RED)
    CRITICAL = ("CRITICAL", Color.BG_RED + Color.WHITE + Color.BOLD)


class Logger:
    """Custom logger with API name prefix and colored output."""

    def __init__(self, api_name: str = "APP"):
        """Initialize logger with API name.

        Args:
            api_name: Name of the API/module (e.g., "AUTH", "FILE", "LFS")
        """
        self.api_name = api_name.upper()

    def _get_timestamp(self) -> str:
        """Get current timestamp in HH:MM:SS format."""
        return datetime.now().strftime("%H:%M:%S")

    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format log message with colors and structure.

        Format: [LEVEL][API-NAME][Worker:PID][HH:MM:SS] message

        Args:
            level: Log level
            message: Message to log

        Returns:
            Formatted colored string
        """
        level_name, level_color = level.value
        timestamp = self._get_timestamp()
        worker_id = os.getpid()  # Process ID identifies the worker

        # Build formatted message
        parts = [
            f"{level_color}[{level_name}]{Color.RESET}",
            f"{Color.BRIGHT_MAGENTA}[{self.api_name}]{Color.RESET}",
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
            file=(
                sys.stderr
                if level in [LogLevel.ERROR, LogLevel.CRITICAL]
                else sys.stdout
            ),
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

    def critical(self, message: str):
        """Log critical error message."""
        self._log(LogLevel.CRITICAL, message)

    def exception(self, message: str, exc: Optional[Exception] = None):
        """Log exception with formatted traceback.

        Args:
            message: Error message
            exc: Exception object (if None, uses sys.exc_info())
        """
        self.error(message)
        self._print_formatted_traceback(exc)

    def _print_formatted_traceback(self, exc: Optional[Exception] = None):
        """Print formatted traceback as tables.

        Format:
        1. Stack trace table for each frame
        2. Final error table with actual error details

        Args:
            exc: Exception object (if None, uses sys.exc_info())
        """
        if exc is None:
            exc_type, exc_value, exc_tb = sys.exc_info()
        else:
            exc_type = type(exc)
            exc_value = exc
            exc_tb = exc.__traceback__

        if exc_tb is None:
            return

        # Extract traceback frames
        frames = tb.extract_tb(exc_tb)

        # Print header
        print(f"\n{Color.BRIGHT_RED}{'═' * 100}{Color.RESET}", file=sys.stderr)
        print(f"{Color.BRIGHT_RED}{Color.BOLD}TRACEBACK{Color.RESET}", file=sys.stderr)
        print(f"{Color.BRIGHT_RED}{'═' * 100}{Color.RESET}\n", file=sys.stderr)

        # Print stack frames as tables
        for i, frame in enumerate(frames, 1):
            self._print_frame_table(i, frame, is_last=(i == len(frames)))

        # Print final error table
        self._print_error_table(exc_type, exc_value, frames[-1] if frames else None)

        print(f"{Color.BRIGHT_RED}{'═' * 100}{Color.RESET}\n", file=sys.stderr)

    def _print_frame_table(self, index: int, frame: tb.FrameSummary, is_last: bool):
        """Print single stack frame as a table.

        Args:
            index: Frame index
            frame: Frame summary
            is_last: Whether this is the last frame (error location)
        """
        color = Color.BRIGHT_RED if is_last else Color.BRIGHT_BLACK

        # Table header
        print(
            f"{color}┌─ Frame #{index} {' (ERROR HERE)' if is_last else ''}",
            file=sys.stderr,
        )

        # File
        print(
            f"{color}│ {Color.CYAN}File:{Color.RESET} {frame.filename}", file=sys.stderr
        )

        # Line number
        print(
            f"{color}│ {Color.YELLOW}Line:{Color.RESET} {frame.lineno}", file=sys.stderr
        )

        # Function/Code
        if frame.name:
            print(
                f"{color}│ {Color.GREEN}In:{Color.RESET} {frame.name}()",
                file=sys.stderr,
            )

        if frame.line:
            # Show the actual code line
            print(
                f"{color}│ {Color.BRIGHT_WHITE}Code:{Color.RESET} {frame.line.strip()}",
                file=sys.stderr,
            )

        print(f"{color}└{'─' * 99}{Color.RESET}\n", file=sys.stderr)

    def _print_error_table(
        self, exc_type, exc_value, last_frame: Optional[tb.FrameSummary]
    ):
        """Print final error details as a table.

        Args:
            exc_type: Exception type
            exc_value: Exception value
            last_frame: Last stack frame (error location)
        """
        # Table header
        print(
            f"{Color.BG_RED}{Color.WHITE}{Color.BOLD} EXCEPTION DETAILS {Color.RESET}",
            file=sys.stderr,
        )
        print(f"{Color.BRIGHT_RED}┌{'─' * 99}", file=sys.stderr)

        # Error type
        print(
            f"{Color.BRIGHT_RED}│ {Color.BOLD}Type:{Color.RESET} {Color.BRIGHT_RED}{exc_type.__name__}{Color.RESET}",
            file=sys.stderr,
        )

        # Error message
        print(
            f"{Color.BRIGHT_RED}│ {Color.BOLD}Message:{Color.RESET} {Color.WHITE}{str(exc_value)}{Color.RESET}",
            file=sys.stderr,
        )

        if last_frame:
            # Error location
            print(
                f"{Color.BRIGHT_RED}│ {Color.BOLD}Location:{Color.RESET} {Color.CYAN}{last_frame.filename}{Color.RESET}:{Color.YELLOW}{last_frame.lineno}{Color.RESET}",
                file=sys.stderr,
            )

            if last_frame.line:
                # Code that caused error
                print(
                    f"{Color.BRIGHT_RED}│ {Color.BOLD}Code:{Color.RESET} {Color.BRIGHT_WHITE}{last_frame.line.strip()}{Color.RESET}",
                    file=sys.stderr,
                )

        print(f"{Color.BRIGHT_RED}└{'─' * 99}{Color.RESET}", file=sys.stderr)


class LoggerFactory:
    """Factory to create loggers with different API names."""

    _loggers = {}

    @classmethod
    def get_logger(cls, api_name: str) -> Logger:
        """Get or create logger for API name.

        Args:
            api_name: Name of the API/module

        Returns:
            Logger instance
        """
        if api_name not in cls._loggers:
            cls._loggers[api_name] = Logger(api_name)
        return cls._loggers[api_name]


# Convenience function for getting logger
def get_logger(api_name: str) -> Logger:
    """Get logger for specific API.

    Usage:
        logger = get_logger("AUTH")
        logger.info("User logged in")
        logger.error("Login failed")

        try:
            # ... code ...
        except Exception as e:
            logger.exception("Failed to process request", e)

    Args:
        api_name: Name of the API/module (e.g., "AUTH", "FILE", "LFS")

    Returns:
        Logger instance
    """
    return LoggerFactory.get_logger(api_name)


# Pre-create common loggers
logger_auth = get_logger("AUTH")
logger_file = get_logger("FILE")
logger_lfs = get_logger("LFS")
logger_repo = get_logger("REPO")
logger_org = get_logger("ORG")
logger_settings = get_logger("SETTINGS")
logger_api = get_logger("API")
logger_db = get_logger("DB")
