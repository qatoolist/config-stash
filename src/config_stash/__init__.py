"""Config-Stash: A flexible configuration management library for Python applications.

Config-Stash provides a unified interface for loading, merging, and accessing
configuration values from multiple sources with support for environment-specific
configs, dynamic reloading, and hook-based transformations.
"""

import logging
import os
from typing import Optional

from config_stash.config import Config

__version__ = "0.0.1"
__all__ = ["Config", "setup_logging"]


def setup_logging(level: Optional[str] = None) -> None:
    """Configure logging for the config-stash library.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
              If not provided, uses the CONFIG_STASH_LOG_LEVEL environment
              variable or defaults to WARNING.
    """
    log_level = level or os.environ.get("CONFIG_STASH_LOG_LEVEL", "WARNING")

    # Configure the logger for this package
    logger = logging.getLogger("config_stash")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Only add handler if one doesn't exist (to avoid duplicates)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False


# Set up default logging configuration (can be overridden by users)
setup_logging()
