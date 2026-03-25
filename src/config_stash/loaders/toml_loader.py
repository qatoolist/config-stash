"""TOML configuration loader for Config-Stash.

This module provides the TomlLoader class for loading configuration
from TOML files.
"""

from typing import Any, Dict, Optional

from config_stash.exceptions import ConfigFormatError, ConfigLoadError
from config_stash.utils.toml_compat import TomlDecodeError
from config_stash.utils.toml_compat import loads as toml_loads
from config_stash.loaders.loader import Loader


class TomlLoader(Loader):
    """Loader for TOML configuration files.

    TomlLoader loads configuration data from TOML (.toml) files.
    It uses the toml library to parse the configuration.

    Attributes:
        source: Path to the TOML configuration file
        config: Loaded configuration dictionary

    Example:
        >>> from config_stash.loaders import TomlLoader
        >>> from config_stash import Config
        >>>
        >>> loader = TomlLoader("config.toml")
        >>> config = Config(loaders=[loader])
        >>> print(config.database.host)

    Note:
        Missing files raise ConfigLoadError. Ensure the file exists or
        handle the exception appropriately.
    """

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from TOML file.

        This method reads the TOML file specified in the source attribute,
        parses it using the toml library, and returns the configuration
        as a dictionary.

        Returns:
            Dictionary containing the loaded configuration, or None if the
            file doesn't exist (allows for optional configuration files).

        Raises:
            ConfigFormatError: If the TOML file contains invalid syntax or
                cannot be parsed.
            ConfigLoadError: If there's an error reading the file (other than
                file not found).

        Example:
            >>> loader = TomlLoader("config.toml")
            >>> config_dict = loader.load()
            >>> if config_dict:
            ...     print(f"Loaded {len(config_dict)} keys")
        """
        try:
            content = self._read_file(self.source)
            self.config = toml_loads(content)
        except ConfigLoadError:
            # Gracefully handle missing files and read errors
            return None
        except TomlDecodeError as error:
            raise ConfigFormatError(
                f"Invalid TOML syntax in {self.source}: {error}",
                source=self.source,
                format_type="toml",
                original_error=error,
            ) from error
        return self.config
