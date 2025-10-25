"""Kubernetes authentication for Vault."""

import os
from typing import Any, Optional

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthMethod,
    VaultAuthenticationError,
)


class KubernetesAuth(VaultAuthMethod):
    """Kubernetes authentication for Vault.

    Use this when running inside a Kubernetes pod to authenticate
    using the service account token.

    Example:
        >>> from config_stash.secret_stores.vault_auth import KubernetesAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> # Automatic (reads from default location)
        >>> auth = KubernetesAuth(role='myapp-role')
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
        >>>
        >>> # Custom JWT path
        >>> auth = KubernetesAuth(
        ...     role='myapp-role',
        ...     jwt_path='/custom/path/to/token'
        ... )
    """

    DEFAULT_JWT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

    def __init__(
        self,
        role: str,
        jwt: Optional[str] = None,
        jwt_path: Optional[str] = None,
        mount_point: str = "kubernetes",
    ):
        """Initialize Kubernetes authentication.

        Args:
            role: Vault Kubernetes role name
            jwt: JWT token (if not provided, reads from file)
            jwt_path: Path to JWT token file (default: K8s service account token path)
            mount_point: Auth mount point (default: 'kubernetes')

        Example:
            >>> # Automatic
            >>> auth = KubernetesAuth(role='myapp')
            >>>
            >>> # Custom JWT
            >>> auth = KubernetesAuth(role='myapp', jwt='eyJhbGc...')
            >>>
            >>> # Custom path
            >>> auth = KubernetesAuth(
            ...     role='myapp',
            ...     jwt_path='/custom/token'
            ... )
        """
        self.role = role
        self.jwt = jwt
        self.jwt_path = jwt_path or self.DEFAULT_JWT_PATH
        self.mount_point_value = mount_point

    def _get_jwt(self) -> str:
        """Get JWT token from file or stored value.

        Returns:
            JWT token string

        Raises:
            VaultAuthenticationError: If JWT cannot be obtained
        """
        if self.jwt:
            return self.jwt

        try:
            with open(self.jwt_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise VaultAuthenticationError(
                f"JWT token file not found: {self.jwt_path}. "
                f"Are you running inside a Kubernetes pod?"
            )
        except Exception as e:
            raise VaultAuthenticationError(
                f"Failed to read JWT token: {e}"
            )

    def authenticate(self, client: Any) -> str:
        """Authenticate using Kubernetes service account.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If Kubernetes auth fails
        """
        try:
            jwt = self._get_jwt()

            response = client.auth.kubernetes.login(
                role=self.role,
                jwt=jwt,
                mount_point=self.mount_point_value,
            )

            return response["auth"]["client_token"]

        except Exception as e:
            raise VaultAuthenticationError(
                f"Kubernetes authentication failed: {e}"
            )

    def get_mount_point(self) -> str:
        """Get the Kubernetes auth mount point."""
        return self.mount_point_value
