"""GCP authentication for Vault."""

from typing import Any, Optional

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthenticationError,
    VaultAuthMethod,
)


class GCPAuth(VaultAuthMethod):
    """GCP authentication for Vault.

    Use this when running on GCP (Compute Engine, GKE, Cloud Run) to
    authenticate using GCP service accounts.

    Example:
        >>> from config_stash.secret_stores.vault_auth import GCPAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> # GCE instance
        >>> auth = GCPAuth(role='myapp-role', auth_type='gce')
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
        >>>
        >>> # IAM service account
        >>> auth = GCPAuth(role='myapp-role', auth_type='iam')
    """

    def __init__(
        self,
        role: str,
        auth_type: str = "gce",
        mount_point: str = "gcp",
        jwt: Optional[str] = None,
    ):
        """Initialize GCP authentication.

        Args:
            role: Vault GCP role name
            auth_type: GCP auth type ('gce' or 'iam', default: 'gce')
            mount_point: Auth mount point (default: 'gcp')
            jwt: Optional JWT token for IAM auth

        Example:
            >>> # GCE instance
            >>> auth = GCPAuth(role='myapp', auth_type='gce')
            >>>
            >>> # IAM with JWT
            >>> auth = GCPAuth(role='myapp', auth_type='iam', jwt='eyJhbGc...')
        """
        self.role = role
        self.auth_type = auth_type
        self.mount_point_value = mount_point
        self.jwt = jwt

    def authenticate(self, client: Any) -> str:
        """Authenticate using GCP credentials.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If GCP auth fails
        """
        try:
            if self.auth_type == "gce":
                response = client.auth.gcp.login(
                    role=self.role,
                    mount_point=self.mount_point_value,
                )
            elif self.auth_type == "iam":
                if not self.jwt:
                    raise VaultAuthenticationError("JWT token required for IAM auth type")

                response = client.auth.gcp.login(
                    role=self.role,
                    jwt=self.jwt,
                    mount_point=self.mount_point_value,
                )
            else:
                raise VaultAuthenticationError(
                    f"Unknown GCP auth type: {self.auth_type}. " f"Must be 'gce' or 'iam'"
                )

            return response["auth"]["client_token"]

        except Exception as e:
            raise VaultAuthenticationError(f"GCP authentication failed: {e}")

    def get_mount_point(self) -> str:
        """Get the GCP auth mount point."""
        return self.mount_point_value
