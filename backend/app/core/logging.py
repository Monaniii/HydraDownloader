"""Centralised logging configuration for the backend.

Provides a consistent, structured log format across all modules and
writes to both console and a rotating file in the data directory.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(level: str | None = None) -> None:
    """Configure root logging with console + rotating file handlers."""
    log_level = (level or settings.log_level).upper()
    root = logging.getLogger()
    root.setLevel(log_level)

    formatter = logging.Formatter(_FORMAT)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(log_level)
    root.addHandler(console)

    # Rotating file handler
    log_file = settings.log_dir / "hydra.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    root.addHandler(file_handler)

    # Mark noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger."""
    return logging.getLogger(name)


def get_download_logger() -> logging.Logger:
    """Return the dedicated downloads logger writing to downloads.log.

    This logger captures download lifecycle events (started, completed,
    cancelled, retries, errors, performance) in a separate file so they
    are easy to audit and trace.
    """
    logger = logging.getLogger("hydra.downloads")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s"
    )
    file_handler = RotatingFileHandler(
        settings.log_dir / "downloads.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    return logger
