"""Token-based authentication for Vault."""

from typing import Any

from config_stash.secret_stores.vault_auth.base import VaultAuthMethod


class TokenAuth(VaultAuthMethod):
    """Token-based authentication for Vault.

    This is the simplest authentication method where you provide
    a pre-existing Vault token directly.

    Example:
        >>> from config_stash.secret_stores.vault_auth import TokenAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> auth = TokenAuth(token='s.1234567890abcdef')
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
    """

    def __init__(self, token: str):
        """Initialize token authentication.

        Args:
            token: Vault token string

        Example:
            >>> auth = TokenAuth(token='s.1234567890')
        """
        self.token = token

    def authenticate(self, client: Any) -> str:
        """Return the provided token.

        Args:
            client: hvac.Client instance (not used for token auth)

        Returns:
            The Vault token
        """
        return self.token

    def supports_token_renewal(self) -> bool:
        """Token auth supports renewal."""
        return True

    def renew_token(self, client: Any) -> str:
        """Renew the token.

        Args:
            client: hvac.Client instance

        Returns:
            Renewed token
        """
        client.auth.token.renew_self()
        return self.token
