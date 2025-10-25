"""HashiCorp Vault integration (backward compatibility wrapper).

This module provides backward compatibility for the VaultResolver class.
For new code, please use the secret_stores module directly:

    from config_stash.secret_stores import HashiCorpVault, SecretResolver
"""

from typing import Any, Optional

from config_stash.secret_stores import HashiCorpVault, SecretResolver


class VaultResolver:
    """HashiCorp Vault secret resolver (backward compatibility wrapper).

    This class is provided for backward compatibility. For new code, please use:
        from config_stash.secret_stores import HashiCorpVault, SecretResolver

    Example:
        >>> # Old way (still works):
        >>> from config_stash.vault_resolver import VaultResolver
        >>> resolver = VaultResolver(
        ...     vault_addr='http://localhost:8200',
        ...     vault_token='your-token'
        ... )
        >>>
        >>> # New way (recommended):
        >>> from config_stash.secret_stores import HashiCorpVault, SecretResolver
        >>> store = HashiCorpVault(url='http://localhost:8200', token='your-token')
        >>> resolver = SecretResolver(store)
    """

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_token: Optional[str] = None,
        mount_point: str = "secret",
        kv_version: int = 2,
    ) -> None:
        """Initialize Vault resolver.

        Args:
            vault_addr: URL of Vault server (e.g., http://127.0.0.1:8200)
            vault_token: Authentication token for Vault
            mount_point: KV secrets engine mount point (default: 'secret')
            kv_version: KV secrets engine version, 1 or 2 (default: 2)

        Raises:
            ImportError: If hvac is not installed
            ValueError: If required parameters are missing

        Example:
            >>> resolver = VaultResolver(
            ...     vault_addr='http://localhost:8200',
            ...     vault_token='s.1234567890',
            ...     mount_point='myapp',
            ...     kv_version=2
            ... )
        """
        if vault_addr is None:
            vault_addr = "http://127.0.0.1:8200"

        if vault_token is None:
            raise ValueError(
                "vault_token is required. Please provide a Vault authentication token."
            )

        # Create the underlying HashiCorpVault store
        self._store = HashiCorpVault(
            url=vault_addr,
            token=vault_token,
            mount_point=mount_point,
            kv_version=kv_version,
        )

        # Create the SecretResolver
        self._resolver = SecretResolver(self._store, cache_enabled=True, fail_on_missing=True)

    def resolve(self, key: str, version: Optional[str] = None) -> Any:
        """Resolve a secret from Vault.

        Args:
            key: Path to secret in Vault (e.g., 'secret/data/db/password')
                For KV v2, format: "path/to/secret:field"
                For KV v1, format: "path/to/secret"
            version: Optional version number for KV v2

        Returns:
            Secret value from Vault

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretAccessError: If there's a permission error
            SecretStoreError: For other Vault errors

        Example:
            >>> resolver = VaultResolver(vault_addr='...', vault_token='...')
            >>>
            >>> # Get secret
            >>> password = resolver.resolve('myapp/database:password')
            >>>
            >>> # Get specific version
            >>> old_key = resolver.resolve('myapp/api-key', version='2')
        """
        return self._store.get_secret(key, version=version)

    def resolve_placeholder(self, value: str) -> str:
        """Resolve secret placeholders in a string value.

        This method processes strings containing ${secret:key} placeholders.

        Args:
            value: String that may contain secret placeholders

        Returns:
            String with placeholders resolved

        Example:
            >>> resolver = VaultResolver(vault_addr='...', vault_token='...')
            >>> result = resolver.resolve_placeholder("${secret:myapp/db:password}")
        """
        return self._resolver.resolve(value)
