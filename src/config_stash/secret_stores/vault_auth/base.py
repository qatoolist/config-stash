"""Base authentication method for Vault."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class VaultAuthMethod(ABC):
    """Abstract base class for Vault authentication methods.

    All Vault authentication implementations should inherit from this class
    and implement the authenticate() method.

    Example:
        >>> class CustomAuth(VaultAuthMethod):
        ...     def authenticate(self, client):
        ...         response = client.auth.custom.login(...)
        ...         return response['auth']['client_token']
    """

    @abstractmethod
    def authenticate(self, client: Any) -> str:
        """Authenticate with Vault and return a client token.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token string

        Raises:
            VaultAuthenticationError: If authentication fails
        """
        pass

    def get_mount_point(self) -> Optional[str]:
        """Get the auth mount point, if different from default.

        Returns:
            Auth mount point or None to use default
        """
        return None

    def supports_token_renewal(self) -> bool:
        """Check if this auth method supports token renewal.

        Returns:
            True if token renewal is supported
        """
        return False

    def renew_token(self, client: Any) -> str:
        """Renew the authentication token.

        Args:
            client: hvac.Client instance

        Returns:
            New or renewed token

        Raises:
            NotImplementedError: If renewal is not supported
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support token renewal"
        )


class VaultAuthenticationError(Exception):
    """Raised when Vault authentication fails."""

    pass
