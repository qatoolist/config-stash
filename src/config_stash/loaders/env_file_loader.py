"""Loader for .env files."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from config_stash.loaders.loader import Loader


class EnvFileLoader(Loader):
    """Loader for .env files with support for nested configurations.

    EnvFileLoader parses ``.env`` files in the standard ``KEY=VALUE`` format
    used by tools such as Docker Compose, Heroku, and direnv. It supports
    quoted values, inline comments, escape sequences in double-quoted
    strings, and nested key structures via dot notation.

    Attributes:
        source: Path to the ``.env`` configuration file.
        config: Loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders import EnvFileLoader
        >>> from config_stash import Config
        >>>
        >>> loader = EnvFileLoader(".env")
        >>> config = Config(loaders=[loader])
        >>> print(config.DATABASE_URL)

    Note:
        The ``.env`` format supports the following features:

        - Comments: lines starting with ``#`` are ignored.
        - Quoting: values wrapped in single or double quotes have the
          quotes stripped. Single-quoted values are treated literally;
          double-quoted values process ``\\n`` and ``\\t`` escapes.
        - Inline comments: ``VALUE # comment`` is supported for unquoted
          values (the ``# comment`` part is stripped).
        - Nested keys: dot-separated keys like ``database.host=localhost``
          are expanded into nested dictionaries.
        - Type coercion: values are automatically converted to int, float,
          bool, or None where appropriate.
        - Missing files return None instead of raising an exception.
    """

    def __init__(self, source: str = ".env"):
        """Initialize the .env file loader.

        Args:
            source: Path to the .env file. Defaults to ``".env"`` in the
                current working directory.
        """
        super().__init__(source)

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from a .env file.

        Parses each ``KEY=VALUE`` line, strips quotes, handles escape
        sequences, expands dot-notation keys into nested dictionaries,
        and coerces scalar values to appropriate Python types.

        Returns:
            Dictionary containing the loaded configuration, or None if the
            file does not exist.

        Raises:
            PermissionError: If the file exists but is not readable.
            UnicodeDecodeError: If the file contains non-UTF-8 content.

        Example:
            >>> loader = EnvFileLoader(".env.production")
            >>> config_dict = loader.load()
            >>> if config_dict:
            ...     print(config_dict["database"]["host"])
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
                            if part not in current or not isinstance(
                                current[part], dict
                            ):
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = parsed_value
                    else:
                        config[key] = parsed_value

        return config
