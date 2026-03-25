"""Multi-store implementation for chaining multiple secret stores."""

from typing import Any, Dict, List, Optional

from config_stash.secret_stores.base import (
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)


class MultiSecretStore(SecretStore):
    """Composite secret store that chains multiple secret stores.

    This allows you to configure a fallback hierarchy of secret stores. When
    resolving a secret, it tries each store in order until the secret is found.

    This is useful for scenarios like:
    - Primary secrets in AWS Secrets Manager, fallback to environment variables
    - Development secrets in local dict, production secrets in Vault
    - Secrets split across multiple cloud providers
    - Testing with mocked stores that override production stores

    Example:
        >>> from config_stash.secret_stores import (
        ...     MultiSecretStore,
        ...     DictSecretStore,
        ...     AWSSecretsManager,
        ...     SecretResolver
        ... )
        >>>
        >>> # Create a multi-store with fallback hierarchy
        >>> store = MultiSecretStore([
        ...     DictSecretStore({"local/override": "dev-value"}),  # Checked first
        ...     AWSSecretsManager(region_name='us-east-1'),  # Fallback to AWS
        ... ])
        >>>
        >>> # Use with Config
        >>> config = Config(secret_resolver=SecretResolver(store))
    """

    def __init__(
        self,
        stores: List[SecretStore],
        fail_on_missing: bool = True,
        write_to_first: bool = True,
    ) -> None:
        """Initialize the multi-store.

        Args:
            stores: List of secret stores in priority order. The first store
                is checked first, then the second, etc.
            fail_on_missing: If True, raises SecretNotFoundError if secret not
                found in any store. If False, returns None (default: True).
            write_to_first: When setting secrets, write to the first store only
                (default: True). If False, writes to all stores.

        Example:
            >>> primary = AWSSecretsManager(region='us-east-1')
            >>> fallback = DictSecretStore({"default/key": "value"})
            >>> store = MultiSecretStore([primary, fallback])
        """
        if not stores:
            raise ValueError("MultiSecretStore requires at least one store")

        self.stores = stores
        self.fail_on_missing = fail_on_missing
        self.write_to_first = write_to_first

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret by trying each store in order.

        Args:
            key: The secret key/name.
            version: Optional version identifier.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The secret value from the first store that has it.

        Raises:
            SecretNotFoundError: If fail_on_missing=True and secret not found
                in any store.

        Example:
            >>> store = MultiSecretStore([store1, store2, store3])
            >>> secret = store.get_secret("api/key")
            >>> # Tries store1, then store2, then store3
        """
        errors = []

        for i, store in enumerate(self.stores):
            try:
                return store.get_secret(key, version=version, **kwargs)
            except SecretNotFoundError as e:
                errors.append(f"Store {i} ({store.__class__.__name__}): {e}")
                continue
            except Exception as e:
                # For non-NotFound errors, log but continue to next store
                errors.append(f"Store {i} ({store.__class__.__name__}) error: {e}")
                continue

        # Secret not found in any store
        if self.fail_on_missing:
            error_msg = f"Secret '{key}' not found in any of {len(self.stores)} stores."
            if errors:
                error_msg += f"\nErrors: {'; '.join(errors)}"
            raise SecretNotFoundError(error_msg)

        return None

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret in one or all stores.

        Args:
            key: The secret key/name.
            value: The secret value.
            **kwargs: Additional provider-specific parameters.

        Example:
            >>> store = MultiSecretStore([store1, store2])
            >>> store.set_secret("new/secret", "value")
            >>> # Writes to store1 only (if write_to_first=True)
        """
        if self.write_to_first:
            self.stores[0].set_secret(key, value, **kwargs)
        else:
            errors = []
            for i, store in enumerate(self.stores):
                try:
                    store.set_secret(key, value, **kwargs)
                except Exception as e:
                    errors.append(f"Store {i} ({store.__class__.__name__}): {e}")

            if errors:
                raise SecretStoreError(
                    f"Failed to set secret in some stores: {'; '.join(errors)}"
                )

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from one or all stores.

        Args:
            key: The secret key/name to delete.
            **kwargs: Additional provider-specific parameters.

        Example:
            >>> store = MultiSecretStore([store1, store2])
            >>> store.delete_secret("old/secret")
        """
        if self.write_to_first:
            self.stores[0].delete_secret(key, **kwargs)
        else:
            errors = []
            for i, store in enumerate(self.stores):
                try:
                    store.delete_secret(key, **kwargs)
                except SecretNotFoundError:
                    # OK if secret doesn't exist in this store
                    continue
                except Exception as e:
                    errors.append(f"Store {i} ({store.__class__.__name__}): {e}")

            if errors:
                raise SecretStoreError(
                    f"Failed to delete secret from some stores: {'; '.join(errors)}"
                )

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List all unique secrets across all stores.

        Args:
            prefix: Optional prefix to filter secrets.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Combined list of unique secret keys from all stores.

        Example:
            >>> store = MultiSecretStore([store1, store2])
            >>> all_secrets = store.list_secrets()
            >>> # Returns unique secrets from both stores
        """
        all_secrets = set()

        for store in self.stores:
            try:
                secrets = store.list_secrets(prefix=prefix, **kwargs)
                all_secrets.update(secrets)
            except Exception:
                # Continue even if one store fails to list
                continue

        return sorted(all_secrets)

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata from the first store that has the secret.

        Args:
            key: The secret key/name.

        Returns:
            Metadata dictionary from the first store that has the secret.

        Raises:
            SecretNotFoundError: If secret not found in any store.

        Example:
            >>> store = MultiSecretStore([store1, store2])
            >>> metadata = store.get_secret_metadata("api/key")
        """
        for store in self.stores:
            try:
                return store.get_secret_metadata(key)
            except (SecretNotFoundError, NotImplementedError):
                continue

        raise SecretNotFoundError(
            f"Secret '{key}' not found in any store or no store supports metadata"
        )

    def secret_exists(self, key: str) -> bool:
        """Check if a secret exists in any store.

        Args:
            key: The secret key/name.

        Returns:
            True if the secret exists in at least one store.

        Example:
            >>> store = MultiSecretStore([store1, store2])
            >>> if store.secret_exists("api/key"):
            ...     print("Secret found")
        """
        for store in self.stores:
            if store.secret_exists(key):
                return True
        return False

    def get_store_for_secret(self, key: str) -> Optional[SecretStore]:
        """Find which store contains a specific secret.

        Args:
            key: The secret key/name.

        Returns:
            The first store that contains the secret, or None if not found.

        Example:
            >>> store = MultiSecretStore([aws_store, vault_store, dict_store])
            >>> source = store.get_store_for_secret("api/key")
            >>> print(f"Secret found in: {source.__class__.__name__}")
        """
        for store in self.stores:
            try:
                store.get_secret(key)
                return store
            except SecretNotFoundError:
                continue
            except Exception:
                continue
        return None

    def __repr__(self) -> str:
        """String representation of the multi-store."""
        store_names = [s.__class__.__name__ for s in self.stores]
        return f"MultiSecretStore(stores={store_names})"
