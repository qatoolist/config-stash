"""Environment variable-based secret store."""

import os
from typing import Any, Dict, List, Optional

from config_stash.secret_stores.base import (
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)


class EnvSecretStore(SecretStore):
    """Secret store that reads from environment variables.

    This provider allows you to use environment variables as a secret source,
    which is useful for:
    - CI/CD pipelines
    - Container-based deployments (Docker, Kubernetes)
    - Local development
    - Integration with .env files via EnvFileLoader

    The store can optionally transform secret keys before looking them up
    in the environment (e.g., converting "api/key" to "API_KEY").

    Example:
        >>> import os
        >>> from config_stash.secret_stores import EnvSecretStore, SecretResolver
        >>> from config_stash import Config
        >>>
        >>> # Set environment variables
        >>> os.environ['DB_PASSWORD'] = 'secret123'
        >>> os.environ['API_KEY'] = 'abc123'
        >>>
        >>> # Create store with key transformation
        >>> store = EnvSecretStore(
        ...     prefix="",
        ...     transform_key=True  # "db/password" -> "DB_PASSWORD"
        ... )
        >>>
        >>> # Use with Config
        >>> config = Config(secret_resolver=SecretResolver(store))
        >>>
        >>> # In config: database.password = "${secret:db/password}"
        >>> # Resolves to os.environ['DB_PASSWORD']
    """

    def __init__(
        self,
        prefix: str = "",
        suffix: str = "",
        transform_key: bool = True,
        case_sensitive: bool = False,
    ) -> None:
        """Initialize the environment variable secret store.

        Args:
            prefix: Prefix to prepend to all environment variable names.
                Example: prefix="SECRET_" will look for "SECRET_API_KEY"
            suffix: Suffix to append to all environment variable names.
            transform_key: If True, transforms secret keys for env var lookup:
                - Replaces "/" and "." with "_"
                - Converts to uppercase (if not case_sensitive)
                Example: "api/key" -> "API_KEY"
                If False, uses the key as-is.
            case_sensitive: If True, preserves case when looking up variables.
                Only applicable when transform_key=False (default: False).

        Example:
            >>> # Look for SECRET_* variables
            >>> store = EnvSecretStore(prefix="SECRET_")
            >>>
            >>> # Custom transformation
            >>> store = EnvSecretStore(transform_key=True)
        """
        self.prefix = prefix
        self.suffix = suffix
        self.transform_key = transform_key
        self.case_sensitive = case_sensitive

    def _transform_key(self, key: str) -> str:
        """Transform a secret key to environment variable name.

        Args:
            key: The secret key (e.g., "api/key", "db.password").

        Returns:
            Transformed environment variable name.

        Example:
            >>> store = EnvSecretStore()
            >>> store._transform_key("api/key")
            'API_KEY'
            >>> store._transform_key("database.password")
            'DATABASE_PASSWORD'
        """
        if self.transform_key:
            # Replace path separators with underscores
            transformed = key.replace("/", "_").replace(".", "_").replace("-", "_")
            if not self.case_sensitive:
                transformed = transformed.upper()
        else:
            transformed = key

        # Add prefix and suffix
        return f"{self.prefix}{transformed}{self.suffix}"

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret from environment variables.

        Args:
            key: The secret key, will be transformed based on store settings.
            version: Ignored for EnvSecretStore (env vars don't have versions).
            **kwargs: Ignored for EnvSecretStore.

        Returns:
            The environment variable value as a string.

        Raises:
            SecretNotFoundError: If the environment variable doesn't exist.

        Example:
            >>> os.environ['API_KEY'] = 'secret123'
            >>> store = EnvSecretStore()
            >>> key = store.get_secret("api/key")
            >>> print(key)  # "secret123"
        """
        env_var_name = self._transform_key(key)

        if env_var_name not in os.environ:
            raise SecretNotFoundError(
                f"Environment variable '{env_var_name}' not found "
                f"(secret key: '{key}'). "
                f"Available variables: {list(os.environ.keys())[:10]}..."
            )

        return os.environ[env_var_name]

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret as an environment variable.

        Args:
            key: The secret key, will be transformed based on store settings.
            value: The secret value to store (will be converted to string).
            **kwargs: Ignored for EnvSecretStore.

        Example:
            >>> store = EnvSecretStore()
            >>> store.set_secret("api/key", "new-secret")
            >>> print(os.environ['API_KEY'])  # "new-secret"
        """
        env_var_name = self._transform_key(key)
        os.environ[env_var_name] = str(value)

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from environment variables.

        Args:
            key: The secret key to delete.
            **kwargs: Ignored for EnvSecretStore.

        Raises:
            SecretNotFoundError: If the environment variable doesn't exist.

        Example:
            >>> store = EnvSecretStore()
            >>> store.delete_secret("api/key")
            >>> # Removes API_KEY from os.environ
        """
        env_var_name = self._transform_key(key)

        if env_var_name not in os.environ:
            raise SecretNotFoundError(
                f"Cannot delete environment variable '{env_var_name}': not found"
            )

        del os.environ[env_var_name]

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List all environment variables matching the pattern.

        Args:
            prefix: Optional prefix to filter results (applied AFTER transformation).
            **kwargs: Ignored for EnvSecretStore.

        Returns:
            List of environment variable names.

        Note:
            This returns the actual environment variable names, not the
            reverse-transformed secret keys. To get secret keys, you would
            need to implement reverse transformation.

        Example:
            >>> os.environ['API_KEY'] = 'value1'
            >>> os.environ['DB_PASSWORD'] = 'value2'
            >>> store = EnvSecretStore(prefix="")
            >>> secrets = store.list_secrets()
            >>> # Returns all environment variables
        """
        # Get all env vars that match our prefix/suffix pattern
        env_vars = []

        for key in os.environ.keys():
            # Check if it matches our prefix/suffix
            if self.prefix and not key.startswith(self.prefix):
                continue
            if self.suffix and not key.endswith(self.suffix):
                continue

            # Apply additional prefix filter if provided
            if prefix:
                # Transform the prefix the same way we transform keys
                transformed_prefix = self._transform_key(prefix)
                if not key.startswith(transformed_prefix):
                    continue

            env_vars.append(key)

        return sorted(env_vars)

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata about an environment variable.

        Args:
            key: The secret key.

        Returns:
            Metadata dictionary with the environment variable name and value length.

        Raises:
            SecretNotFoundError: If the environment variable doesn't exist.

        Example:
            >>> os.environ['API_KEY'] = 'secret123'
            >>> store = EnvSecretStore()
            >>> metadata = store.get_secret_metadata("api/key")
            >>> print(metadata)
            {'key': 'api/key', 'env_var_name': 'API_KEY', 'value_length': 9}
        """
        env_var_name = self._transform_key(key)

        if env_var_name not in os.environ:
            raise SecretNotFoundError(
                f"Environment variable '{env_var_name}' not found"
            )

        value = os.environ[env_var_name]

        return {
            "key": key,
            "env_var_name": env_var_name,
            "value_length": len(value),
            "type": "environment_variable",
        }

    def __repr__(self) -> str:
        """String representation of the store."""
        return (
            f"EnvSecretStore(prefix='{self.prefix}', "
            f"suffix='{self.suffix}', "
            f"transform_key={self.transform_key})"
        )
