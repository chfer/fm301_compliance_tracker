"""Logging setup for the tracker."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import LoggingConfig


def configure_logging(config: LoggingConfig, verbose: bool) -> logging.Logger:
    """Create the tracker logger with rotating file and optional console output."""
    logger = logging.getLogger("fm301_compliance_tracker")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Create the log directory because it may not exist in a new checkout.
    config.file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        config.file, maxBytes=config.max_size, backupCount=config.backup_count, encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, config.level.upper(), logging.INFO))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if verbose:
        # File logs follow the configured level; verbose mode shows all details on the console.
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger