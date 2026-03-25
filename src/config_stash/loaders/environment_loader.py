import os
from typing import Any, Dict, List, Optional

from config_stash.exceptions import ConfigLoadError
from config_stash.loaders.loader import Loader


class EnvironmentLoader(Loader):
    """Loader for environment variables with prefix support.

    This loader reads environment variables with a specific prefix and
    converts them into a nested configuration structure.
    """

    def __init__(self, prefix: str, separator: str = "__") -> None:
        """Initialize the environment loader.

        Args:
            prefix: Prefix for environment variables to load (e.g., "APP")
            separator: Separator for nested keys (default: "__")
                      Example: APP_DATABASE__HOST -> database.host
        """
        super().__init__(source=f"environment:{prefix}")
        self.prefix: str = prefix.upper()
        self.separator: str = separator
        self.config: Dict[str, Any] = {}

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from environment variables.

        Returns:
            Dictionary containing loaded environment variables, or None if
            no matching environment variables found.

        Raises:
            ConfigLoadError: If loading fails due to an error
        """
        try:
            # Reset config to avoid stale keys from previous loads
            self.config = {}

            # Match env vars that start with prefix followed by underscore
            # e.g., "APP_" matches "APP_DATABASE", but not "APPLET_"
            prefix_with_underscore = f"{self.prefix}_"
            env_vars = {
                key: value
                for key, value in os.environ.items()
                if key.startswith(prefix_with_underscore)
            }

            if not env_vars:
                # No matching environment variables found - return None
                return None

            for key, value in env_vars.items():
                # Remove prefix and initial underscore
                key_without_prefix = key[len(self.prefix) :]
                if key_without_prefix.startswith("_"):
                    key_without_prefix = key_without_prefix[1:]

                # Split by separator for nested keys
                nested_keys = key_without_prefix.split(self.separator)
                self._set_nested_value(self.config, nested_keys, value)

            return self.config
        except ConfigLoadError:
            # Re-raise ConfigLoadError as-is
            raise
        except Exception as e:
            raise ConfigLoadError(
                f"Unexpected error loading environment variables with prefix {self.prefix}",
                source=self.source,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e

    def _set_nested_value(self, config: Dict[str, Any], keys: List[str], value: str) -> None:
        """Set a nested value in the configuration dictionary.

        Args:
            config: Configuration dictionary (modified in place)
            keys: List of nested keys (e.g., ["database", "host"])
            value: Value to set (as string, will be converted to appropriate type)
        """
        # Navigate to the parent dictionary
        for key in keys[:-1]:
            config = config.setdefault(key.lower(), {})

        # Convert value to appropriate type
        from config_stash.utils.type_coercion import parse_scalar_value

        final_value: Any = parse_scalar_value(value)

        config[keys[-1].lower()] = final_value
