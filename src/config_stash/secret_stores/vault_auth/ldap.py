"""LDAP authentication for Vault."""

import getpass
from typing import Any, Callable, Optional

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthMethod,
    VaultAuthenticationError,
)


class LDAPAuth(VaultAuthMethod):
    """LDAP authentication for Vault.

    Authenticate using LDAP credentials (username/password).
    Supports custom password providers for complex authentication flows.

    Example:
        >>> from config_stash.secret_stores.vault_auth import LDAPAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> # Simple username/password
        >>> auth = LDAPAuth(
        ...     username='john.doe',
        ...     password='secret'
        ... )
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
        >>>
        >>> # Interactive prompt
        >>> auth = LDAPAuth(username='john.doe')  # Will prompt for password
        >>>
        >>> # Custom password provider (e.g., PIN+Token)
        >>> def get_complex_password():
        ...     pin = getpass.getpass("Enter PIN: ")
        ...     token = getpass.getpass("Enter Token: ")
        ...     return pin + token
        >>>
        >>> auth = LDAPAuth(
        ...     username='john.doe',
        ...     password_provider=get_complex_password
        ... )
    """

    def __init__(
        self,
        username: str,
        password: Optional[str] = None,
        password_provider: Optional[Callable[[], str]] = None,
        mount_point: str = "ldap",
    ):
        """Initialize LDAP authentication.

        Args:
            username: LDAP username
            password: LDAP password. If not provided and password_provider
                is None, will prompt interactively.
            password_provider: Optional function that returns the password.
                Useful for complex authentication like PIN+Token.
            mount_point: Auth mount point (default: 'ldap')

        Example:
            >>> # Simple
            >>> auth = LDAPAuth(username='user', password='pass')
            >>>
            >>> # Interactive
            >>> auth = LDAPAuth(username='user')
            >>>
            >>> # Custom provider for PIN+Token
            >>> def pin_token():
            ...     pin = getpass.getpass("PIN: ")
            ...     token = getpass.getpass("Token: ")
            ...     return pin + token
            >>>
            >>> auth = LDAPAuth(username='user', password_provider=pin_token)
        """
        self.username = username
        self.password = password
        self.password_provider = password_provider
        self.mount_point_value = mount_point

    def _get_password(self) -> str:
        """Get password from provider, stored value, or prompt.

        Returns:
            Password string

        Raises:
            VaultAuthenticationError: If password cannot be obtained
        """
        # Use password provider if available
        if self.password_provider:
            try:
                return self.password_provider()
            except Exception as e:
                raise VaultAuthenticationError(
                    f"Password provider failed: {e}"
                )

        # Use stored password if available
        if self.password:
            return self.password

        # Prompt for password interactively
        try:
            return getpass.getpass(f"Enter LDAP password for {self.username}: ")
        except Exception as e:
            raise VaultAuthenticationError(
                f"Failed to get password: {e}"
            )

    def authenticate(self, client: Any) -> str:
        """Authenticate using LDAP.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If LDAP auth fails
        """
        try:
            password = self._get_password()

            response = client.auth.ldap.login(
                username=self.username,
                password=password,
                mount_point=self.mount_point_value,
            )

            return response["auth"]["client_token"]

        except Exception as e:
            raise VaultAuthenticationError(
                f"LDAP authentication failed: {e}"
            )

    def get_mount_point(self) -> str:
        """Get the LDAP auth mount point."""
        return self.mount_point_value
