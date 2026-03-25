"""YAML configuration loader for Config-Stash.

This module provides the YamlLoader class for loading configuration
from YAML files.
"""

from typing import Any, Dict, Optional

import yaml

from config_stash.exceptions import ConfigFormatError, ConfigLoadError
from config_stash.loaders.loader import Loader


class YamlLoader(Loader):
    """Loader for YAML configuration files.

    YamlLoader loads configuration data from YAML (.yaml or .yml) files.
    It uses PyYAML's safe_load to parse the configuration, which prevents
    arbitrary code execution.

    Attributes:
        source: Path to the YAML configuration file
        config: Loaded configuration dictionary

    Example:
        >>> from config_stash.loaders import YamlLoader
        >>> from config_stash import Config
        >>>
        >>> loader = YamlLoader("config.yaml")
        >>> config = Config(loaders=[loader])
        >>> print(config.database.host)

    Note:
        Missing files are handled gracefully and return None instead of
        raising an exception. This allows for optional configuration files.
    """

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file.

        This method reads the YAML file specified in the source attribute,
        parses it using PyYAML's safe_load, and returns the configuration
        as a dictionary.

        Returns:
            Dictionary containing the loaded configuration, or None if the
            file doesn't exist (allows for optional configuration files).

        Raises:
            ConfigFormatError: If the YAML file contains invalid syntax or
                cannot be parsed.
            ConfigLoadError: If there's an error reading the file (other than
                file not found).

        Example:
            >>> loader = YamlLoader("config.yaml")
            >>> config_dict = loader.load()
            >>> if config_dict:
            ...     print(f"Loaded {len(config_dict)} keys")
        """
        try:
            content = self._read_file(self.source)
            self.config = yaml.safe_load(content) or {}
        except ConfigLoadError:
            # Gracefully handle missing files and read errors
            return None
        except yaml.YAMLError as error:
            raise ConfigFormatError(
                f"Invalid YAML syntax in {self.source}: {error}",
                source=self.source,
                format_type="yaml",
                original_error=error,
            ) from error
        return self.config
