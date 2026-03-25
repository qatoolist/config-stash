"""Dictionary-based secret store for testing and development."""

from typing import Any, Dict, List, Optional

from config_stash.secret_stores.base import (
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)


class DictSecretStore(SecretStore):
    """In-memory dictionary-based secret store.

    This is a simple secret store implementation that stores secrets in a Python
    dictionary. It's ideal for:
    - Testing and development
    - Unit tests
    - Local development without external dependencies
    - Simple applications that don't need external secret management

    Warning:
        This store keeps secrets in memory and provides no encryption or
        persistence. Do NOT use in production for sensitive secrets.

    Example:
        >>> from config_stash.secret_stores import DictSecretStore, SecretResolver
        >>> from config_stash import Config
        >>>
        >>> # Create store with secrets
        >>> secrets = DictSecretStore({
        ...     "database/password": "dev-password",
        ...     "api/key": "test-api-key-123",
        ...     "redis/config": {
        ...         "host": "localhost",
        ...         "port": 6379,
        ...         "password": "redis-pass"
        ...     }
        ... })
        >>>
        >>> # Use with Config
        >>> config = Config(
        ...     env='development',
        ...     secret_resolver=SecretResolver(secrets)
        ... )
    """

    def __init__(self, secrets: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the dictionary secret store.

        Args:
            secrets: Optional dictionary of secrets to initialize with.
                Keys are secret names, values are secret values.

        Example:
            >>> store = DictSecretStore({
            ...     "api/key": "abc123",
            ...     "db/password": "secret"
            ... })
        """
        self._secrets: Dict[str, Any] = secrets or {}
        self._versions: Dict[str, List[Any]] = {}  # key -> list of versions

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret from the dictionary.

        Args:
            key: The secret key/name.
            version: Optional version number (0-indexed). If not provided,
                returns the latest version.
            **kwargs: Ignored for DictSecretStore.

        Returns:
            The secret value.

        Raises:
            SecretNotFoundError: If the secret key doesn't exist or
                version is out of range.

        Example:
            >>> store = DictSecretStore({"api/key": "abc123"})
            >>> key = store.get_secret("api/key")
            >>> print(key)  # "abc123"
        """
        if key not in self._secrets:
            raise SecretNotFoundError(
                f"Secret '{key}' not found in DictSecretStore. "
                f"Available secrets: {list(self._secrets.keys())}"
            )

        # Handle versioned access
        if version is not None:
            if key not in self._versions:
                raise SecretNotFoundError(f"No versions found for secret '{key}'")
            try:
                version_idx = int(version)
                return self._versions[key][version_idx]
            except (ValueError, IndexError) as e:
                raise SecretNotFoundError(
                    f"Version '{version}' not found for secret '{key}'. "
                    f"Available versions: 0-{len(self._versions.get(key, [])) - 1}"
                )

        return self._secrets[key]

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret in the dictionary.

        Args:
            key: The secret key/name.
            value: The secret value to store.
            **kwargs: Optional parameters:
                - keep_versions: If True, keeps previous versions (default: False)

        Example:
            >>> store = DictSecretStore()
            >>> store.set_secret("api/key", "new-key-123")
            >>> store.set_secret("api/key", "newer-key-456", keep_versions=True)
        """
        keep_versions = kwargs.get("keep_versions", False)

        # Store version history if requested
        if keep_versions:
            if key in self._secrets:
                if key not in self._versions:
                    self._versions[key] = [self._secrets[key]]
                else:
                    self._versions[key].append(self._secrets[key])

        self._secrets[key] = value

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from the dictionary.

        Args:
            key: The secret key/name to delete.
            **kwargs: Optional parameters:
                - delete_versions: If True, also deletes version history (default: True)

        Raises:
            SecretNotFoundError: If the secret key doesn't exist.

        Example:
            >>> store = DictSecretStore({"api/key": "abc123"})
            >>> store.delete_secret("api/key")
        """
        if key not in self._secrets:
            raise SecretNotFoundError(
                f"Cannot delete secret '{key}': not found in DictSecretStore"
            )

        del self._secrets[key]

        delete_versions = kwargs.get("delete_versions", True)
        if delete_versions and key in self._versions:
            del self._versions[key]

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List all secrets or secrets matching a prefix.

        Args:
            prefix: Optional prefix to filter secrets.
            **kwargs: Ignored for DictSecretStore.

        Returns:
            List of secret keys.

        Example:
            >>> store = DictSecretStore({
            ...     "database/password": "pass1",
            ...     "database/user": "admin",
            ...     "api/key": "key1"
            ... })
            >>> all_secrets = store.list_secrets()
            >>> db_secrets = store.list_secrets(prefix="database/")
        """
        if prefix is None:
            return list(self._secrets.keys())

        return [key for key in self._secrets.keys() if key.startswith(prefix)]

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata about a secret.

        Args:
            key: The secret key/name.

        Returns:
            Dictionary with metadata including version count.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.

        Example:
            >>> store = DictSecretStore({"api/key": "abc123"})
            >>> metadata = store.get_secret_metadata("api/key")
            >>> print(metadata["version_count"])
        """
        if key not in self._secrets:
            raise SecretNotFoundError(f"Secret '{key}' not found")

        return {
            "key": key,
            "type": type(self._secrets[key]).__name__,
            "version_count": len(self._versions.get(key, [])),
            "has_versions": key in self._versions,
        }

    def clear(self) -> None:
        """Clear all secrets from the store.

        This is useful for testing scenarios where you want to reset state.

        Example:
            >>> store = DictSecretStore({"key1": "value1"})
            >>> store.clear()
            >>> store.list_secrets()  # Returns []
        """
        self._secrets.clear()
        self._versions.clear()

    def update(self, secrets: Dict[str, Any]) -> None:
        """Bulk update secrets from a dictionary.

        Args:
            secrets: Dictionary of secrets to add/update.

        Example:
            >>> store = DictSecretStore()
            >>> store.update({
            ...     "api/key": "abc123",
            ...     "db/password": "secret"
            ... })
        """
        self._secrets.update(secrets)

    def __len__(self) -> int:
        """Return the number of secrets in the store."""
        return len(self._secrets)

    def __contains__(self, key: str) -> bool:
        """Check if a secret exists in the store."""
        return key in self._secrets

    def __repr__(self) -> str:
        """String representation of the store."""
        return f"DictSecretStore(secrets={len(self._secrets)})"
