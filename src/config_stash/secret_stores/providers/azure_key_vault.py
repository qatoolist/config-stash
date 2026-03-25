"""Azure Key Vault secret store provider."""

# pyright: reportPossiblyUnboundVariable=false
# pyright: reportMissingImports=false

from typing import Any, Dict, List, Optional

from config_stash.secret_stores.base import (
    SecretAccessError,
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)

try:
    from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class AzureKeyVault(SecretStore):
    """Azure Key Vault secret store provider.

    This provider integrates with Azure Key Vault to retrieve secrets.

    Prerequisites:
        pip install azure-keyvault-secrets azure-identity

    Authentication:
        Uses DefaultAzureCredential which supports:
        - Environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
        - Managed Identity (when running in Azure)
        - Azure CLI credentials
        - Visual Studio Code credentials

    Example:
        >>> from config_stash import Config
        >>> from config_stash.secret_stores import AzureKeyVault, SecretResolver
        >>>
        >>> # Initialize with vault URL
        >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net')
        >>>
        >>> # Use with Config
        >>> config = Config(secret_resolver=SecretResolver(store))
        >>>
        >>> # In config file: database.password = "${"secret" + ":" + "db-password"}"
        >>> # Note: Azure Key Vault secret names must match regex: ^[0-9a-zA-Z-]+$
    """

    def __init__(self, vault_url: str, credential: Optional[Any] = None) -> None:
        """Initialize Azure Key Vault client.

        Args:
            vault_url: Azure Key Vault URL (e.g., 'https://my-vault.vault.azure.net').
            credential: Optional Azure credential. If None, uses DefaultAzureCredential.

        Raises:
            ImportError: If Azure SDK is not installed.
            SecretAccessError: If authentication fails.

        Example:
            >>> # Use default credentials
            >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net')
            >>>
            >>> # Use specific credential
            >>> from azure.identity import ClientSecretCredential
            >>> cred = ClientSecretCredential(
            ...     tenant_id='...',
            ...     client_id='...',
            ...     client_secret='...'
            ... )
            >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net', credential=cred)
        """
        if not AZURE_AVAILABLE:
            raise ImportError(
                "azure-keyvault-secrets and azure-identity are required for AzureKeyVault. "
                "Install with: pip install azure-keyvault-secrets azure-identity"
            )

        self.vault_url = vault_url

        try:
            if credential is None:
                credential = DefaultAzureCredential()

            self.client = SecretClient(vault_url=vault_url, credential=credential)
        except Exception as e:
            raise SecretAccessError(f"Failed to initialize Azure Key Vault client: {e}")

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret from Azure Key Vault.

        Args:
            key: The secret name. Note: Azure Key Vault names must match ^[0-9a-zA-Z-]+$
            version: Optional secret version ID. If None, gets latest.
            **kwargs: Additional parameters.

        Returns:
            The secret value as a string.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other Azure errors.

        Example:
            >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net')
            >>>
            >>> # Get latest version
            >>> password = store.get_secret("db-password")
            >>>
            >>> # Get specific version
            >>> old_password = store.get_secret("db-password", version="abc123...")
        """
        try:
            if version:
                secret = self.client.get_secret(name=key, version=version)
            else:
                secret = self.client.get_secret(name=key)

            return secret.value

        except ResourceNotFoundError:
            raise SecretNotFoundError(
                f"Secret '{key}' not found in Azure Key Vault '{self.vault_url}'"
            )
        except HttpResponseError as e:
            if e.status_code in (401, 403):
                raise SecretAccessError(f"Access denied to secret '{key}': {e}")
            else:
                raise SecretStoreError(f"Azure Key Vault error for '{key}': {e}")
        except Exception as e:
            raise SecretStoreError(f"Unexpected error accessing '{key}': {e}")

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret in Azure Key Vault.

        Args:
            key: The secret name. Must match regex: ^[0-9a-zA-Z-]+$
            value: The secret value (will be converted to string).
            **kwargs: Additional parameters (tags, content_type, etc.).

        Raises:
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other Azure errors.

        Example:
            >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net')
            >>> store.set_secret("api-key", "abc123", tags={"env": "prod"})
        """
        try:
            self.client.set_secret(name=key, value=str(value), **kwargs)
        except HttpResponseError as e:
            if e.status_code in (401, 403):
                raise SecretAccessError(f"Access denied setting secret '{key}': {e}")
            else:
                raise SecretStoreError(f"Failed to set secret '{key}': {e}")

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from Azure Key Vault.

        This begins a deletion process. The secret is recoverable during the retention period.

        Args:
            key: The secret name to delete.
            **kwargs: Additional parameters.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.

        Example:
            >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net')
            >>> store.delete_secret("old-api-key")
        """
        try:
            self.client.begin_delete_secret(name=key).result()
        except ResourceNotFoundError:
            raise SecretNotFoundError(f"Secret '{key}' not found")
        except HttpResponseError as e:
            if e.status_code in (401, 403):
                raise SecretAccessError(f"Access denied deleting secret '{key}': {e}")
            else:
                raise SecretStoreError(f"Failed to delete secret '{key}': {e}")

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List secrets in Azure Key Vault.

        Args:
            prefix: Optional prefix to filter secrets.
            **kwargs: Additional parameters.

        Returns:
            List of secret names.

        Example:
            >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net')
            >>> all_secrets = store.list_secrets()
            >>> prod_secrets = store.list_secrets(prefix="prod-")
        """
        try:
            secrets = []
            for secret in self.client.list_properties_of_secrets():
                name = secret.name
                if prefix is None or name.startswith(prefix):
                    secrets.append(name)
            return secrets
        except HttpResponseError as e:
            if e.status_code in (401, 403):
                raise SecretAccessError(f"Access denied listing secrets: {e}")
            else:
                raise SecretStoreError(f"Failed to list secrets: {e}")

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata about a secret.

        Args:
            key: The secret name.

        Returns:
            Dictionary with secret metadata.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.

        Example:
            >>> store = AzureKeyVault(vault_url='https://my-vault.vault.azure.net')
            >>> metadata = store.get_secret_metadata("db-password")
            >>> print(f"Created: {metadata['created_on']}")
        """
        try:
            secret = self.client.get_secret(name=key)
            return {
                "name": secret.name,
                "id": secret.id,
                "created_on": secret.properties.created_on,
                "updated_on": secret.properties.updated_on,
                "enabled": secret.properties.enabled,
                "tags": secret.properties.tags,
                "content_type": secret.properties.content_type,
                "version": secret.properties.version,
            }
        except ResourceNotFoundError:
            raise SecretNotFoundError(f"Secret '{key}' not found")

    def __repr__(self) -> str:
        """String representation of the store."""
        return f"AzureKeyVault(vault_url='{self.vault_url}')"
