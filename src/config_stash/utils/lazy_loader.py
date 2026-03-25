from typing import Any, Dict


class LazyLoader:
    """Lazy loader for configuration values with instance-level caching.

    Wraps a flat or nested configuration dictionary and resolves
    dot-separated key paths on first access, caching the result so
    subsequent lookups are O(1).  Call ``clear_cache()`` after a
    configuration reload to invalidate stale entries.

    Attributes:
        config: The underlying configuration dictionary.

    Example:
        >>> loader = LazyLoader({"database": {"host": "localhost", "port": 5432}})
        >>> loader.get("database.host")
        'localhost'
        >>> loader.get("database.port")
        5432
        >>> loader.clear_cache()  # after a config reload
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the lazy loader with a configuration dictionary.

        Args:
            config: Configuration dictionary to load values from
        """
        self.config = config
        self._cache: Dict[str, Any] = {}  # Instance-level cache

    def get(self, key: str) -> Any:
        """Get a configuration value by dot-separated key path.

        Args:
            key: Dot-separated key path (e.g., 'database.host')

        Returns:
            Configuration value at the specified path

        Raises:
            KeyError: If the configuration key is not found
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Navigate through the config dictionary
        keys = key.split(".")
        value = self.config

        try:
            for k in keys:
                value = value[k]
        except (KeyError, TypeError) as e:
            raise KeyError(f"Configuration key '{key}' not found") from e

        # Cache the value
        self._cache[key] = value
        return value

    def clear_cache(self) -> None:
        """Clear the cache when configuration is reloaded."""
        self._cache.clear()
