"""AppRole authentication for Vault."""

from typing import Any, Optional

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthMethod,
    VaultAuthenticationError,
)


class AppRoleAuth(VaultAuthMethod):
    """AppRole authentication for Vault.

    AppRole is designed for automated workflows (CI/CD, containers)
    where you have a role_id and secret_id.

    Example:
        >>> from config_stash.secret_stores.vault_auth import AppRoleAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> auth = AppRoleAuth(
        ...     role_id='your-role-id',
        ...     secret_id='your-secret-id'
        ... )
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
    """

    def __init__(
        self,
        role_id: str,
        secret_id: str,
        mount_point: str = "approle",
    ):
        """Initialize AppRole authentication.

        Args:
            role_id: AppRole role ID
            secret_id: AppRole secret ID
            mount_point: Auth mount point (default: 'approle')

        Example:
            >>> auth = AppRoleAuth(
            ...     role_id='abc-123',
            ...     secret_id='xyz-789'
            ... )
        """
        self.role_id = role_id
        self.secret_id = secret_id
        self.mount_point_value = mount_point

    def authenticate(self, client: Any) -> str:
        """Authenticate using AppRole.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If authentication fails
        """
        try:
            response = client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id,
                mount_point=self.mount_point_value,
            )
            return response["auth"]["client_token"]
        except Exception as e:
            raise VaultAuthenticationError(
                f"AppRole authentication failed: {e}"
            )

    def get_mount_point(self) -> str:
        """Get the AppRole mount point."""
        return self.mount_point_value
