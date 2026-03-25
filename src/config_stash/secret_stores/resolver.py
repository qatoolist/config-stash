"""Secret resolver for integrating secret stores with Config-Stash."""

import re
from typing import Any, Dict, Optional, Union

from config_stash.secret_stores.base import (
    SecretAccessError,
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)


class SecretResolver:
    """Resolves secret placeholders in configuration values.

    This class integrates secret stores with Config-Stash by automatically
    resolving secret placeholders in configuration values. Placeholders follow
    the format: ${secret:key} or ${secret:key:json_path}

    Attributes:
        secret_store: The secret store instance to use for resolving secrets.
        pattern: Regex pattern for matching secret placeholders.
        cache_enabled: Whether to cache resolved secrets.
        fail_on_missing: Whether to raise an error if a secret is not found.

    Example:
        >>> from config_stash import Config
        >>> from config_stash.secret_stores import DictSecretStore, SecretResolver
        >>>
        >>> # Create a secret store
        >>> secrets = DictSecretStore({
        ...     "db/password": "super-secret",
        ...     "api/credentials": {"key": "abc123", "secret": "xyz789"}
        ... })
        >>>
        >>> # Create resolver
        >>> resolver = SecretResolver(secrets)
        >>>
        >>> # Use with Config
        >>> config = Config(env='prod', secret_resolver=resolver)
        >>>
        >>> # In config file: database.password = "${"secret" + ":" + "db/password"}"
        >>> # Automatically resolves to: "super-secret"
    """

    # Pattern matches: ${secret:key} or ${secret:key:json_path} or ${secret:key:version}
    SECRET_PATTERN = re.compile(r"\$\{secret:([^}:]+)(?::([^}:]+))?(?::([^}]+))?\}")

    def __init__(
        self,
        secret_store: SecretStore,
        cache_enabled: bool = True,
        fail_on_missing: bool = True,
        prefix: Optional[str] = None,
        cache_ttl: Optional[float] = None,
    ) -> None:
        """Initialize the secret resolver.

        Args:
            secret_store: The secret store instance to use for resolving secrets.
            cache_enabled: Enable caching of resolved secrets (default: True).
                Caching improves performance but secrets won't be refreshed until
                config reload or TTL expiry.
            fail_on_missing: Raise an error if a secret is not found (default: True).
                If False, leaves the placeholder unchanged.
            prefix: Optional prefix to prepend to all secret keys. Useful for
                namespacing secrets per environment.
            cache_ttl: Optional cache time-to-live in seconds. If set, cached
                secrets expire after this duration and are re-fetched on next access.
                If None (default), cache entries never expire.

        Example:
            >>> resolver = SecretResolver(
            ...     secret_store=my_store,
            ...     cache_enabled=True,
            ...     fail_on_missing=True,
            ...     prefix="prod/",
            ...     cache_ttl=300,  # 5 minutes
            ... )
        """
        self.secret_store = secret_store
        self.cache_enabled = cache_enabled
        self.fail_on_missing = fail_on_missing
        self.prefix = prefix
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}

    def resolve(self, value: Any) -> Any:
        """Resolve secret placeholders in a value.

        This method is designed to be used as a Config hook. It processes
        string values and replaces secret placeholders with actual secret values.

        Args:
            value: The configuration value to process. Only strings containing
                secret placeholders are modified.

        Returns:
            The value with all secret placeholders resolved.

        Raises:
            SecretNotFoundError: If fail_on_missing=True and a secret is not found.
            SecretAccessError: If there's a permission or authentication error.
            SecretStoreError: For other secret store errors.

        Example:
            >>> resolver = SecretResolver(my_store)
            >>> result = resolver.resolve("${secret:api/key}")
            >>> # Returns the actual secret value
        """
        if not isinstance(value, str):
            return value

        # Check if value contains secret placeholder
        if "${secret:" not in value:
            return value

        def replace_secret(match: re.Match) -> str:
            """Replace a single secret placeholder."""
            key = match.group(1)
            json_path_or_version = match.group(2)
            version = match.group(3)

            # Add prefix if configured
            if self.prefix:
                key = f"{self.prefix}{key}"

            # Check cache first
            import time

            cache_key = f"{key}:{json_path_or_version}:{version}"
            if self.cache_enabled and cache_key in self._cache:
                # Check TTL if configured
                if self.cache_ttl is not None:
                    cached_at = self._cache_timestamps.get(cache_key, 0)
                    if (time.time() - cached_at) > self.cache_ttl:
                        # Cache entry expired — remove and re-fetch
                        del self._cache[cache_key]
                        del self._cache_timestamps[cache_key]
                    else:
                        return str(self._cache[cache_key])
                else:
                    return str(self._cache[cache_key])

            try:
                # Fetch secret from store
                secret_value = self.secret_store.get_secret(key, version=version)

                # Extract nested value using json path if provided
                if json_path_or_version and isinstance(secret_value, dict):
                    secret_value = self._extract_json_path(
                        secret_value, json_path_or_version
                    )

                # Cache the result
                if self.cache_enabled:
                    self._cache[cache_key] = secret_value
                    self._cache_timestamps[cache_key] = time.time()

                return str(secret_value)

            except SecretNotFoundError:
                if self.fail_on_missing:
                    raise SecretNotFoundError(
                        f"Secret not found: {key}. " f"Placeholder: {match.group(0)}"
                    )
                # Return original placeholder if fail_on_missing is False
                return match.group(0)

            except (SecretAccessError, SecretStoreError) as e:
                # Always propagate access and store errors
                raise

        # Replace all secret placeholders in the value
        try:
            result = self.SECRET_PATTERN.sub(replace_secret, value)
            return result
        except (SecretNotFoundError, SecretAccessError, SecretStoreError):
            raise
        except Exception as e:
            raise SecretStoreError(f"Error resolving secrets in value: {e}")

    def _extract_json_path(self, data: dict, path: str) -> Any:
        """Extract a value from nested dict using dot notation.

        Args:
            data: The dictionary to extract from.
            path: Dot-separated path (e.g., "database.password").

        Returns:
            The extracted value.

        Raises:
            SecretValidationError: If the path doesn't exist in the data.

        Example:
            >>> data = {"db": {"host": "localhost", "port": 5432}}
            >>> result = resolver._extract_json_path(data, "db.host")
            >>> # Returns "localhost"
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                from config_stash.secret_stores.base import SecretValidationError

                raise SecretValidationError(
                    f"JSON path '{path}' not found in secret data. "
                    f"Failed at key: '{key}'"
                )

        return current

    def clear_cache(self) -> None:
        """Clear the secret cache.

        Useful when you want to force re-fetching of secrets, for example
        after rotating credentials.

        Example:
            >>> resolver = SecretResolver(my_store)
            >>> # ... some time passes, secrets are rotated ...
            >>> resolver.clear_cache()
            >>> config.reload()  # Secrets will be re-fetched
        """
        self._cache.clear()

    def hook(self, value: Any) -> Any:
        """Hook method for integration with Config's HookProcessor.

        This is a convenience method that simply calls resolve().

        Args:
            value: The configuration value to process.

        Returns:
            The value with secret placeholders resolved.

        Example:
            >>> from config_stash import Config
            >>> resolver = SecretResolver(my_store)
            >>> config = Config(env='prod')
            >>> config.hook_processor.register_global_hook(resolver.hook)
        """
        return self.resolve(value)

    def prefetch_secrets(self, keys: list) -> None:
        """Prefetch and cache multiple secrets at once.

        This can improve performance when you know which secrets will be needed.

        Args:
            keys: List of secret keys to prefetch.

        Example:
            >>> resolver = SecretResolver(my_store, cache_enabled=True)
            >>> resolver.prefetch_secrets([
            ...     "database/password",
            ...     "api/key",
            ...     "redis/url"
            ... ])
        """
        for key in keys:
            if self.prefix:
                full_key = f"{self.prefix}{key}"
            else:
                full_key = key

            try:
                value = self.secret_store.get_secret(full_key)
                cache_key = f"{full_key}:None:None"
                self._cache[cache_key] = value
            except SecretStoreError:
                # Skip secrets that can't be fetched
                pass

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache information including size and keys.

        Example:
            >>> resolver = SecretResolver(my_store)
            >>> stats = resolver.cache_stats
            >>> print(f"Cached secrets: {stats['size']}")
        """
        return {
            "enabled": self.cache_enabled,
            "size": len(self._cache),
            "keys": list(self._cache.keys()) if self._cache else [],
        }
