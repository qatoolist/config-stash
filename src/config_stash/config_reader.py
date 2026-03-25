"""Configuration reader for loading config-stash defaults from pyproject.toml.

This module reads the ``[tool.config_stash]`` section of ``pyproject.toml`` to
discover project-level defaults such as custom loader classes, the default
environment name, default configuration files, and feature flags like dynamic
reloading.

The lookup order for ``pyproject.toml`` is:

1. Current working directory
2. The config-stash package installation directory
3. ``~/.config/config-stash/``

Use ``get_default_loaders()`` to retrieve custom loader class mappings and
``get_default_settings()`` to retrieve general application defaults.

Example:
    >>> from config_stash.config_reader import get_default_settings
    >>> settings = get_default_settings()
    >>> settings["default_environment"]
    'development'
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict

from config_stash.utils.toml_compat import load_file as toml_load_file

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
                pyproject = toml_load_file(str(config_path))
                config = pyproject.get("tool", {}).get("config_stash", {})
                logger.debug(f"Loaded config-stash settings from {config_path}")
                return config
        except Exception as e:
            logger.debug(f"Failed to read {config_path}: {e}")
            continue

    logger.warning("No pyproject.toml found with config-stash settings, using defaults")
    return {}


def get_default_loaders():
    """Load custom loader class mappings from pyproject.toml.

    Reads the ``[tool.config_stash.loaders]`` table and dynamically imports
    each loader class specified there.  Each entry should map a short name to
    a fully qualified ``module_path:ClassName`` string.

    Returns:
        A dictionary mapping loader names (strings) to their imported Python
        classes.  Returns an empty dictionary if no loaders are configured.

    Raises:
        ModuleNotFoundError: If a module referenced in the loader definition
            cannot be imported.
        AttributeError: If the class name does not exist in the specified
            module.
        ValueError: If a loader path string does not contain a ``:``
            separator.

    Example:
        Given the following ``pyproject.toml`` snippet::

            [tool.config_stash.loaders]
            consul = "my_plugins.consul_loader:ConsulLoader"

        >>> loaders = get_default_loaders()
        >>> loaders
        {'consul': <class 'my_plugins.consul_loader.ConsulLoader'>}
    """
    config = read_pyproject_config()
    loader_definitions = config.get("loaders", {})
    loaders = {}
    for name, path in loader_definitions.items():
        module_name, class_name = path.split(":")
        module = importlib.import_module(module_name)
        loaders[name] = getattr(module, class_name)
    return loaders


def get_default_settings():
    """Retrieve default application settings from pyproject.toml.

    Reads the ``[tool.config_stash]`` section and extracts commonly used
    settings, falling back to sensible defaults when a setting is absent.

    The returned dictionary always contains the following keys:

    * ``default_environment`` -- The environment name (default ``"development"``).
    * ``default_files`` -- A list of configuration file paths to load by
      default (default ``[]``).
    * ``default_prefix`` -- The environment-variable prefix used by the
      environment loader (default ``"PREFIX"``).
    * ``dynamic_reloading`` -- Whether to watch for file changes and reload
      automatically (default ``False``).

    Returns:
        A dictionary of setting names to their values.

    Example:
        >>> settings = get_default_settings()
        >>> settings["default_environment"]
        'development'
        >>> settings["dynamic_reloading"]
        False
    """
    config = read_pyproject_config()
    settings = {
        "default_environment": config.get("default_environment", "development"),
        "default_files": config.get("default_files", []),
        "default_prefix": config.get("default_prefix", "PREFIX"),
        "dynamic_reloading": config.get("dynamic_reloading", False),
    }
    return settings
