import os

from config_stash.loaders.loader import Loader


class EnvironmentLoader(Loader):
    def __init__(self, prefix, separator="__"):
        """Initialize the environment loader.

        Args:
            prefix: Prefix for environment variables to load
            separator: Separator for nested keys (default: "__")
        """
        super().__init__(source=f"environment:{prefix}")
        self.prefix = prefix.upper()
        self.separator = separator
        self.config = {}

    def load(self):
        try:
            # Match env vars that start with prefix followed by underscore
            # e.g., "APP_" matches "APP_DATABASE", but not "APPLET_"
            prefix_with_underscore = f"{self.prefix}_"
            env_vars = {
                key: value for key, value in os.environ.items()
                if key.startswith(prefix_with_underscore)
            }
            for key, value in env_vars.items():
                # Remove prefix and initial underscore
                key_without_prefix = key[len(self.prefix) :]
                if key_without_prefix.startswith("_"):
                    key_without_prefix = key_without_prefix[1:]

                # Split by separator for nested keys
                nested_keys = key_without_prefix.split(self.separator)
                self._set_nested_value(self.config, nested_keys, value)
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error loading environment variables with prefix {self.prefix}: {e}"
            )
        return self.config

    def _set_nested_value(self, config, keys, value):
        """Set a nested value in the configuration dictionary.

        Args:
            config: Configuration dictionary
            keys: List of nested keys
            value: Value to set
        """
        for key in keys[:-1]:
            config = config.setdefault(key.lower(), {})

        # Convert value to appropriate type
        final_value = value
        if value.lower() == "true":
            final_value = True
        elif value.lower() == "false":
            final_value = False
        elif value.isdigit():
            final_value = int(value)
        else:
            try:
                final_value = float(value)
            except ValueError:
                pass  # Keep as string

        config[keys[-1].lower()] = final_value
