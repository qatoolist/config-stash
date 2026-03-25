"""HashiCorp Vault secret store provider."""
# pyright: reportPossiblyUnboundVariable=false

from typing import Any, Dict, List, Optional

from config_stash.secret_stores.base import (
    SecretAccessError,
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)

try:
    import hvac
    from hvac.exceptions import Forbidden, InvalidPath, VaultError

    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False


class HashiCorpVault(SecretStore):
    """HashiCorp Vault secret store provider.

    This provider integrates with HashiCorp Vault to retrieve secrets from:
    - KV v1 and KV v2 secrets engines
    - Dynamic secrets
    - Custom secrets engines

    Prerequisites:
        pip install hvac

    Example:
        >>> from config_stash import Config
        >>> from config_stash.secret_stores import HashiCorpVault, SecretResolver
        >>>
        >>> # Initialize with token authentication
        >>> store = HashiCorpVault(
        ...     url='http://localhost:8200',
        ...     token='your-vault-token'
        ... )
        >>>
        >>> # Or with AppRole authentication
        >>> store = HashiCorpVault(
        ...     url='http://localhost:8200',
        ...     role_id='your-role-id',
        ...     secret_id='your-secret-id'
        ... )
        >>>
        >>> # Use with Config
        >>> config = Config(secret_resolver=SecretResolver(store))
        >>>
        >>> # In config file:
        >>> # database.password = "${secret:secret/data/db/password:password}"
        >>> # For KV v2: secret/data/myapp/db
        >>> # For KV v1: secret/myapp/db
    """

    def __init__(
        self,
        url: str = "http://127.0.0.1:8200",
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        auth_method: Optional[Any] = None,
        namespace: Optional[str] = None,
        mount_point: str = "secret",
        kv_version: int = 2,
        verify: bool = True,
    ) -> None:
        """Initialize HashiCorp Vault client.

        Args:
            url: Vault server URL (default: 'http://127.0.0.1:8200').
            token: Vault authentication token (for token auth). Deprecated: use auth_method.
            role_id: Role ID for AppRole authentication. Deprecated: use auth_method.
            secret_id: Secret ID for AppRole authentication. Deprecated: use auth_method.
            auth_method: VaultAuthMethod instance (recommended). Supports:
                - TokenAuth, AppRoleAuth, OIDCAuth, KerberosAuth, LDAPAuth
                - JWTAuth, KubernetesAuth, AWSAuth, AzureAuth, GCPAuth
            namespace: Vault namespace (Vault Enterprise feature).
            mount_point: KV secrets engine mount point (default: 'secret').
            kv_version: KV secrets engine version, 1 or 2 (default: 2).
            verify: Verify SSL certificates (default: True).

        Raises:
            ImportError: If hvac is not installed.
            SecretAccessError: If authentication fails.

        Example:
            >>> # Token auth (legacy)
            >>> store = HashiCorpVault(
            ...     url='https://vault.example.com',
            ...     token='s.1234567890',
            ...     mount_point='myapp',
            ...     kv_version=2
            ... )
            >>>
            >>> # AppRole auth (legacy)
            >>> store = HashiCorpVault(
            ...     url='https://vault.example.com',
            ...     role_id='role-id-here',
            ...     secret_id='secret-id-here'
            ... )
            >>>
            >>> # OIDC with Kerberos (recommended)
            >>> from config_stash.secret_stores.vault_auth import OIDCAuth
            >>> auth = OIDCAuth(role='myapp-role', use_kerberos=True)
            >>> store = HashiCorpVault(
            ...     url='https://vault.example.com',
            ...     auth_method=auth
            ... )
            >>>
            >>> # LDAP with PIN+Token
            >>> from config_stash.secret_stores.vault_auth import LDAPAuth
            >>> def get_pin_token():
            ...     pin = getpass.getpass("PIN: ")
            ...     token = getpass.getpass("Token: ")
            ...     return pin + token
            >>> auth = LDAPAuth(username='user', password_provider=get_pin_token)
            >>> store = HashiCorpVault(
            ...     url='https://vault.example.com',
            ...     auth_method=auth
            ... )
        """
        if not HVAC_AVAILABLE:
            raise ImportError(
                "hvac is required for HashiCorpVault. " "Install it with: pip install hvac"
            )

        self.url = url
        self.mount_point = mount_point
        self.kv_version = kv_version
        self.namespace = namespace

        try:
            self.client = hvac.Client(url=url, verify=verify, namespace=namespace)

            # Use new auth_method system if provided
            if auth_method:
                self.client.token = auth_method.authenticate(self.client)
            # Fall back to legacy authentication
            elif token:
                self.client.token = token
            elif role_id and secret_id:
                auth_response = self.client.auth.approle.login(role_id=role_id, secret_id=secret_id)
                self.client.token = auth_response["auth"]["client_token"]
            else:
                raise ValueError(
                    "Either 'auth_method' or 'token' or both 'role_id' and 'secret_id' must be provided"
                )

            # Verify authentication
            if not self.client.is_authenticated():
                raise SecretAccessError("Failed to authenticate with Vault")

        except (SecretAccessError, ValueError):
            raise
        except Exception as e:
            raise SecretAccessError(f"Failed to initialize Vault client: {e}") from e

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret from Vault.

        Args:
            key: The secret path. For KV v2, use format: "path/to/secret:field"
                to extract a specific field. For example:
                - "myapp/database:password" extracts the 'password' field
                - "myapp/database" returns the entire secret dict
            version: For KV v2, specify version number. If None, gets latest.
            **kwargs: Additional parameters for read operation.

        Returns:
            The secret value or dict of values.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other Vault errors.

        Example:
            >>> store = HashiCorpVault(url='http://localhost:8200', token='...')
            >>>
            >>> # Get entire secret
            >>> secret = store.get_secret("myapp/database")
            >>> # Returns: {"host": "localhost", "password": "secret"}
            >>>
            >>> # Get specific field
            >>> password = store.get_secret("myapp/database:password")
            >>> # Returns: "secret"
            >>>
            >>> # Get specific version (KV v2)
            >>> old_secret = store.get_secret("myapp/database", version="2")
        """
        # Parse key and field from format "path:field"
        if ":" in key:
            path, field = key.rsplit(":", 1)
        else:
            path = key
            field = None

        try:
            if self.kv_version == 2:
                # KV v2 API
                read_params: Dict[str, Any] = {"path": path, "mount_point": self.mount_point}
                if version:
                    read_params["version"] = int(version)
                read_params.update(kwargs)

                response = self.client.secrets.kv.v2.read_secret_version(**read_params)
                data = response.get("data", {}).get("data", {})
            else:
                # KV v1 API
                read_params = {"path": path, "mount_point": self.mount_point}
                read_params.update(kwargs)

                response = self.client.secrets.kv.v1.read_secret(**read_params)
                data = response.get("data", {})

            if not data:
                raise SecretNotFoundError(f"Secret '{path}' exists but has no data")

            # Extract specific field if requested
            if field:
                if field in data:
                    return data[field]
                else:
                    raise SecretNotFoundError(
                        f"Field '{field}' not found in secret '{path}'. "
                        f"Available fields: {list(data.keys())}"
                    )

            return data

        except InvalidPath:
            raise SecretNotFoundError(
                f"Secret '{path}' not found in Vault "
                f"(mount: {self.mount_point}, version: {self.kv_version})"
            )
        except Forbidden as e:
            raise SecretAccessError(f"Access denied to secret '{path}': {e}")
        except VaultError as e:
            raise SecretStoreError(f"Vault error for '{path}': {e}")
        except Exception as e:
            raise SecretStoreError(f"Unexpected error accessing '{path}': {e}")

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret in Vault.

        Args:
            key: The secret path.
            value: The secret value. For KV engines, should be a dict.
                If a string/other type is provided, it will be wrapped as {"value": value}.
            **kwargs: Additional parameters for create/update operation.

        Raises:
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other Vault errors.

        Example:
            >>> store = HashiCorpVault(url='http://localhost:8200', token='...')
            >>>
            >>> # Store dict secret
            >>> store.set_secret("myapp/database", {
            ...     "host": "localhost",
            ...     "port": 5432,
            ...     "password": "secret"
            ... })
            >>>
            >>> # Store simple value
            >>> store.set_secret("myapp/api-key", "abc123")
            >>> # Stored as: {"value": "abc123"}
        """
        # Ensure value is a dict for KV engines
        if not isinstance(value, dict):
            secret_data = {"value": value}
        else:
            secret_data = value

        try:
            if self.kv_version == 2:
                # KV v2 API
                self.client.secrets.kv.v2.create_or_update_secret(
                    path=key, secret=secret_data, mount_point=self.mount_point, **kwargs
                )
            else:
                # KV v1 API
                self.client.secrets.kv.v1.create_or_update_secret(
                    path=key, secret=secret_data, mount_point=self.mount_point, **kwargs
                )

        except Forbidden as e:
            raise SecretAccessError(f"Access denied writing secret '{key}': {e}")
        except VaultError as e:
            raise SecretStoreError(f"Vault error writing '{key}': {e}")
        except Exception as e:
            raise SecretStoreError(f"Unexpected error writing '{key}': {e}")

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from Vault.

        For KV v2, this performs a soft delete (can be recovered).
        Use destroy_secret() for permanent deletion.

        Args:
            key: The secret path to delete.
            **kwargs: Additional parameters:
                - versions: For KV v2, list of versions to delete (default: [latest])

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other Vault errors.

        Example:
            >>> store = HashiCorpVault(url='http://localhost:8200', token='...')
            >>>
            >>> # Delete latest version
            >>> store.delete_secret("myapp/old-key")
            >>>
            >>> # Delete specific versions (KV v2)
            >>> store.delete_secret("myapp/secret", versions=[1, 2, 3])
        """
        try:
            if self.kv_version == 2:
                # KV v2 soft delete
                versions = kwargs.get("versions")
                if versions is None:
                    # Delete latest version - first read to get current version
                    metadata = self.client.secrets.kv.v2.read_secret_metadata(
                        path=key, mount_point=self.mount_point
                    )
                    current_version = metadata["data"]["current_version"]
                    versions = [current_version]

                self.client.secrets.kv.v2.delete_secret_versions(
                    path=key, versions=versions, mount_point=self.mount_point
                )
            else:
                # KV v1 delete
                self.client.secrets.kv.v1.delete_secret(path=key, mount_point=self.mount_point)

        except InvalidPath:
            raise SecretNotFoundError(f"Secret '{key}' not found")
        except Forbidden as e:
            raise SecretAccessError(f"Access denied deleting secret '{key}': {e}")
        except VaultError as e:
            raise SecretStoreError(f"Vault error deleting '{key}': {e}")

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List secrets in Vault.

        Args:
            prefix: Optional path prefix to list from.
            **kwargs: Additional parameters for list operation.

        Returns:
            List of secret paths.

        Raises:
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other Vault errors.

        Example:
            >>> store = HashiCorpVault(url='http://localhost:8200', token='...')
            >>>
            >>> # List all secrets at root
            >>> all_secrets = store.list_secrets()
            >>>
            >>> # List secrets under a path
            >>> app_secrets = store.list_secrets(prefix="myapp/")
        """
        path = prefix if prefix else ""

        try:
            if self.kv_version == 2:
                response = self.client.secrets.kv.v2.list_secrets(
                    path=path, mount_point=self.mount_point
                )
            else:
                response = self.client.secrets.kv.v1.list_secrets(
                    path=path, mount_point=self.mount_point
                )

            keys = response.get("data", {}).get("keys", [])
            return keys

        except InvalidPath:
            # Path doesn't exist or is empty
            return []
        except Forbidden as e:
            raise SecretAccessError(f"Access denied listing secrets at '{path}': {e}")
        except VaultError as e:
            raise SecretStoreError(f"Vault error listing secrets at '{path}': {e}")

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata about a secret.

        Only available for KV v2.

        Args:
            key: The secret path.

        Returns:
            Dictionary with secret metadata.

        Raises:
            NotImplementedError: For KV v1.
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.

        Example:
            >>> store = HashiCorpVault(url='http://localhost:8200', token='...', kv_version=2)
            >>> metadata = store.get_secret_metadata("myapp/database")
            >>> print(f"Current version: {metadata['current_version']}")
            >>> print(f"Created: {metadata['created_time']}")
        """
        if self.kv_version != 2:
            raise NotImplementedError("Metadata is only available for KV v2 secrets engine")

        try:
            response = self.client.secrets.kv.v2.read_secret_metadata(
                path=key, mount_point=self.mount_point
            )

            return response.get("data", {})

        except InvalidPath:
            raise SecretNotFoundError(f"Secret '{key}' not found")
        except Forbidden as e:
            raise SecretAccessError(f"Access denied to secret metadata '{key}': {e}")
        except VaultError as e:
            raise SecretStoreError(f"Vault error reading metadata for '{key}': {e}")

    def __repr__(self) -> str:
        """String representation of the store."""
        return (
            f"HashiCorpVault(url='{self.url}', "
            f"mount='{self.mount_point}', "
            f"kv_version={self.kv_version})"
        )
