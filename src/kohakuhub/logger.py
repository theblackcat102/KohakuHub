"""Loguru-based logging implementation for KohakuHub."""

import os
import sys
import logging

import traceback as tb
from loguru import logger
from enum import Enum
from typing import Optional

from kohakuhub.config import cfg


class LogLevel(Enum):
    """Log levels mapping to loguru levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRACE = "TRACE"


class InterceptHandler(logging.Handler):
    """
    Logger Interceptor：Redirects standard library logs to Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get Level Name and API name from LogRecord
        try:
            level = logger.level(record.levelname).name
            api_name = record.name.upper()
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.bind(api_name=api_name).opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class Logger:
    """Loguru-based logger"""

    def __init__(self, api_name: str = "APP"):
        """Initialize logger with API name.

        Args:
            api_name: Name of the API/module (e.g., "AUTH", "FILE", "LFS")
        """
        self.api_name = api_name.upper()
        self._logger = logger.bind(api_name=api_name)

    def _log(self, level: LogLevel, message: str):
        """Internal log method."""
        match level:
            case LogLevel.DEBUG:
                self._logger.debug(message)
            case LogLevel.INFO:
                self._logger.info(message)
            case LogLevel.SUCCESS:
                self._logger.success(message)
            case LogLevel.WARNING:
                self._logger.warning(message)
            case LogLevel.ERROR:
                self._logger.error(message)
            case LogLevel.CRITICAL:
                self._logger.critical(message)
            case LogLevel.TRACE:
                self._logger.trace(message)
            case _:
                self._logger.log(level, message)

    def debug(self, message: str):
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str):
        self._log(LogLevel.INFO, message)

    def success(self, message: str):
        self._log(LogLevel.SUCCESS, message)

    def warning(self, message: str):
        self._log(LogLevel.WARNING, message)

    def error(self, message: str):
        self._log(LogLevel.ERROR, message)

    def critical(self, message: str):
        self._log(LogLevel.CRITICAL, message)

    def trace(self, message: str):
        self._log(LogLevel.TRACE, message)

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
        self.trace(f"{'=' * 50}")
        self.trace("TRACEBACK")
        self.trace(f"{'=' * 50}")

        # Print stack frames as tables
        for i, frame in enumerate(frames, 1):
            self._print_frame_table(i, frame, is_last=(i == len(frames)))

        # Print final error table
        self._print_error_table(exc_type, exc_value, frames[-1] if frames else None)

        self.trace(f"{'=' * 50}")

    def _print_frame_table(self, index: int, frame: tb.FrameSummary, is_last: bool):
        """Print single stack frame as a table.

        Args:
            index: Frame index
            frame: Frame summary
            is_last: Whether this is the last frame (error location)
        """
        # loguru only renders colors in format
        # color = "ff0000" if is_last else "09D0EF"

        # Table header
        self.trace(f"┌─ Frame #{index} {' (ERROR HERE)' if is_last else ''}")

        # File
        self.trace(f"│ File: {frame.filename}")

        # Line number
        self.trace(f"│ Line: {frame.lineno}")

        # Function/Code
        if frame.name:
            self.trace(f"│ In:{frame.name}()")

        if frame.line:
            # Show the actual code line
            self.trace(f"│ Code: {frame.line.strip()}")

        self.trace(f"└{'─' * 99}")

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
        self.trace(" EXCEPTION DETAILS ")

        self.trace(f"┌{'─' * 99}")

        # Error type
        self.trace(f"│ Type: {exc_type.__name__}")

        # Error message
        self.trace(f"│ Message: {str(exc_value)}")

        if last_frame:
            # Error location
            self.trace(f"│ Location: {last_frame.filename}:{last_frame.lineno}")

            if last_frame.line:
                # Code that caused error
                self.trace(f"│ Code: {last_frame.line.strip()}")

        self.trace(f"└{'─' * 99}")


class LoggerFactory:
    """Factory to create loguru loggers."""

    _loggers = {}

    @classmethod
    def init_logger_settings(cls):

        log_dir = cfg.app.log_dir
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        log_path = os.path.join(log_dir, "kohakuhub.log")
        log_level = cfg.app.log_level.upper()
        log_format = cfg.app.log_format.lower()
        # Configure loguru format to match existing style

        # Remove default handler
        logger.remove()

        """ About Color codes for loguru.
        Actually, it also support 8bit , Hex , RGB color codes.
        See https://loguru.readthedocs.io/en/stable/api/logger.html#color
        """
        logger.level("DEBUG", color="<fg #222024>")
        logger.level("INFO", color="<fg #09D0EF>")
        logger.level("SUCCESS", color="<fg #66FF00>")
        logger.level("WARNING", color="<fg #FFEB2A>")
        logger.level("ERROR", color="<fg #FF160C>")
        logger.level("CRITICAL", color="<white><bg #FF160C><bold>")
        logger.level("TRACE", color="<fg #FF160C>")

        """Add Defualt Terminal logger"""
        logger.add(
            sys.stderr,
            format="<level>[{level}]</level><fg #FF00CD>[{extra[api_name]}]</fg #FF00CD><blue>[W:{process}]</blue>[{time:HH:mm:ss}] {message}",
            level=log_level,
            colorize=True,
        )

        """Add File logger"""
        if log_format == "file":
            logger.add(
                log_path,
                format="<level>[{level}]</level><fg #FF00CD>[{extra[api_name]}]</fg #FF00CD><blue>[W:{process}]</blue>[{time:HH:mm:ss}] {message}",
                level=log_level,
                rotation="2 MB",
            )

        logger_name_list = [name for name in logging.root.manager.loggerDict]
        for logger_name in logger_name_list:
            _logger = logging.getLogger(logger_name)
            _logger.setLevel(logging.INFO)
            _logger.handlers = []
            if "." not in logger_name:
                _logger.addHandler(InterceptHandler())
            else:
                _logger.propagate = True

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


def init_logger_settings():
    """Initialize logger settings."""
    LoggerFactory.init_logger_settings()


def get_logger(api_name: str) -> Logger:
    """Get logger for specific API.

    Args:
        api_name: Name of the API/module

    Returns:
        Logger instance
    """
    return LoggerFactory.get_logger(api_name)


init_logger_settings()
# Pre-create common loggers
logger_auth = get_logger("AUTH")
logger_file = get_logger("FILE")
logger_lfs = get_logger("LFS")
logger_repo = get_logger("REPO")
logger_org = get_logger("ORG")
logger_settings = get_logger("SETTINGS")
logger_api = get_logger("API")
logger_db = get_logger("DB")
