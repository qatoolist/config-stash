"""Loader for INI configuration files."""

import configparser
from pathlib import Path
from typing import Any, Dict, Optional


class IniLoader:
    """Loader for INI configuration files."""

    def __init__(self, source: str):
        """Initialize the INI loader.

        Args:
            source: Path to the INI file
        """
        self.source = source

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from INI file.

        Returns:
            Dictionary containing the configuration from INI file
        """
        if not Path(self.source).exists():
            return None

        # Use RawConfigParser to avoid interpolation of % characters
        parser = configparser.RawConfigParser()
        parser.read(self.source)

        config: Dict[str, Any] = {}

        for section in parser.sections():
            config[section] = {}
            for key, value in parser.items(section):
                # Try to convert values to appropriate types
                if value.lower() == 'true':
                    config[section][key] = True
                elif value.lower() == 'false':
                    config[section][key] = False
                elif value.isdigit():
                    config[section][key] = int(value)
                else:
                    try:
                        config[section][key] = float(value)
                    except ValueError:
                        config[section][key] = value

        return config