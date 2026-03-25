"""JSON configuration loader for Config-Stash.

This module provides the JsonLoader class for loading configuration
from JSON files.
"""

import json
from typing import Any, Dict, Optional

from config_stash.exceptions import ConfigFormatError, ConfigLoadError
from config_stash.loaders.loader import Loader


class JsonLoader(Loader):
    """Loader for JSON configuration files.

    JsonLoader loads configuration data from JSON (.json) files.
    It uses Python's built-in json module to parse the configuration.

    Attributes:
        source: Path to the JSON configuration file
        config: Loaded configuration dictionary

    Example:
        >>> from config_stash.loaders import JsonLoader
        >>> from config_stash import Config
        >>>
        >>> loader = JsonLoader("config.json")
        >>> config = Config(loaders=[loader])
        >>> print(config.database.host)

    Note:
        Missing files are handled gracefully and return None instead of
        raising an exception. This allows for optional configuration files.
    """

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from JSON file.

        This method reads the JSON file specified in the source attribute,
        parses it using Python's json.loads, and returns the configuration
        as a dictionary.

        Returns:
            Dictionary containing the loaded configuration, or None if the
            file doesn't exist (allows for optional configuration files).

        Raises:
            ConfigFormatError: If the JSON file contains invalid syntax or
                cannot be parsed.
            ConfigLoadError: If there's an error reading the file (other than
                file not found).

        Example:
            >>> loader = JsonLoader("config.json")
            >>> config_dict = loader.load()
            >>> if config_dict:
            ...     print(f"Loaded {len(config_dict)} keys")
        """
        try:
            content = self._read_file(self.source)
            self.config = json.loads(content)
        except ConfigLoadError:
            # Gracefully handle missing files and read errors
            return None
        except json.JSONDecodeError as error:
            raise ConfigFormatError(
                f"Invalid JSON syntax in {self.source}: {error}",
                source=self.source,
                format_type="json",
                line_number=getattr(error, "lineno", None),
                column_number=getattr(error, "colno", None),
                original_error=error,
            ) from error
        return self.config
