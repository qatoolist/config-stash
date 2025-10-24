"""Loader for .env files."""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class EnvFileLoader:
    """Loader for .env files with support for nested configurations."""

    def __init__(self, source: str = ".env"):
        """Initialize the .env file loader.

        Args:
            source: Path to the .env file
        """
        self.source = source

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from .env file.

        Returns:
            Dictionary containing the configuration from .env file
        """
        if not Path(self.source).exists():
            return None

        config: Dict[str, Any] = {}

        with open(self.source, 'r') as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]

                    # Handle escape sequences
                    value = value.replace('\\n', '\n').replace('\\t', '\t')

                    # Convert to appropriate types
                    parsed_value: Any = value
                    if value.lower() == 'true':
                        parsed_value = True
                    elif value.lower() == 'false':
                        parsed_value = False
                    elif value.isdigit():
                        parsed_value = int(value)
                    else:
                        try:
                            parsed_value = float(value)
                        except ValueError:
                            pass  # Keep as string

                    # Support nested keys with dot notation
                    if '.' in key:
                        parts = key.split('.')
                        current = config
                        for part in parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = parsed_value
                    else:
                        config[key] = parsed_value

        return config