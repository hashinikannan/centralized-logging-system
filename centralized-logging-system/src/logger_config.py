"""Centralized logging configuration module.

Configures consistent, structured logging across all services.
Each service writes to its own dedicated log file in the `logs/` directory
while adhering to a unified format:
    timestamp | severity | service_name | message
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Root directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

# Standard log format across all services
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_log_dir() -> Path:
    """Ensure and return the logs directory."""
    env_dir = os.getenv("LOG_DIR")
    target_dir = Path(env_dir) if env_dir else LOG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    """Return a consistently configured logger for a service.

    Features:
    - Writes to console (StreamHandler)
    - Writes to a dedicated rotating log file (e.g. `logs/<name>.log`)
    - Consistent timestamp, severity, service, and message format
    - Idempotent: prevents duplicate handlers if called multiple times
    - Safe for Windows paths and UTF-8 encoding

    Args:
        name: Name of the service or component (e.g. 'login_service', 'payment_service')
        log_file: Optional explicit log filename. If omitted, defaults to `<name>.log`.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers if this logger was already initialized
    if logger.handlers:
        return logger

    # Resolve log level from environment or default to INFO
    env_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    configured_level = getattr(logging, env_level, logging.INFO)
    logger.setLevel(configured_level)
    logger.propagate = False

    # Create unified formatter
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # 1. Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(configured_level)
    logger.addHandler(console_handler)

    # 2. File handler (dedicated per service)
    log_dir = get_log_dir()
    target_filename = log_file if log_file else f"{name}.log"
    file_path = log_dir / target_filename

    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=2_000_000,  # 2 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(configured_level)
    logger.addHandler(file_handler)

    return logger
