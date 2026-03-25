"""Loader for .env files."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from config_stash.loaders.loader import Loader


class EnvFileLoader(Loader):
    """Loader for .env files with support for nested configurations."""

    def __init__(self, source: str = ".env"):
        """Initialize the .env file loader.

        Args:
            source: Path to the .env file
        """
        super().__init__(source)

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from .env file.

        Returns:
            Dictionary containing the configuration from .env file
        """
        if not Path(self.source).exists():
            return None

        config: Dict[str, Any] = {}

        with open(self.source, "r") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE format
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Strip inline comments (only for unquoted values)
                    quote_char = None
                    if value and value[0] == value[-1] and value[0] in ('"', "'"):
                        quote_char = value[0]
                        value = value[1:-1]
                    else:
                        # Strip inline comments for unquoted values
                        comment_idx = value.find(" #")
                        if comment_idx != -1:
                            value = value[:comment_idx].rstrip()

                    # Handle escape sequences only for double-quoted values
                    if quote_char != "'":
                        value = value.replace("\\n", "\n").replace("\\t", "\t")

                    # Convert to appropriate types
                    from config_stash.utils.type_coercion import parse_scalar_value

                    parsed_value: Any = parse_scalar_value(value)

                    # Support nested keys with dot notation
                    if "." in key:
                        parts = key.split(".")
                        current = config
                        for part in parts[:-1]:
                            if part not in current or not isinstance(current[part], dict):
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = parsed_value
                    else:
                        config[key] = parsed_value

        return config
