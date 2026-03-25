"""JWT authentication for Vault."""

from typing import Any, Optional

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthenticationError,
    VaultAuthMethod,
)


class JWTAuth(VaultAuthMethod):
    """JWT authentication for Vault.

    Use this when you have a JWT token from an external source
    (CI/CD system, service mesh, etc.) that Vault can validate.

    Example:
        >>> from config_stash.secret_stores.vault_auth import JWTAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> # JWT from environment or file
        >>> import os
        >>> jwt_token = os.getenv('JWT_TOKEN')
        >>>
        >>> auth = JWTAuth(
        ...     role='myapp-role',
        ...     jwt=jwt_token
        ... )
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
    """

    def __init__(
        self,
        role: str,
        jwt: str,
        mount_point: str = "jwt",
    ):
        """Initialize JWT authentication.

        Args:
            role: Vault role name
            jwt: JWT token string
            mount_point: Auth mount point (default: 'jwt')

        Example:
            >>> auth = JWTAuth(
            ...     role='myapp',
            ...     jwt='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
            ... )
        """
        self.role = role
        self.jwt = jwt
        self.mount_point_value = mount_point

    def authenticate(self, client: Any) -> str:
        """Authenticate using JWT.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If JWT auth fails
        """
        try:
            response = client.auth.jwt.jwt_login(
                role=self.role,
                jwt=self.jwt,
                mount_point=self.mount_point_value,
            )
            return response["auth"]["client_token"]
        except Exception as e:
            raise VaultAuthenticationError(f"JWT authentication failed: {e}")

    def get_mount_point(self) -> str:
        """Get the JWT auth mount point."""
        return self.mount_point_value
