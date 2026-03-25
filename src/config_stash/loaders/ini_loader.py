"""Loader for INI configuration files."""

import configparser
from pathlib import Path
from typing import Any, Dict, Optional

from config_stash.loaders.loader import Loader


class IniLoader(Loader):
    """Loader for INI configuration files.

    IniLoader loads configuration data from INI (.ini or .cfg) files using
    Python's ``configparser.RawConfigParser``. The raw parser is used to
    avoid interpolation of ``%`` characters that may appear in configuration
    values such as connection strings or format patterns.

    Each INI section becomes a top-level key in the resulting dictionary,
    with the section's key-value pairs nested underneath. Scalar values
    are automatically coerced to appropriate Python types (int, float,
    bool, None) via ``parse_scalar_value``.

    Attributes:
        source: Path to the INI configuration file.
        config: Loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders import IniLoader
        >>> from config_stash import Config
        >>>
        >>> loader = IniLoader("database.ini")
        >>> config = Config(loaders=[loader])
        >>> print(config.database.host)

    Note:
        Missing files are handled gracefully and return None instead of
        raising an exception. This allows for optional configuration files.
        The ``DEFAULT`` section in INI files is not included as a separate
        key; its values are inherited by other sections per standard
        configparser behavior.
    """

    def __init__(self, source: str):
        """Initialize the INI loader.

        Args:
            source: Path to the INI file.
        """
        super().__init__(source)

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from an INI file.

        Reads the INI file, parses each section into a nested dictionary,
        and coerces scalar values to their appropriate Python types.

        Returns:
            Dictionary containing the loaded configuration keyed by section
            name, or None if the file does not exist or is unreadable.

        Raises:
            configparser.MissingSectionHeaderError: If the file is not valid
                INI format (missing section headers).

        Example:
            >>> loader = IniLoader("app.ini")
            >>> config_dict = loader.load()
            >>> if config_dict:
            ...     print(config_dict["database"]["host"])
        """
        if not Path(self.source).exists():
            return None

        # Use RawConfigParser to avoid interpolation of % characters
        parser = configparser.RawConfigParser()
        read_ok = parser.read(self.source)
        if not read_ok:
            # parser.read() silently ignores unreadable files
            return None

        config: Dict[str, Any] = {}

        for section in parser.sections():
            config[section] = {}
            for key, value in parser.items(section):
                from config_stash.utils.type_coercion import parse_scalar_value

                config[section][key] = parse_scalar_value(value)

        return config
