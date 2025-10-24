import importlib
import logging
from pathlib import Path
from typing import Any, Dict

import toml

logger = logging.getLogger(__name__)


def read_pyproject_config() -> Dict[str, Any]:
    """Read config-stash settings from pyproject.toml.

    Searches for pyproject.toml in multiple locations:
    1. Current working directory
    2. Package installation directory
    3. User's home directory

    Returns:
        Dictionary containing config-stash settings, or empty dict if not found
    """
    # Try multiple locations in order of precedence
    search_paths = [
        Path.cwd() / "pyproject.toml",  # Current directory
        Path(__file__).parent.parent.parent / "pyproject.toml",  # Package directory
        Path.home() / ".config" / "config-stash" / "pyproject.toml",  # User config dir
    ]

    for config_path in search_paths:
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    pyproject = toml.load(f)
                config = pyproject.get("tool", {}).get("config_stash", {})
                logger.debug(f"Loaded config-stash settings from {config_path}")
                return config
        except Exception as e:
            logger.debug(f"Failed to read {config_path}: {e}")
            continue

    logger.warning("No pyproject.toml found with config-stash settings, using defaults")
    return {}


def get_default_loaders():
    config = read_pyproject_config()
    loader_definitions = config.get("loaders", {})
    loaders = {}
    for name, path in loader_definitions.items():
        module_name, class_name = path.split(":")
        module = importlib.import_module(module_name)
        loaders[name] = getattr(module, class_name)
    return loaders


def get_default_settings():
    config = read_pyproject_config()
    settings = {
        "default_environment": config.get("default_environment", "development"),
        "default_files": config.get("default_files", []),
        "default_prefix": config.get("default_prefix", "PREFIX"),
        "dynamic_reloading": config.get("dynamic_reloading", False),
    }
    return settings
