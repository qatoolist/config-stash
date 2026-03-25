"""Base abstract class for secret store providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class SecretStore(ABC):
    """Abstract base class for secret store providers.

    This class defines the interface that all secret store implementations must follow.
    Users can create custom secret store providers by subclassing this class and
    implementing the required methods.

    Example:
        >>> class CustomSecretStore(SecretStore):
        ...     def __init__(self, api_key: str):
        ...         self.api_key = api_key
        ...
        ...     def get_secret(self, key: str, version: Optional[str] = None) -> Any:
        ...         # Your implementation here
        ...         return my_custom_api.fetch_secret(key, version)
        ...
        ...     def set_secret(self, key: str, value: Any, **kwargs) -> None:
        ...         # Your implementation here
        ...         my_custom_api.store_secret(key, value)
        ...
        ...     def delete_secret(self, key: str) -> None:
        ...         # Your implementation here
        ...         my_custom_api.remove_secret(key)
        ...
        ...     def list_secrets(self, prefix: Optional[str] = None) -> list:
        ...         # Your implementation here
        ...         return my_custom_api.list_all_secrets(prefix)
    """

    @abstractmethod
    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret value from the secret store.

        Args:
            key: The unique identifier for the secret. Format may vary by provider.
                Examples:
                - AWS: "my-secret-name" or "my-secret-name:key"
                - Azure: "my-secret-name"
                - Vault: "secret/data/myapp/db-password"
            version: Optional version identifier for the secret. If not provided,
                retrieves the latest version.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The secret value. Can be a string, dict, or other type depending on
            the secret store and how the secret was stored.

        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretAccessError: If there's a permission or authentication error.
            SecretStoreError: For other errors communicating with the secret store.

        Example:
            >>> store = CustomSecretStore()
            >>> password = store.get_secret("database/password")
            >>> api_key = store.get_secret("api/key", version="v2")
        """
        pass

    @abstractmethod
    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret value in the secret store.

        Args:
            key: The unique identifier for the secret.
            value: The secret value to store. Can be a string, dict, or other
                serializable type.
            **kwargs: Additional provider-specific parameters such as:
                - description: Human-readable description
                - tags: Metadata tags
                - kms_key: Encryption key identifier

        Raises:
            SecretAccessError: If there's a permission or authentication error.
            SecretStoreError: For other errors communicating with the secret store.

        Example:
            >>> store = CustomSecretStore()
            >>> store.set_secret("database/password", "super-secret-pass")
            >>> store.set_secret("api/config", {"key": "abc123", "endpoint": "https://api.example.com"})
        """
        pass

    @abstractmethod
    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from the secret store.

        Args:
            key: The unique identifier for the secret to delete.
            **kwargs: Additional provider-specific parameters such as:
                - force: Force deletion without recovery period
                - recovery_window: Days before permanent deletion

        Raises:
            SecretNotFoundError: If the secret does not exist.
            SecretAccessError: If there's a permission or authentication error.
            SecretStoreError: For other errors communicating with the secret store.

        Example:
            >>> store = CustomSecretStore()
            >>> store.delete_secret("old/api-key")
        """
        pass

    @abstractmethod
    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> list:
        """List all secrets or secrets matching a prefix.

        Args:
            prefix: Optional prefix to filter secrets. If None, lists all secrets.
            **kwargs: Additional provider-specific parameters.

        Returns:
            List of secret keys/names available in the store.

        Raises:
            SecretAccessError: If there's a permission or authentication error.
            SecretStoreError: For other errors communicating with the secret store.

        Example:
            >>> store = CustomSecretStore()
            >>> all_secrets = store.list_secrets()
            >>> db_secrets = store.list_secrets(prefix="database/")
        """
        pass

    def secret_exists(self, key: str) -> bool:
        """Check if a secret exists in the store.

        Args:
            key: The unique identifier for the secret.

        Returns:
            True if the secret exists, False otherwise.

        Example:
            >>> store = CustomSecretStore()
            >>> if store.secret_exists("api/key"):
            ...     print("Secret exists")
        """
        try:
            self.get_secret(key)
            return True
        except SecretNotFoundError:
            return False
        except Exception:
            # For other errors, we can't determine existence
            return False

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata about a secret without retrieving the value.

        This is an optional method that providers can override to provide
        metadata such as creation date, version info, tags, etc.

        Args:
            key: The unique identifier for the secret.

        Returns:
            Dictionary containing metadata about the secret.

        Raises:
            NotImplementedError: If the provider doesn't support metadata retrieval.

        Example:
            >>> store = CustomSecretStore()
            >>> metadata = store.get_secret_metadata("database/password")
            >>> print(f"Created: {metadata['created_date']}")
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support metadata retrieval")


class SecretStoreError(Exception):
    """Base exception for secret store errors."""

    pass


class SecretNotFoundError(SecretStoreError):
    """Raised when a requested secret does not exist."""

    pass


class SecretAccessError(SecretStoreError):
    """Raised when there's a permission or authentication error."""

    pass


class SecretValidationError(SecretStoreError):
    """Raised when secret validation fails."""

    pass
