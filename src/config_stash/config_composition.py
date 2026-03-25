"""Configuration composition system for Config-Stash.

This module provides support for composing configurations from multiple sources
using includes, defaults, and other composition directives similar to Hydra.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from config_stash.exceptions import ConfigLoadError
from config_stash.loaders.loader import Loader

logger = logging.getLogger(__name__)

# Special keys for composition directives
INCLUDE_KEY = "_include"
DEFAULTS_KEY = "_defaults"
MERGE_STRATEGY_KEY = "_merge_strategy"


class ConfigComposer:
    """Handles composition of configurations with includes and defaults.

    This class processes composition directives in configuration files,
    such as _include and _defaults, to build composite configurations.
    It supports recursive composition with cycle detection.

    Example:
        >>> composer = ConfigComposer(base_path="/config", loaders=[YamlLoader])
        >>> # Config file with _include directive:
        >>> # config.yaml:
        >>> #   _include: ["base.yaml", "features.yaml"]
        >>> #   app:
        >>> #     name: MyApp
        >>> composed = composer.compose(config_dict, source="config.yaml")
    """

    def __init__(
        self,
        base_path: Optional[str] = None,
        loaders: Optional[List[Loader]] = None,
    ) -> None:
        """Initialize the config composer.

        Args:
            base_path: Base path for resolving relative file paths in includes
            loaders: List of loaders to use for loading included files
        """
        self.base_path = base_path or os.getcwd()
        self.loaders = loaders or []
        self._loaded_files: Set[str] = set()  # Track loaded files to prevent cycles

    def compose(self, config: Dict[str, Any], source: str = "", depth: int = 0) -> Dict[str, Any]:
        """Compose a configuration by processing includes and defaults.

        Args:
            config: Configuration dictionary to compose
            source: Source file path (for resolving relative includes)
            depth: Current composition depth (for cycle detection)

        Returns:
            Composed configuration dictionary

        Raises:
            ConfigLoadError: If composition fails (e.g., circular includes)
        """
        if depth > 10:  # Prevent infinite recursion
            raise ConfigLoadError(
                f"Maximum composition depth exceeded. Possible circular include in {source}",
                source=source,
            )

        # Clear loaded files tracking at the start of a top-level compose
        if depth == 0:
            self._loaded_files.clear()

        # Work on a copy to avoid mutating the input
        config = dict(config)

        # Process defaults first (they provide base values)
        if DEFAULTS_KEY in config:
            defaults = config.pop(DEFAULTS_KEY)
            config = self._process_defaults(defaults, config, source)

        # Process includes (they merge additional configs)
        if INCLUDE_KEY in config:
            includes = config.pop(INCLUDE_KEY)
            config = self._process_includes(includes, config, source, depth)

        # Remove composition directives from final config
        config.pop(MERGE_STRATEGY_KEY, None)

        return config

    def _process_defaults(
        self, defaults: Any, config: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """Process defaults list to build base configuration.

        Args:
            defaults: Defaults specification (list of strings or dicts)
            config: Current configuration
            source: Source file path

        Returns:
            Configuration with defaults applied
        """
        if not isinstance(defaults, list):
            logger.warning(f"Invalid defaults format in {source}, expected list")
            return config

        base_config: Dict[str, Any] = {}

        for default_spec in defaults:
            if isinstance(default_spec, str):
                # Simple string: "database: postgres"
                parts = default_spec.split(":", 1)
                if len(parts) == 2:
                    key, value = parts[0].strip(), parts[1].strip()
                    base_config[key] = value
            elif isinstance(default_spec, dict):
                # Dict with options: {"database": "postgres", "optional": true}
                for key, value in default_spec.items():
                    if key != "optional":
                        base_config[key] = value

        # Merge defaults into config (defaults are base, config overrides)
        return self._merge_dicts(base_config, config)

    def _process_includes(
        self,
        includes: Any,
        config: Dict[str, Any],
        source: str,
        depth: int,
    ) -> Dict[str, Any]:
        """Process includes to merge additional configuration files.

        Args:
            includes: Include specification (string or list of strings)
            config: Current configuration
            source: Source file path
            depth: Current composition depth

        Returns:
            Configuration with includes merged

        Raises:
            ConfigLoadError: If include files cannot be loaded
        """
        if isinstance(includes, str):
            includes = [includes]
        elif not isinstance(includes, list):
            logger.warning(f"Invalid include format in {source}, expected string or list")
            return config

        # Resolve base directory from source file
        if source:
            base_dir = os.path.dirname(os.path.abspath(source)) or self.base_path
        else:
            base_dir = self.base_path

        for include_path in includes:
            if not isinstance(include_path, str):
                continue

            # Resolve include path (relative to source file or absolute)
            if os.path.isabs(include_path):
                full_path = include_path
            else:
                full_path = os.path.join(base_dir, include_path)

            # Normalize path
            full_path = os.path.normpath(full_path)

            # Check for circular includes
            if full_path in self._loaded_files:
                logger.warning(f"Circular include detected: {full_path}, skipping")
                continue

            # Load included configuration
            try:
                included_config = self._load_include(full_path, depth)
                if included_config:
                    # Merge included config into current config
                    config = self._merge_dicts(config, included_config)
            except Exception as e:
                logger.warning(f"Failed to load include {include_path}: {e}")
                # Continue with other includes even if one fails

        return config

    def _load_include(self, file_path: str, depth: int) -> Optional[Dict[str, Any]]:
        """Load an included configuration file.

        Args:
            file_path: Path to the file to include
            depth: Current composition depth

        Returns:
            Loaded configuration dictionary, or None if file not found

        Raises:
            ConfigLoadError: If file cannot be loaded
        """
        if not os.path.exists(file_path):
            logger.warning(f"Include file not found: {file_path}")
            return None

        # Detect file type and load
        ext = Path(file_path).suffix.lower()
        self._loaded_files.add(file_path)

        try:
            if ext in (".yaml", ".yml"):
                import yaml

                with open(file_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            elif ext == ".json":
                import json

                with open(file_path, "r", encoding="utf-8") as f:
                    config = json.load(f) or {}
            elif ext == ".toml":
                from config_stash.utils.toml_compat import load_file as toml_load_file

                config = toml_load_file(file_path) or {}
            else:
                logger.warning(f"Unknown file type for include: {file_path}")
                return None

            # Recursively compose the included config
            config = self.compose(config, file_path, depth + 1)

            return config
        except Exception as e:
            raise ConfigLoadError(
                f"Failed to load include file {file_path}",
                source=file_path,
                original_error=e,
            ) from e
        finally:
            pass  # Keep file in _loaded_files to prevent duplicate inclusion

    def _merge_dicts(self, base: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary
            new: New configuration to merge in

        Returns:
            Merged configuration dictionary
        """
        from config_stash.utils.dict_utils import deep_merge_dicts

        return deep_merge_dicts(
            base, new,
            skip_keys={INCLUDE_KEY, DEFAULTS_KEY, MERGE_STRATEGY_KEY},
        )
        return result


def process_composition(
    config: Dict[str, Any],
    source: str = "",
    base_path: Optional[str] = None,
    loaders: Optional[List[Loader]] = None,
) -> Dict[str, Any]:
    """Process composition directives in a configuration.

    This is a convenience function for processing includes and defaults
    in a configuration dictionary.

    Args:
        config: Configuration dictionary to process
        source: Source file path (for resolving relative includes)
        base_path: Base path for resolving relative file paths
        loaders: Optional list of loaders for loading includes

    Returns:
        Composed configuration dictionary

    Example:
        >>> config = {
        ...     "_include": ["common.yaml", "secrets.yaml"],
        ...     "database": {"host": "localhost"}
        ... }
        >>> composed = process_composition(config, source="config.yaml")
    """
    composer = ConfigComposer(base_path=base_path, loaders=loaders)
    return composer.compose(config, source=source)
