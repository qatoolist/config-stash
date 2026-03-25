"""Loader for INI configuration files."""

import configparser
from pathlib import Path
from typing import Any, Dict, Optional

from config_stash.loaders.loader import Loader


class IniLoader(Loader):
    """Loader for INI configuration files."""

    def __init__(self, source: str):
        """Initialize the INI loader.

        Args:
            source: Path to the INI file
        """
        super().__init__(source)

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from INI file.

        Returns:
            Dictionary containing the configuration from INI file
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
