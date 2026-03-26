"""Configuration reader for loading config-stash defaults.

This module reads self-configuration from dedicated ``config-stash.*`` files
(YAML, JSON, or TOML) or falls back to the ``[tool.config_stash]`` section
of ``pyproject.toml``.

Search order for the self-configuration file:

1. ``config-stash.yaml``, ``config-stash.yml``, ``config-stash.json``,
   ``config-stash.toml`` in the current working directory.
2. Hidden variants: ``.config-stash.yaml``, ``.config-stash.yml``,
   ``.config-stash.json``, ``.config-stash.toml`` in the current working
   directory.
3. ``pyproject.toml`` ``[tool.config_stash]`` section (cwd, package dir,
   user config dir).

Use ``get_default_loaders()`` to retrieve custom loader class mappings and
``get_default_settings()`` to retrieve general application defaults.

Example:
    >>> from config_stash.config_reader import get_default_settings
    >>> settings = get_default_settings()
    >>> settings["default_environment"]
    'development'
"""

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from config_stash.utils.toml_compat import load_file as toml_load_file

logger = logging.getLogger(__name__)

# Filenames to search, in priority order
_CONFIG_STASH_FILENAMES = [
    "config-stash.yaml",
    "config-stash.yml",
    "config-stash.json",
    "config-stash.toml",
    ".config-stash.yaml",
    ".config-stash.yml",
    ".config-stash.json",
    ".config-stash.toml",
]


def _load_yaml_file(path: str) -> Dict[str, Any]:
    """Load a YAML file and return its contents as a dictionary."""
    import yaml

    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_json_file(path: str) -> Dict[str, Any]:
    """Load a JSON file and return its contents as a dictionary."""
    with open(path, "r") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _load_toml_file(path: str) -> Dict[str, Any]:
    """Load a TOML file and return its contents as a dictionary."""
    return toml_load_file(path)


def _load_config_file(path: Path) -> Dict[str, Any]:
    """Load a config-stash self-configuration file based on its extension.

    Args:
        path: Path to the configuration file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ValueError: If the file extension is not supported.
    """
    suffix = path.suffix.lower()
    path_str = str(path)

    if suffix in (".yaml", ".yml"):
        return _load_yaml_file(path_str)
    elif suffix == ".json":
        return _load_json_file(path_str)
    elif suffix == ".toml":
        return _load_toml_file(path_str)
    else:
        raise ValueError(f"Unsupported config-stash file format: {suffix}")


def read_config_stash_file(search_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Search for and read a ``config-stash.*`` self-configuration file.

    Looks for config-stash.yaml/.yml/.json/.toml (and hidden-file variants)
    in the given directory (defaults to cwd).

    Args:
        search_dir: Directory to search in.  Defaults to the current working
            directory.

    Returns:
        Parsed configuration dictionary, or ``None`` if no file was found.
    """
    base = Path(search_dir) if search_dir else Path.cwd()

    for filename in _CONFIG_STASH_FILENAMES:
        config_path = base / filename
        try:
            if config_path.exists():
                config = _load_config_file(config_path)
                logger.debug(f"Loaded config-stash settings from {config_path}")
                return config
        except Exception as e:
            logger.debug(f"Failed to read {config_path}: {e}")
            continue

    return None


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


def read_self_config(search_dir: Optional[str] = None) -> Dict[str, Any]:
    """Read config-stash self-configuration.

    Searches for a dedicated ``config-stash.*`` file first, then falls back
    to ``[tool.config_stash]`` in ``pyproject.toml``.

    Args:
        search_dir: Directory to search in.  Defaults to the current working
            directory.

    Returns:
        Configuration dictionary (may be empty if nothing was found).
    """
    # Try dedicated config-stash file first
    config = read_config_stash_file(search_dir=search_dir)
    if config is not None:
        return config

    # Fall back to pyproject.toml
    return read_pyproject_config()


# All supported settings with their defaults
_DEFAULT_SETTINGS: Dict[str, Any] = {
    # Environment
    "default_environment": "development",
    "env_switcher": None,
    # Sources
    "default_files": [],
    "default_prefix": "PREFIX",
    "env_prefix": None,
    "sysenv_fallback": False,
    # Merging
    "deep_merge": True,
    "merge_strategy": None,
    "merge_strategy_map": {},
    # Validation
    "validate_on_load": False,
    "strict_validation": False,
    # Hooks
    "use_env_expander": True,
    "use_type_casting": True,
    # Reloading
    "dynamic_reloading": False,
    "incremental_reload": True,
    # Secret Resolution
    "secret_cache_ttl": 300,
    # Observability
    "enable_observability": False,
    "enable_events": False,
    "max_reload_durations": 1000,
    # Versioning
    "enable_versioning": False,
    "version_storage_path": ".config_stash/versions",
    "max_versions": 100,
    # IDE Support
    "enable_ide_support": True,
    "ide_stub_path": None,
    # Debug
    "debug_mode": False,
    "log_level": "WARNING",
    # Loaders (custom)
    "loaders": {},
}


def get_default_loaders() -> Dict[str, Any]:
    """Load custom loader class mappings from configuration.

    Reads the ``loaders`` table from the self-configuration file (or
    ``[tool.config_stash.loaders]`` in pyproject.toml) and dynamically
    imports each loader class specified there.

    Returns:
        A dictionary mapping loader names to their imported Python classes.

    Raises:
        ModuleNotFoundError: If a referenced module cannot be imported.
        AttributeError: If the class name does not exist in the module.
        ValueError: If a loader path string does not contain a ``:`` separator.

    Example:
        Given a ``config-stash.yaml``::

            loaders:
              consul: my_plugins.consul_loader:ConsulLoader

        >>> loaders = get_default_loaders()
        >>> loaders
        {'consul': <class 'my_plugins.consul_loader.ConsulLoader'>}
    """
    config = read_self_config()
    loader_definitions = config.get("loaders", {})
    loaders = {}
    for name, path in loader_definitions.items():
        module_name, class_name = path.split(":")
        module = importlib.import_module(module_name)
        loaders[name] = getattr(module, class_name)
    return loaders


def get_default_settings() -> Dict[str, Any]:
    """Retrieve default application settings from self-configuration.

    Reads from a ``config-stash.*`` file first, falling back to
    ``[tool.config_stash]`` in ``pyproject.toml``.

    The returned dictionary contains all supported settings with their
    defaults applied for any missing keys.

    Returns:
        A dictionary of setting names to their values.

    Example:
        >>> settings = get_default_settings()
        >>> settings["default_environment"]
        'development'
        >>> settings["dynamic_reloading"]
        False
    """
    config = read_self_config()
    settings = {}
    for key, default in _DEFAULT_SETTINGS.items():
        settings[key] = config.get(key, default)
    return settings
