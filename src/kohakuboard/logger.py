"""Logging configuration for KohakuBoard"""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""

    COLORS = {
        "DEBUG": "\033[0;36m",  # Cyan
        "INFO": "\033[0;32m",  # Green
        "WARNING": "\033[0;33m",  # Yellow
        "ERROR": "\033[0;31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        record.name = f"\033[0;35m[{record.name}]{self.RESET}"
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """Get a colored logger instance"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColoredFormatter("%(name)s %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


# Pre-created loggers
logger_api = get_logger("API")
logger_mock = get_logger("MOCK")
