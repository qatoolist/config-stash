"""Azure authentication for Vault."""

from typing import Any

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthenticationError,
    VaultAuthMethod,
)


class AzureAuth(VaultAuthMethod):
    """Azure authentication for Vault.

    Use this when running on Azure (VM, AKS, Container Instances) to
    authenticate using Azure Managed Identity.

    Example:
        >>> from config_stash.secret_stores.vault_auth import AzureAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> auth = AzureAuth(role='myapp-role')
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
    """

    def __init__(
        self,
        role: str,
        mount_point: str = "azure",
    ):
        """Initialize Azure authentication.

        Args:
            role: Vault Azure role name
            mount_point: Auth mount point (default: 'azure')

        Example:
            >>> auth = AzureAuth(role='myapp')
        """
        self.role = role
        self.mount_point_value = mount_point

    def authenticate(self, client: Any) -> str:
        """Authenticate using Azure Managed Identity.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If Azure auth fails
        """
        try:
            response = client.auth.azure.login(
                role=self.role,
                mount_point=self.mount_point_value,
            )

            return response["auth"]["client_token"]

        except Exception as e:
            raise VaultAuthenticationError(f"Azure authentication failed: {e}")

    def get_mount_point(self) -> str:
        """Get the Azure auth mount point."""
        return self.mount_point_value
